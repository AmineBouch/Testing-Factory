"""Petit client pour l'API GraphQL de Xray Cloud.

Les identifiants sont lus dans le fichier .env à la racine du projet
(XRAY_CLIENT_ID, XRAY_CLIENT_SECRET). Ils ne sont jamais affichés.

Usage :
    python xray.py auth
    python xray.py get-test <issueIdDuTest>
    python xray.py create-test <fichier.json>
    python xray.py create-test-plan <fichier.json>
    python xray.py add-tests-to-plan <issueIdDuPlan> <issueIdTest> [<issueIdTest> ...]
    python xray.py update-steps <issueIdDuTest> <fichier.json>   # remplace toutes les étapes
                                       # (anciennes étapes sauvegardées dans reports/.backup/)

Garde-fous (guard.py) : create-test et create-test-plan sont refusés si AGENT_PAUSE=1
dans .env, ou si la limite de tickets du passage planifié en cours est atteinte.

Format JSON pour update-steps : {"steps": [{"action": "...", "data": "...", "result": "..."}]}

Format JSON pour create-test :
    {
      "project": "SCRUM",
      "summary": "Titre du test",
      "description": "Texte libre (optionnel)",
      "labels": ["optionnel"],
      "parent": "SCRUM-8 (epic, optionnel)",
      "steps": [
        {"action": "...", "data": "...", "result": "..."}
      ]
    }

Format JSON pour create-test-plan :
    {
      "project": "SCRUM",
      "summary": "Titre du plan",
      "description": "Texte libre (optionnel)",
      "parent": "SCRUM-8 (epic, optionnel)",
      "testIssueIds": ["10020", "10021"]
    }

Chaque commande affiche un JSON sur la sortie standard.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests
import truststore

import guard

# Utilise le magasin de certificats Windows (antivirus / proxy d'entreprise).
truststore.inject_into_ssl()

BASE_URL = "https://xray.cloud.getxray.app/api/v2"
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def load_env():
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def authenticate():
    env = load_env()
    resp = requests.post(
        f"{BASE_URL}/authenticate",
        json={
            "client_id": env["XRAY_CLIENT_ID"],
            "client_secret": env["XRAY_CLIENT_SECRET"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def graphql(token, query, variables):
    resp = requests.post(
        f"{BASE_URL}/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"], ensure_ascii=False))
    return body["data"]


def jira_fields(spec):
    fields = {"summary": spec["summary"], "project": {"key": spec["project"]}}
    if spec.get("description"):
        fields["description"] = spec["description"]
    if spec.get("labels"):
        fields["labels"] = spec["labels"]
    if spec.get("parent"):
        fields["parent"] = {"key": spec["parent"]}
    return {"fields": fields}


CREATE_TEST = """
mutation ($steps: [CreateStepInput], $jira: JSON!) {
  createTest(testType: {name: "Manual"}, steps: $steps, jira: $jira) {
    test { issueId jira(fields: ["key"]) }
    warnings
  }
}
"""

CREATE_TEST_PLAN = """
mutation ($testIssueIds: [String], $jira: JSON!) {
  createTestPlan(testIssueIds: $testIssueIds, jira: $jira) {
    testPlan { issueId jira(fields: ["key"]) }
    warnings
  }
}
"""

ADD_TESTS_TO_PLAN = """
mutation ($issueId: String!, $testIssueIds: [String]) {
  addTestsToTestPlan(issueId: $issueId, testIssueIds: $testIssueIds) {
    addedTests
    warning
  }
}
"""


GET_TEST = """
query ($issueId: String) {
  getTest(issueId: $issueId) {
    issueId
    testType { name }
    steps { action data result }
    jira(fields: ["key", "summary"])
  }
}
"""


def cmd_get_test(args):
    return graphql(authenticate(), GET_TEST, {"issueId": args[0]})["getTest"]


def cmd_auth(_args):
    authenticate()
    return {"ok": True}


def cmd_create_test(args):
    spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    guard.check_create("Test")
    data = graphql(authenticate(), CREATE_TEST, {
        "steps": spec.get("steps", []),
        "jira": jira_fields(spec),
    })["createTest"]
    return {
        "issueId": data["test"]["issueId"],
        "key": data["test"]["jira"]["key"],
        "warnings": data["warnings"],
    }


def cmd_create_test_plan(args):
    spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    guard.check_create("Test Plan")
    data = graphql(authenticate(), CREATE_TEST_PLAN, {
        "testIssueIds": spec.get("testIssueIds", []),
        "jira": jira_fields(spec),
    })["createTestPlan"]
    return {
        "issueId": data["testPlan"]["issueId"],
        "key": data["testPlan"]["jira"]["key"],
        "warnings": data["warnings"],
    }


def cmd_add_tests_to_plan(args):
    data = graphql(authenticate(), ADD_TESTS_TO_PLAN, {
        "issueId": args[0],
        "testIssueIds": args[1:],
    })["addTestsToTestPlan"]
    return data


REMOVE_ALL_STEPS = """
mutation ($issueId: String!) { removeAllTestSteps(issueId: $issueId) }
"""

ADD_STEP = """
mutation ($issueId: String!, $step: CreateStepInput!) {
  addTestStep(issueId: $issueId, step: $step) { id }
}
"""


def cmd_update_steps(args):
    """Remplace les étapes d'un test (correction après un rejet en relecture)."""
    issue_id = args[0]
    steps = json.loads(Path(args[1]).read_text(encoding="utf-8"))["steps"]
    if not steps:
        raise RuntimeError("aucune étape fournie : rien n'est modifié")
    if guard.paused():
        raise RuntimeError("Agent en pause (AGENT_PAUSE=1) : modification refusée.")
    token = authenticate()
    before = graphql(token, GET_TEST, {"issueId": issue_id})["getTest"]
    backup_dir = guard.ROOT / "reports" / ".backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{before['jira']['key']}-{datetime.now():%Y%m%d-%H%M%S}.json"
    backup.write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
    graphql(token, REMOVE_ALL_STEPS, {"issueId": issue_id})
    for step in steps:
        graphql(token, ADD_STEP, {"issueId": issue_id, "step": step})
    return {"ok": True, "key": before["jira"]["key"], "steps_avant": len(before["steps"]),
            "steps_apres": len(steps), "sauvegarde": str(backup.relative_to(guard.ROOT))}


COMMANDS = {
    "auth": cmd_auth,
    "update-steps": cmd_update_steps,
    "get-test": cmd_get_test,
    "create-test": cmd_create_test,
    "create-test-plan": cmd_create_test_plan,
    "add-tests-to-plan": cmd_add_tests_to_plan,
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    try:
        result = COMMANDS[sys.argv[1]](sys.argv[2:])
    except guard.Stop as exc:
        print(json.dumps({"ok": False, "stop": True, "error": str(exc)}, ensure_ascii=False))
        sys.exit(2)
    except (requests.RequestException, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
