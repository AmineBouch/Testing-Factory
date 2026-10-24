"""Petit client de l'API REST Jira Cloud (remplace le connecteur Atlassian sur GitHub Actions).

Identifiants lus dans .env ou dans les variables d'environnement (jamais affichés) :
  JIRA_EMAIL       adresse du compte Atlassian
  JIRA_API_TOKEN   token créé sur https://id.atlassian.com/manage-profile/security/api-tokens
  JIRA_BASE_URL    (optionnel) https://testingfactory2026.atlassian.net par défaut

Les descriptions et commentaires sont en « wiki markup » Jira (API v2) :
  h2. Titre · *gras* · [texte|https://lien] · * puce · # liste numérotée
  {code:gherkin} ... {code}

Usage :
    python jira.py check                                   # vérifie la connexion
    python jira.py search "<JQL>" [champ1,champ2,...]      # recherche (pagine tout seul)
    python jira.py get <clé> [champ1,champ2,...]           # lit un ticket (description, liens…)
    python jira.py create <fichier.json>                   # crée un ticket
    python jira.py edit <clé> <fichier.json>               # modifie des champs
    python jira.py link <type> <inward> <outward>          # ex. link Test SCRUM-120 SCRUM-119
    python jira.py comment <clé> "<texte>"                 # ajoute un commentaire

Format JSON pour create :
    {"project": "SCRUM", "issuetype": "Subtask", "summary": "...",
     "description": "wiki markup", "parent": "SCRUM-120", "labels": ["gherkin"]}
Format JSON pour edit : {"fields": {"labels": ["a", "b"], "description": "..."}}

Chaque commande affiche un JSON sur la sortie standard.
"""

import json
import sys
from pathlib import Path

import requests
import truststore

import guard
from chatfmt import load_env

truststore.inject_into_ssl()

DEFAULT_BASE = "https://testingfactory2026.atlassian.net"
DEFAULT_FIELDS = "summary,status,issuetype,parent,labels,issuelinks,reporter,created"


class JiraError(RuntimeError):
    pass


def session():
    env = load_env()
    email, token = env.get("JIRA_EMAIL", ""), env.get("JIRA_API_TOKEN", "")
    if not email or not token:
        raise JiraError("JIRA_EMAIL ou JIRA_API_TOKEN est vide (.env ou Secrets GitHub)")
    s = requests.Session()
    s.auth = (email, token)
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    return s, env.get("JIRA_BASE_URL", DEFAULT_BASE).rstrip("/")


def call(method, path, **kwargs):
    s, base = session()
    resp = s.request(method, base + path, timeout=60, **kwargs)
    if resp.status_code >= 400:
        raise JiraError(f"{method} {path} : HTTP {resp.status_code} {resp.text[:400]}")
    return resp.json() if resp.content else {}


def slim(issue):
    """Garde l'essentiel d'un ticket pour une sortie lisible."""
    f = issue.get("fields", {})
    out = {"key": issue.get("key"), "id": issue.get("id")}
    for name, value in f.items():
        if value in (None, [], ""):
            continue
        if name in ("status", "issuetype", "priority"):
            out[name] = value.get("name")
        elif name == "parent":
            out[name] = value.get("key")
        elif name in ("reporter", "assignee"):
            out[name] = value.get("displayName")
        elif name == "issuelinks":
            out[name] = [{"type": l["type"]["name"],
                          "inward": l.get("inwardIssue", {}).get("key"),
                          "outward": l.get("outwardIssue", {}).get("key")} for l in value]
        elif name == "subtasks":
            out[name] = [{"key": s["key"], "summary": s["fields"]["summary"]} for s in value]
        elif name == "comment":
            out[name] = [{"author": c["author"]["displayName"], "created": c["created"],
                          "body": c["body"]} for c in value.get("comments", [])]
        else:
            out[name] = value
    return out


def cmd_check(_args):
    me = call("GET", "/rest/api/2/myself")
    return {"ok": True, "compte": me.get("displayName")}


def cmd_search(args):
    jql = args[0]
    fields = args[1] if len(args) > 1 else DEFAULT_FIELDS
    issues, token = [], None
    while True:
        body = {"jql": jql, "fields": fields.split(","), "maxResults": 100}
        if token:
            body["nextPageToken"] = token
        data = call("POST", "/rest/api/3/search/jql", json=body)
        issues += data.get("issues", [])
        token = data.get("nextPageToken")
        if not token or data.get("isLast", True):
            break
    # Les descriptions v3 sont en ADF : on ne les renvoie pas ici (utiliser get).
    result = []
    for i in issues:
        i.get("fields", {}).pop("description", None)
        result.append(slim(i))
    return {"ok": True, "total": len(result), "issues": result}


def cmd_get(args):
    fields = args[1] if len(args) > 1 else (
        "summary,description,status,issuetype,parent,labels,issuelinks,subtasks,comment,reporter,created")
    issue = call("GET", f"/rest/api/2/issue/{args[0]}", params={"fields": fields})
    return {"ok": True, "issue": slim(issue)}


def cmd_create(args):
    if guard.paused():
        return {"ok": False, "stop": True, "error": "Agent en pause (AGENT_PAUSE=1) : création refusée"}
    spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    fields = {"project": {"key": spec.get("project", "SCRUM")},
              "issuetype": {"name": spec["issuetype"]},
              "summary": spec["summary"]}
    if spec.get("description"):
        fields["description"] = spec["description"]
    if spec.get("labels"):
        fields["labels"] = spec["labels"]
    if spec.get("parent"):
        fields["parent"] = {"key": spec["parent"]}
    data = call("POST", "/rest/api/2/issue", json={"fields": fields})
    return {"ok": True, "key": data["key"], "id": data["id"]}


def cmd_edit(args):
    if guard.paused():
        return {"ok": False, "stop": True, "error": "Agent en pause (AGENT_PAUSE=1) : modification refusée"}
    body = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    call("PUT", f"/rest/api/2/issue/{args[0]}", json=body)
    return {"ok": True, "key": args[0]}


def cmd_link(args):
    link_type, inward, outward = args[0], args[1], args[2]
    call("POST", "/rest/api/2/issueLink", json={
        "type": {"name": link_type},
        "inwardIssue": {"key": inward},
        "outwardIssue": {"key": outward}})
    return {"ok": True, "lien": f"{inward} {link_type} {outward}"}


def cmd_comment(args):
    data = call("POST", f"/rest/api/2/issue/{args[0]}/comment", json={"body": args[1]})
    return {"ok": True, "id": data.get("id")}


COMMANDS = {"check": cmd_check, "search": cmd_search, "get": cmd_get, "create": cmd_create,
            "edit": cmd_edit, "link": cmd_link, "comment": cmd_comment}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    try:
        result = COMMANDS[sys.argv[1]](sys.argv[2:])
    except Exception as exc:  # message sans secret (l'auth n'apparaît jamais dans les erreurs)
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
