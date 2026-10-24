"""Envoi du rapport Testing Factory par email (SMTP Gmail).

Les identifiants sont lus dans le fichier .env à la racine du projet
(MAIL_SMTP_USER, MAIL_SMTP_APP_PASSWORD, MAIL_TO). Ils ne sont jamais affichés.
MAIL_SMTP_APP_PASSWORD est un « mot de passe d'application » Google (16 lettres),
pas le mot de passe du compte. MAIL_TO peut contenir plusieurs adresses séparées
par des virgules ; vide = envoi à MAIL_SMTP_USER.

Usage :
    python mailer.py check                            # vérifie la connexion SMTP
    python mailer.py send-text "<sujet>" "<texte>"    # envoie un email texte
    python mailer.py send-file <fichier> ["<sujet>"]  # envoie le contenu d'un fichier
                                                      # texte + le fichier en pièce jointe

Chaque commande affiche un JSON sur la sortie standard.
"""

import json
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

import truststore

from chatfmt import load_env  # .env + variables d'environnement (Secrets GitHub Actions)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def settings():
    env = load_env()
    user = env.get("MAIL_SMTP_USER", "")
    password = env.get("MAIL_SMTP_APP_PASSWORD", "").replace(" ", "")
    if not user:
        raise RuntimeError("MAIL_SMTP_USER est vide dans .env")
    if not password:
        raise RuntimeError("MAIL_SMTP_APP_PASSWORD est vide dans .env")
    to = [a.strip() for a in env.get("MAIL_TO", "").split(",") if a.strip()] or [user]
    return user, password, to


def connect(user, password):
    # Magasin de certificats Windows (antivirus / proxy d'entreprise).
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=60)
    server.login(user, password)
    return server


def send(subject, body, attachment=None):
    user, password, to = settings()
    msg = EmailMessage()
    msg["From"] = f"TestingFactory QA <{user}>"
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body)
    files = attachment if isinstance(attachment, list) else [attachment] if attachment else []
    types = {".pdf": ("application", "pdf"), ".mp4": ("video", "mp4")}
    for f in files:
        maintype, subtype = types.get(f.suffix.lower(), ("text", "markdown"))
        msg.add_attachment(f.read_bytes(), maintype=maintype, subtype=subtype, filename=f.name)
    with connect(user, password) as server:
        server.send_message(msg)
    names = [f.name for f in files]
    return {"ok": True, "destinataires": len(to),
            "piece_jointe": (names[0] if len(names) == 1 else names) if names else None}


def cmd_check(_args):
    user, password, to = settings()
    with connect(user, password):
        pass
    return {"ok": True, "smtp": SMTP_HOST, "destinataires": len(to)}


def cmd_send_text(args):
    if len(args) < 2:
        raise RuntimeError('usage : send-text "<sujet>" "<texte>"')
    return send(args[0], " ".join(args[1:]))


def cmd_send_file(args):
    if not args:
        raise RuntimeError('usage : send-file <fichier> ["<sujet>"]')
    path = Path(args[0])
    subject = args[1] if len(args) > 1 else f"Rapport Xray – {path.stem}"
    return send(subject, path.read_text(encoding="utf-8"), attachment=path)


def cmd_send_doc(args):
    """send-doc <fichier> "<sujet>" ["<texte>"] [<autre fichier>…] : fichiers binaires (PDF, MP4…)
    en pièces jointes d'un même mail."""
    if len(args) < 2:
        raise RuntimeError('usage : send-doc <fichier> "<sujet>" ["<texte>"] [<autre fichier>…]')
    body = args[2] if len(args) > 2 else "Rapport en pièce jointe."
    files = [Path(args[0])] + [Path(a) for a in args[3:]]
    return send(args[1], body, attachment=files)


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
    except (smtplib.SMTPException, RuntimeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
