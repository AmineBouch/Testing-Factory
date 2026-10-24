"""Notifications et rapports sur tous les canaux : email, Slack et Teams.

S'appuie sur mailer.py, slack.py et teams.py (identifiants .env,
jamais affichés). Un canal non configuré dans .env (Slack ou Teams) est ignoré.
Garde dans state/last-notified-key (fichier suivi par git, mis à jour par GitHub
Actions) le numéro du dernier ticket SCRUM déjà signalé, pour ne jamais notifier
deux fois le même ticket.

Usage :
    python notify.py last                          # dernier ticket déjà notifié (ex. SCRUM-100)
    python notify.py send "<sujet>" "<texte>"      # envoie sur email + Slack + Teams
    python notify.py send-file <fichier.md> "<sujet>"  # envoie un rapport sur les 3 canaux
    python notify.py mark SCRUM-123                # enregistre SCRUM-123 comme dernier notifié
                                                   # (ne recule jamais)

Chaque commande affiche un JSON sur la sortie standard.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STATE = ROOT / "state" / "last-notified-key"
PROJECT = "SCRUM"


def key_number(key):
    m = re.fullmatch(rf"{PROJECT}-(\d+)", key.strip().upper())
    if not m:
        raise ValueError(f"clé invalide : {key}")
    return int(m.group(1))


def read_last():
    try:
        return int(STATE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def run(script, *args):
    proc = subprocess.run([sys.executable, str(HERE / script), *args],
                          capture_output=True, text=True, encoding="utf-8")
    out = proc.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"ok": False, "error": (out or proc.stderr.strip())[-500:]}


def cmd_last(_args):
    n = read_last()
    return {"ok": True, "last": f"{PROJECT}-{n}" if n else None}


def summary(results):
    """ok = tous les canaux configurés ont réussi ; un échec n'empêche pas les autres."""
    failed = [name for name, r in results.items() if not r.get("ok")]
    return {"ok": not failed, "echecs": failed, **results}


def cmd_send(args):
    subject, text = args[0], args[1]
    return summary({
        "email": run("mailer.py", "send-text", subject, text),
        "slack": run("slack.py", "send-text", f"**{subject}**\n\n{text}"),
        "teams": run("teams.py", "send-text", f"{subject}\n{text}"),
    })


def cmd_send_file(args):
    path, subject = args[0], args[1]
    return summary({
        "email": run("mailer.py", "send-file", path, subject),
        "slack": run("slack.py", "send-file", path, subject),
        "teams": run("teams.py", "send-file", path, subject),
    })


def cmd_mark(args):
    n = max(read_last(), key_number(args[0]))
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(str(n), encoding="utf-8")
    return {"ok": True, "last": f"{PROJECT}-{n}"}


COMMANDS = {"last": cmd_last, "send": cmd_send, "send-file": cmd_send_file, "mark": cmd_mark}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    try:
        result = COMMANDS[sys.argv[1]](sys.argv[2:])
    except (ValueError, IndexError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
