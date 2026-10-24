"""Envoi des rapports et notifications Testing Factory sur Slack.

Identifiants lus dans le .env à la racine du projet (jamais affichés) :
  SLACK_WEBHOOK_URL   webhook entrant Slack (https://hooks.slack.com/services/...) : messages texte.
  SLACK_BOT_TOKEN     (optionnel) token de bot xoxb-... avec le droit files:write,
  SLACK_CHANNEL_ID    (optionnel) ID du canal (C0123...) : permettent d'envoyer aussi
                      les fichiers (PDF, vidéo, .md) en pièce jointe.
Si SLACK_WEBHOOK_URL est vide, Slack est ignoré (réponse "skipped") sans erreur.

Usage :
    python slack.py check                              # envoie un message de test
    python slack.py send-text "<texte>"                # envoie un message
    python slack.py send-file <fichier> ["<titre>"]    # contenu d'un fichier .md (+ fichier joint si bot)
    python slack.py send-doc <fichier> ["<texte>"]     # résumé + fichier joint (PDF, MP4) si bot

Chaque commande affiche un JSON sur la sortie standard.
"""

import json
import sys
from pathlib import Path

import requests
import truststore

from chatfmt import chunks, load_env, to_slack

truststore.inject_into_ssl()

MAX_LEN = 3500
SKIPPED = {"ok": True, "skipped": True,
           "info": "Slack non configuré (SLACK_WEBHOOK_URL vide dans .env)"}


class SlackError(RuntimeError):
    pass


def settings():
    env = load_env()
    return (env.get("SLACK_WEBHOOK_URL", ""), env.get("SLACK_BOT_TOKEN", ""),
            env.get("SLACK_CHANNEL_ID", ""))


def post_webhook(url, text):
    try:
        resp = requests.post(url, json={"text": text, "mrkdwn": True}, timeout=60)
    except requests.RequestException as exc:
        # Le message d'erreur de requests contient l'URL (secrète) : on ne garde que le type.
        raise SlackError(f"webhook : connexion impossible ({type(exc).__name__})") from None
    if resp.status_code != 200:
        blocked = "zscaler" in resp.text.lower()
        raise SlackError(f"webhook : HTTP {resp.status_code} {resp.text[:100]}"
                         + (" – bloqué par Zscaler" if blocked else ""))


def send_text(text):
    url, _, _ = settings()
    if not url:
        return None
    parts = chunks(to_slack(text), MAX_LEN)
    for part in parts:
        post_webhook(url, part)
    return len(parts)


def bot_api(method, token, **kwargs):
    resp = requests.post(f"https://slack.com/api/{method}", timeout=120,
                         headers={"Authorization": f"Bearer {token}"}, **kwargs)
    body = resp.json()
    if not body.get("ok"):
        raise SlackError(f"{method} : {body.get('error', resp.status_code)}")
    return body


def upload(path, comment=""):
    """Envoie un fichier dans le canal si le bot est configuré, sinon renvoie None."""
    _, token, channel = settings()
    if not (token and channel):
        return None
    data = path.read_bytes()
    up = bot_api("files.getUploadURLExternal", token,
                 data={"filename": path.name, "length": len(data)})
    requests.post(up["upload_url"], files={"file": (path.name, data)}, timeout=300).raise_for_status()
    bot_api("files.completeUploadExternal", token,
            json={"files": [{"id": up["file_id"], "title": path.name}],
                  "channel_id": channel, "initial_comment": comment[:3000]})
    return path.name


def cmd_check(_args):
    n = send_text("✅ Testing Factory : connexion Slack OK.")
    if n is None:
        return SKIPPED
    _, token, channel = settings()
    return {"ok": True, "messages": n, "fichiers": bool(token and channel)}


def cmd_send_text(args):
    n = send_text(" ".join(args))
    return SKIPPED if n is None else {"ok": True, "messages": n}


def cmd_send_file(args):
    path = Path(args[0])
    title = args[1] if len(args) > 1 else ""
    text = path.read_text(encoding="utf-8")
    n = send_text(f"**{title}**\n\n{text}" if title else text)
    if n is None:
        return SKIPPED
    return {"ok": True, "messages": n, "piece_jointe": upload(path, title)}


def cmd_send_doc(args):
    paths = [Path(args[0])]
    comment = args[1] if len(args) > 1 else "Rapport en pièce jointe."
    paths += [Path(a) for a in args[2:]]
    url, token, channel = settings()
    if not url:
        return SKIPPED
    if token and channel:
        sent = [upload(paths[0], comment)] + [upload(p) for p in paths[1:]]
        return {"ok": True, "pieces_jointes": sent}
    n = send_text(comment + "\n_(fichier non joint : ajouter SLACK_BOT_TOKEN et SLACK_CHANNEL_ID pour l'envoyer)_")
    return {"ok": True, "messages": n, "pieces_jointes": None}


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
    except (SlackError, requests.RequestException, OSError, ValueError, IndexError) as exc:
        msg = str(exc) if isinstance(exc, (SlackError, OSError, IndexError)) else type(exc).__name__
        print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
