"""Envoi des rapports et notifications Testing Factory sur Microsoft Teams.

Identifiant lu dans le .env à la racine du projet (jamais affiché) :
  TEAMS_WEBHOOK_URL   URL d'un workflow Teams « Publier dans un canal lorsqu'une
                      demande de webhook est reçue » (Power Automate / Workflows).
Si TEAMS_WEBHOOK_URL est vide, Teams est ignoré (réponse "skipped") sans erreur.

Limite : un webhook Teams n'accepte pas de pièce jointe. Les rapports sont envoyés
sous forme de carte (texte mis en forme, liens cliquables) ; les PDF et vidéos
restent disponibles par mail et Slack.

Usage :
    python teams.py check                              # envoie un message de test
    python teams.py send-text "<texte>"                # envoie un message
    python teams.py send-file <fichier> ["<titre>"]    # contenu d'un fichier .md
    python teams.py send-doc <fichier> ["<texte>"]     # résumé seulement (fichier non joint)

Chaque commande affiche un JSON sur la sortie standard.
"""

import json
import sys
from pathlib import Path

import requests
import truststore

from chatfmt import chunks, load_env, to_teams

truststore.inject_into_ssl()

MAX_LEN = 15000  # une carte Teams est limitée à ~28 Ko
SKIPPED = {"ok": True, "skipped": True,
           "info": "Teams non configuré (TEAMS_WEBHOOK_URL vide dans .env)"}


class TeamsError(RuntimeError):
    pass


def card(text, title=""):
    body, gap = [], False
    if title:
        body.append({"type": "TextBlock", "text": title, "weight": "Bolder",
                     "size": "Medium", "wrap": True})
    for line in text.splitlines():
        if not line.strip():
            gap = True
            continue
        body.append({"type": "TextBlock", "text": line, "wrap": True,
                     "spacing": "Medium" if gap else "None"})
        gap = False
    return {"type": "message", "attachments": [{
        "contentType": "application/vnd.microsoft.card.adaptive",
        "contentUrl": None,
        "content": {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard", "version": "1.4",
                    "msteams": {"width": "Full"}, "body": body}}]}


def post(text, title=""):
    url = load_env().get("TEAMS_WEBHOOK_URL", "")
    if not url:
        return None
    parts = chunks(to_teams(text), MAX_LEN)
    for i, part in enumerate(parts):
        label = title if i == 0 else (f"{title} (suite)" if title else "")
        try:
            resp = requests.post(url, json=card(part, label), timeout=60)
        except requests.RequestException as exc:
            # Le message d'erreur de requests contient l'URL (secrète) : on ne garde que le type.
            raise TeamsError(f"webhook : connexion impossible ({type(exc).__name__})") from None
        if resp.status_code not in (200, 202):
            blocked = "zscaler" in resp.text.lower()
            raise TeamsError(f"webhook : HTTP {resp.status_code} {resp.text[:100]}"
                             + (" – bloqué par Zscaler" if blocked else ""))
    return len(parts)


def cmd_check(_args):
    n = post("Connexion Teams OK.", "✅ Testing Factory")
    return SKIPPED if n is None else {"ok": True, "messages": n}


def cmd_send_text(args):
    text = " ".join(args)
    first, _, rest = text.partition("\n")
    n = post(rest.strip(), first) if rest.strip() else post(text)
    return SKIPPED if n is None else {"ok": True, "messages": n}


def cmd_send_file(args):
    path = Path(args[0])
    title = args[1] if len(args) > 1 else path.stem
    n = post(path.read_text(encoding="utf-8"), title)
    return SKIPPED if n is None else {"ok": True, "messages": n, "piece_jointe": None}


def cmd_send_doc(args):
    path = Path(args[0])
    text = args[1] if len(args) > 1 else "Rapport disponible."
    n = post(f"{text}\n\n_Fichier {path.name} envoyé par mail et Slack._")
    return SKIPPED if n is None else {"ok": True, "messages": n, "piece_jointe": None}


COMMANDS = {
    "check": cmd_check,
    "send-text": cmd_send_text,
    "send-file": cmd_send_file,
    "send-doc": cmd_send_doc,
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    try:
        result = COMMANDS[sys.argv[1]](sys.argv[2:])
    except (TeamsError, OSError, IndexError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
