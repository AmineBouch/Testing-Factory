"""Garde-fous de l'agent QA : frein d'urgence (pause) et limite de tickets par passage.

Réglages dans le .env à la racine du projet :
  AGENT_PAUSE=0         1 = l'agent est en pause : les tâches planifiées s'arrêtent
                        tout de suite et xray.py refuse de créer quoi que ce soit.
  AGENT_MAX_TICKETS=40  nombre maximum de tickets créés par un passage planifié
                        (Tests + sous-tâches Gherkin + Test Plans).

État du passage en cours : reports/.agent-run.json.

Usage :
    python guard.py status           # pause ? limite ? passage en cours ?
    python guard.py pause            # met AGENT_PAUSE=1 (frein d'urgence)
    python guard.py resume           # remet AGENT_PAUSE=0
    python guard.py start <tâche>    # début d'un passage planifié (refusé si pause)
    python guard.py reserve <n>      # réserve n créations avant de les faire
                                     # (refusé si la limite serait dépassée : le passage s'arrête)
    python guard.py end              # fin du passage

Chaque commande affiche un JSON. Code de sortie 0 = feu vert, 2 = arrêt demandé.
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT / ".env"
STATE = ROOT / "reports" / ".agent-run.json"
DEFAULT_MAX = 40
RUN_TTL = timedelta(hours=6)  # un passage oublié (pas de « end ») expire tout seul


class Stop(Exception):
    """Arrêt demandé par un garde-fou (pause ou limite)."""


def load_env():
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def paused():
    return load_env().get("AGENT_PAUSE", "0").strip().lower() in ("1", "true", "oui", "yes", "on")


def max_tickets():
    try:
        return int(load_env().get("AGENT_MAX_TICKETS", DEFAULT_MAX))
    except ValueError:
        return DEFAULT_MAX


def set_env(key, value):
    """Remplace (ou ajoute) une ligne KEY=value du .env sans toucher aux autres."""
    text = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    line = f"{key}={value}"
    text, n = re.subn(rf"(?m)^{re.escape(key)}=.*$", line, text)
    if not n:
        text = text.rstrip("\n") + f"\n{line}\n"
    ENV_FILE.write_text(text, encoding="utf-8")


def read_run():
    try:
        run = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if run.get("ended") or datetime.now() - datetime.fromisoformat(run["started"]) > RUN_TTL:
        return None
    return run


def write_run(run):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")


def check_create(kind):
    """Appelé par xray.py avant chaque création : lève Stop si un garde-fou l'interdit."""
    if paused():
        raise Stop("Agent en pause (AGENT_PAUSE=1) : création refusée. "
                   "Relancer avec : python .claude/skills/test-plan/guard.py resume")
    run = read_run()
    if not run:
        return  # hors passage planifié (utilisateur présent) : seule la pause s'applique
    if run.get("stopped"):
        raise Stop(f"Passage « {run['task']} » arrêté par la limite de tickets : création refusée.")
    run["created"] = run.get("created", 0) + 1
    if run["created"] > run["max"]:
        run["stopped"] = True
        write_run(run)
        raise Stop(f"Limite de {run['max']} tickets atteinte pendant « {run['task']} » : création refusée.")
    run.setdefault("log", []).append(kind)
    write_run(run)


def cmd_status(_args):
    return {"ok": True, "paused": paused(), "max_tickets": max_tickets(), "run": read_run()}


def cmd_pause(_args):
    set_env("AGENT_PAUSE", "1")
    return {"ok": True, "paused": True, "info": "Frein d'urgence activé : l'agent ne crée plus rien."}


def cmd_resume(_args):
    set_env("AGENT_PAUSE", "0")
    return {"ok": True, "paused": False, "info": "Agent réactivé."}


def cmd_start(args):
    task = args[0] if args else "passage"
    if paused():
        raise Stop("Agent en pause (AGENT_PAUSE=1) : passage annulé, rien n'est fait.")
    run = {"task": task, "started": datetime.now().isoformat(timespec="seconds"),
           "max": max_tickets(), "reserved": 0, "created": 0, "stopped": False}
    write_run(run)
    return {"ok": True, **run}


def cmd_reserve(args):
    n = int(args[0])
    if paused():
        raise Stop("Agent en pause (AGENT_PAUSE=1) : création refusée.")
    run = read_run()
    if not run:
        raise Stop("Aucun passage en cours : lancer d'abord « guard.py start <tâche> ».")
    if run.get("stopped"):
        raise Stop("Le passage est déjà arrêté par la limite de tickets.")
    if run["reserved"] + n > run["max"]:
        run["stopped"] = True
        write_run(run)
        raise Stop(f"Limite atteinte : {run['reserved']} déjà réservés + {n} demandés "
                   f"> {run['max']} tickets. Passage arrêté, rien de plus ne sera créé.")
    run["reserved"] += n
    write_run(run)
    return {"ok": True, "reserved": run["reserved"], "max": run["max"],
            "remaining": run["max"] - run["reserved"]}


def cmd_end(_args):
    run = read_run()
    if run:
        run["ended"] = datetime.now().isoformat(timespec="seconds")
        write_run(run)
    return {"ok": True, "run": run}


COMMANDS = {"status": cmd_status, "pause": cmd_pause, "resume": cmd_resume,
            "start": cmd_start, "reserve": cmd_reserve, "end": cmd_end}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    try:
        result = COMMANDS[sys.argv[1]](sys.argv[2:])
    except Stop as exc:
        print(json.dumps({"ok": False, "stop": True, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(2)
    except (ValueError, IndexError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
