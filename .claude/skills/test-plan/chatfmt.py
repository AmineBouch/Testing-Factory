"""Outils communs à slack.py et teams.py : lecture du .env et mise en forme
du Markdown des rapports (titres, gras, liens, tableaux) pour Slack ou Teams."""

import re
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD = re.compile(r"\*\*(.+?)\*\*")
TABLE_SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")


def load_env():
    values = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _table_row(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return "• " + " · ".join(c for c in cells if c)


def flatten(md):
    """Titres → gras, tableaux → une puce par ligne (ni Slack ni Teams n'affichent
    les tableaux Markdown). Le gras et les liens restent en syntaxe Markdown."""
    out = []
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            if not TABLE_SEP.match(stripped):
                out.append(_table_row(stripped))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        out.append(f"**{m.group(2)}**" if m else line)
    return "\n".join(out)


def to_slack(md):
    """Markdown → mrkdwn Slack : **x** → *x*, [t](u) → <u|t>."""
    text = flatten(md)
    text = LINK.sub(lambda m: f"<{m.group(2)}|{m.group(1)}>", text)
    return BOLD.sub(r"*\1*", text)


def to_teams(md):
    """Markdown → texte pour un TextBlock d'Adaptive Card (gras et liens gérés)."""
    return flatten(md)


def chunks(text, size):
    parts, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > size and current:
            parts.append(current)
            current = ""
        current += line
    if current:
        parts.append(current)
    return parts
