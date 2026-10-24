# Testing Factory

Agent QA piloté par Claude Code : il lit les user stories et les bugs dans Jira, crée les tests Xray, les exécute avec Playwright et envoie les rapports, sous la supervision d'un humain.

## Ce que fait le projet

1. **Génération des tests Xray** : pour chaque story ou bug de l'epic, l'agent conçoit des tests (cas passants, cas d'erreur, cas limites ; non-régression pour un bug), les crée dans Xray avec leurs étapes, ajoute une sous-tâche Gherkin (en anglais) à chaque test et regroupe le tout dans un Test Plan.
2. **Exécution automatisée** : les scénarios Gherkin sont exécutés par Playwright + playwright-bdd.
3. **Rapports** : après chaque exécution, un PDF mis en page et une vidéo résumé de 10 s sont générés. Un rapport Xray quotidien est aussi produit.
4. **Notifications** : email, Slack et Teams, à chaque ticket créé et à chaque rapport.
5. **Humain dans la boucle** :
   - chaque test généré porte le label `a-relire` ; un QA le passe à `valide` ou à `rejete`, et l'agent corrige les tests rejetés ;
   - un frein d'urgence (`AGENT_PAUSE`) arrête l'agent, et une limite de tickets par passage borne ce qu'il crée.

## Structure

| Dossier | Contenu |
|---|---|
| `.claude/skills/test-plan/` | Skill Claude Code (`SKILL.md`) et scripts Python : `xray.py` (API Xray), `notify.py`, `mailer.py`, `slack.py`, `teams.py`, `exec_report.py`, `guard.py` |
| `automation/` | Projet Playwright : `features/` (Gherkin), `steps/` (définitions des étapes), `scripts/` (rendu PDF et captures) |
| `reports/` | Exemples de rapports Xray et de rapports d'exécution (PDF, MP4) |
| `cv/` | Vidéo de présentation du projet et scripts de génération |

## Installation

```bash
pip install -r requirements.txt
cd automation && npm install && npx playwright install chromium
```

Copier `.env.example` en `.env` et remplir les identifiants (Xray, SMTP, webhooks Slack/Teams).

## Utilisation

- **Générer les tests d'une story** : dans Claude Code, `/test-plan SCRUM-123`.
- **Exécuter les tests** : `cd automation && npm test`.
- **Envoyer le rapport d'exécution** : `python .claude/skills/test-plan/exec_report.py --plan SCRUM-<test plan>`.
- **Mettre l'agent en pause** : `python .claude/skills/test-plan/guard.py pause` (et `resume` pour le relancer).

## Stack

Claude Code · Jira + Xray Cloud · Playwright + playwright-bdd (TypeScript) · Python · Slack / Teams / SMTP
