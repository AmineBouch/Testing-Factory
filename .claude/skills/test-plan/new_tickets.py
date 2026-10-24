"""Notification des nouveaux tickets du projet Jira SCRUM (lancé toutes les heures par GitHub Actions).

1. Agent en pause (AGENT_PAUSE=1) → ne fait rien.
2. Lit le dernier ticket déjà notifié (state/last-notified-key, via notify.py).
3. Cherche les tickets plus récents ; s'il y en a, envoie UNE notification groupée
   (mail + Slack + Teams) puis mémorise le plus grand numéro.
   Si tous les canaux échouent, ne mémorise rien : les tickets seront renotifiés au passage suivant.

Usage :
    python new_tickets.py            # détecte, notifie, mémorise
    python new_tickets.py --dry-run  # affiche seulement ce qui serait envoyé

Affiche un JSON. Code de sortie 1 si l'envoi a échoué sur tous les canaux.
"""

import json
import sys

import guard
import jira
import notify

PROJECT = notify.PROJECT
BROWSE = "https://testingfactory2026.atlassian.net/browse/"
MAX_LINES = 30


def lines_for(issues):
    """Une ligne par ticket ; les sous-tâches et tests sous leur parent quand il est dans le lot."""
    by_key = {i["key"]: i for i in issues}
    children = {}
    roots = []
    for i in issues:
        parent = i.get("parent")
        if parent in by_key:
            children.setdefault(parent, []).append(i)
        else:
            roots.append(i)

    def fmt(i, depth):
        who = f" · créé par {i['reporter']}" if i.get("reporter") else ""
        return (f"{'  ' * depth}{i['key']} · {i.get('issuetype', '?')} · {i.get('summary', '')}"
                f"{who} · {BROWSE}{i['key']}")

    out = []

    def walk(i, depth):
        out.append(fmt(i, depth))
        for c in children.get(i["key"], []):
            walk(c, depth + 1)

    for r in roots:
        walk(r, 0)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dry = "--dry-run" in sys.argv
    if guard.paused():
        print(json.dumps({"ok": True, "info": "Agent en pause : surveillance des tickets suspendue"},
                         ensure_ascii=False))
        return
    last = notify.read_last()
    if not last:
        latest = jira.cmd_search([f"project = {PROJECT} ORDER BY created DESC", "summary"])["issues"][:1]
        if latest and not dry:
            notify.cmd_mark([latest[0]["key"]])
        print(json.dumps({"ok": True, "info": "aucun état : initialisé sans notifier",
                          "last": latest[0]["key"] if latest else None}, ensure_ascii=False))
        return
    found = jira.cmd_search([f"project = {PROJECT} AND key > {PROJECT}-{last} ORDER BY key ASC",
                             "summary,issuetype,parent,reporter,created"])["issues"]
    if not found:
        print(json.dumps({"ok": True, "info": "Aucun nouveau ticket", "last": f"{PROJECT}-{last}"},
                         ensure_ascii=False))
        return
    lines = lines_for(found)
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES] + [f"… et {len(lines) - MAX_LINES} autres"]
    subject = f"[TestFactory] {len(found)} nouveau(x) ticket(s) dans {PROJECT}"
    text = "\n".join(lines)
    highest = max(found, key=lambda i: notify.key_number(i["key"]))["key"]
    if dry:
        print(json.dumps({"ok": True, "dry_run": True, "sujet": subject, "texte": text,
                          "mark": highest}, ensure_ascii=False, indent=2))
        return
    sent = notify.cmd_send([subject, text])
    delivered = any(r.get("ok") and not r.get("skipped")
                    for k, r in sent.items() if isinstance(r, dict))
    if delivered:
        notify.cmd_mark([highest])
    print(json.dumps({"ok": delivered, "tickets": len(found), "mark": highest if delivered else None,
                      "envoi": sent}, ensure_ascii=False, indent=2))
    sys.exit(0 if delivered else 1)


if __name__ == "__main__":
    main()
