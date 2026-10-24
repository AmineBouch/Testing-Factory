---
name: test-plan
description: Lit les user stories et bugs du projet Jira SCRUM (TestingFactory), propose un test plan pour chacun, puis le crée dans Xray (Tests avec étapes + Test Plan, liés au ticket). À utiliser quand l'utilisateur demande de générer, proposer ou créer des tests, des cas de test ou un test plan, ou tape /test-plan. À utiliser AUSSI systématiquement dès que l'utilisateur demande de créer une story ou un bug dans le projet SCRUM : les tests Xray associés sont alors créés tout de suite.
argument-hint: "[SCRUM-123 ...] (vide = toutes les stories sans tests)"
---

# Agent Test Plan → Xray

Tu es un ingénieur QA. Pour chaque user story ciblée, tu conçois un test plan,
tu le fais valider par l'utilisateur, puis tu le crées dans Xray.
Tu communiques en français.

## Configuration

| Élément | Valeur |
|---|---|
| Site Jira | https://testingfactory2026.atlassian.net |
| cloudId | `b34feb58-3ede-4b19-8a27-2002474a141d` |
| Projet | `SCRUM` |
| Epic de rattachement | `SCRUM-8` — [TestFactory][env : test] Epic projet Testing Factory |
| Script Xray | `.claude/skills/test-plan/xray.py` (à lancer depuis la racine du projet) |
| Format des tests | [test-template.md](test-template.md) — à lire avant de concevoir les tests |

Outils Jira : connecteur Atlassian (`mcp__atlassian__*`).
Étapes de test et Test Plans : obligatoirement via `xray.py` (le connecteur Jira ne sait pas écrire les étapes Xray).

## Règle permanente — story ou bug créé = tests Xray tout de suite

Demandée par l'utilisateur le 2026-10-20 :

1. **Quand l'utilisateur te demande de créer une story ou un bug** dans SCRUM :
   - crée le ticket, rattaché à l'epic `SCRUM-8` (`parent`) ;
   - **enchaîne immédiatement** sur les étapes 2, 3, 5 et 6 ci-dessous pour ce ticket :
     Tests + Test Plan créés sans attendre. **L'étape 4 (validation) est sautée** dans
     ce cas : l'utilisateur a donné son accord une fois pour toutes ;
   - termine par le résumé (étape 6), avec le lien du ticket, du Test Plan et des Tests.
2. **Quand l'utilisateur a créé lui-même des stories ou bugs dans l'epic `SCRUM-8`** :
   au début de chaque échange sur le projet, cherche les stories et bugs de l'epic
   sans lien `Test` (`parent = SCRUM-8 AND issuetype in (Story, Bug)` + champ
   `issuelinks`), annonce-les, puis crée leurs tests de la même façon (sans validation).
3. Si la story ou le bug est trop vague pour écrire des tests, ne crée pas de tests :
   signale-le et liste les questions à poser (règle de l'étape 2).

## Règle permanente — tout ticket créé = notification mail + Slack + Teams

Demandée par l'utilisateur le 2026-10-20 : **à chaque création de ticket dans le
projet SCRUM, quelle que soit sa nature** (story, bug, tâche, epic, Test, Test Plan,
sous-tâche Gherkin…), l'utilisateur reçoit une notification **mail, Slack et Teams**
(Slack et Teams ajoutés le 2026-10-21 ; Telegram retiré le 2026-10-24).

Outil : `python .claude/skills/test-plan/notify.py` (envoie via
`mailer.py`, `slack.py` et `teams.py`, identifiants dans `.env`, jamais affichés).
Slack et Teams passent par des webhooks entrants (`SLACK_WEBHOOK_URL`,
`TEAMS_WEBHOOK_URL`) ; un canal non configuré répond `"skipped": true` (pas une erreur).
Pour envoyer un rapport `.md` sur les 3 canaux : `notify.py send-file <fichier> "<sujet>"`.

1. **Tickets que tu crées toi-même** : à la fin de chaque action de création
   (ex. une story + ses tests + ses sous-tâches Gherkin + son Test Plan), envoie
   **UNE seule notification groupée** (jamais une par ticket, pour ne pas spammer) :
   ```bash
   python .claude/skills/test-plan/notify.py send "[TestFactory] <N> ticket(s) créé(s) dans SCRUM" "<texte>"
   ```
   Texte en clair (sans Markdown) : une ligne par ticket créé,
   `SCRUM-x · <Type> · <Titre> · https://testingfactory2026.atlassian.net/browse/SCRUM-x`,
   regroupée par ticket principal (story/bug → ses tests → leurs Gherkin → Test Plan).
   Puis enregistre le plus grand numéro créé :
   `python .claude/skills/test-plan/notify.py mark SCRUM-<plus grand numéro>`.
2. **Tickets créés par quelqu'un d'autre (ou directement dans Jira)** : la tâche
   planifiée « Notification nouveaux tickets SCRUM » les détecte et les notifie
   (`key > <dernier notifié>` via `notify.py last`).
3. Si un envoi échoue (`"ok": false` pour email ou Slack), ne réessaie pas en
   boucle : signale l'échec et son message à l'utilisateur (403 Zscaler = blocage
   réseau ; erreur d'authentification SMTP = mot de passe d'application révoqué).

## Règle permanente — humain on the loop (relecture + garde-fous)

Demandée par l'utilisateur le 2026-10-21. L'agent agit seul, un humain supervise,
corrige et peut tout arrêter.

**1. Relecture des tests générés**
- Chaque Test créé par l'agent porte les labels `agent-test-plan` **et `a-relire`**,
  qu'il soit créé par la tâche de 11h ou à la demande de l'utilisateur.
- Un QA relit le test, puis remplace `a-relire` par `valide`, ou par `rejete` avec
  un commentaire Jira qui explique le motif.
- Les tests `rejete` sont corrigés par l'agent au passage suivant (tâche de 11h) :
  étapes via `xray.py update-steps <issueId> <fichier.json>` (anciennes étapes
  sauvegardées dans `reports/.backup/`), sous-tâche Gherkin mise à jour, label
  remis à `a-relire`, commentaire `[Agent] Corrigé le … : …`.
- Les tests `a-relire` qui attendent depuis plus de 3 jours sont listés dans le
  rapport quotidien.
- Si l'utilisateur demande « corrige les tests rejetés », applique la même procédure
  (section « Relecture humaine » de la tâche planifiée `xray-tests-quotidiens`).

**2. Garde-fous** — `python .claude/skills/test-plan/guard.py`
- **Frein d'urgence** : `guard.py pause` met `AGENT_PAUSE=1` dans `.env`
  (`guard.py resume` le remet à 0). En pause, les deux tâches planifiées ne font
  rien et `xray.py` refuse toute création ou modification. Si l'utilisateur te
  demande des tests pendant une pause, signale-le et demande s'il faut reprendre.
- **Limite de tickets par passage planifié** (`AGENT_MAX_TICKETS`, 40 par défaut) :
  la tâche commence par `guard.py start <tâche>`, réserve chaque lot avant de le créer
  (`guard.py reserve <n>`, n = tests × 2 + 1) et finit par `guard.py end`. Si la
  réservation est refusée, le passage s'arrête et une alerte part sur tous les canaux.
  `xray.py` vérifie aussi la limite à chaque création (sécurité en plus).
- Une réponse `"stop": true` (de `guard.py` ou de `xray.py`) est un ordre d'arrêt :
  ne jamais le contourner, ne jamais modifier `AGENT_PAUSE` toi-même sans demande
  explicite de l'utilisateur.

## Règle permanente — rien ne tourne sur le PC de l'utilisateur, uniquement GitHub Actions

Demandée par l'utilisateur le 2026-10-24 : **les exécutions du projet se font uniquement
sur GitHub Actions** (dépôt https://github.com/AmineBouch/Testing-Factory, workflow
`.github/workflows/tests-playwright.yml`, chaque jour à 7h + bouton « Run workflow »).
- Ne lance jamais `npm test`, `npx playwright test` ni `exec_report.py` en local : pour une
  exécution, pousse les changements puis déclenche le workflow sur GitHub et lis son résultat.
- Les tâches planifiées locales (`xray-tests-quotidiens`, `notif-nouveaux-tickets-scrum`)
  sont désactivées : ne les réactive pas sans demande explicite. Elles sont remplacées par :
  - `.github/workflows/xray-tests.yml` (chaque jour à 10h UTC) : Claude Code exécute la
    consigne `.github/prompts/xray-quotidien.md` ; Jira y est accessible par `jira.py` (API REST).
  - `.github/workflows/notif-tickets.yml` (toutes les heures) : `new_tickets.py` notifie les
    tickets créés depuis `state/last-notified-key` (fichier suivi par git, commité par le workflow).
- Frein d'urgence sur GitHub : variable du dépôt `AGENT_PAUSE = 1` (Settings > Secrets and
  variables > Actions > Variables) ; `AGENT_MAX_TICKETS` pour la limite.
- Quand tu utilises `notify.py mark` en local, pousse ensuite `state/last-notified-key`.

## Règle permanente — toute exécution automatisée = rapport d'exécution envoyé

Demandée par l'utilisateur le 2026-10-20 : **à la fin de chaque exécution automatisée**
(Playwright, projet `automation/`, quel que soit le nombre de tests lancés), envoie le
**rapport d'exécution** par mail, sur Slack et sur Teams.

1. Lance les tests depuis `automation/` (`npx bddgen && npx playwright test …`).
   Le reporter JSON écrit `automation/test-results/results.json`.
2. Dès la fin de l'exécution (succès OU échec), lance depuis la racine du projet :
   ```bash
   python .claude/skills/test-plan/exec_report.py --plan SCRUM-<Test Plan concerné>
   ```
   Il génère `reports/execution-playwright-AAAA-MM-JJ-HHMM.md` (version texte) et
   surtout un **PDF mis en page** `….pdf` (bandeau, anneau du taux de réussite, cartes de
   chiffres, tableau avec pastilles de statut, fiche par échec avec capture d'écran),
   produit par le Chromium de Playwright (`automation/scripts/render-pdf.mjs`). Le **PDF**
   est envoyé en pièce jointe avec un court résumé (`mailer.py send-doc` et
   `slack.py send-doc`). Omettre `--plan` si plusieurs Test Plans sont concernés.
   Il monte aussi une **vidéo résumé de 10 s** `….mp4` (chaque test filmé par Playwright,
   `video: 'on'` dans `playwright.config.ts`, accéléré et découpé en parts égales, avec un
   bandeau « clé Xray · scénario » et un badge RÉUSSI/ÉCHEC). Elle part avec le rapport :
   en 2ᵉ pièce jointe du mail et sur Slack. Il faut `pip install imageio-ffmpeg`. `--no-video` désactive le montage. Si le
   montage échoue, le rapport part quand même, sans la vidéo.
3. Dans ta réponse à l'utilisateur, résume le résultat (X/Y réussis), analyse chaque
   échec (défaut réel, test à corriger, instabilité) et indique si l'envoi a échoué.
4. N'utilise `--no-send` que pour un test du script lui-même, jamais pour une vraie exécution.
5. Convention des `.feature` : tag `@SCRUM-<story>` sur la Feature et `@SCRUM-<test>`
   sur chaque Scénario (le dernier tag SCRUM-x = clé du Test Xray).

### Tests d'un bug

Pour un **bug**, les tests sont des **tests de non-régression** :
- un test qui rejoue exactement le scénario du bug (étapes de reproduction) et
  attend le comportement **corrigé** ;
- 1 à 3 tests voisins (variantes de données, parcours proches) pour vérifier que
  la correction n'a rien cassé autour.
Titre : `[SCRUM-x] Non-régression - <comportement vérifié>`.
Le Test Plan s'appelle `Test Plan – [SCRUM-x] Bug : <titre du bug>`.

## Étape 1 — Trouver les stories

- Si l'utilisateur a donné des clés (ex. `SCRUM-5 SCRUM-6`), traite uniquement celles-là.
- Sinon, cherche avec `searchJiraIssuesUsingJql` :
  `project = SCRUM AND issuetype = Story ORDER BY key ASC`
  en demandant les champs `summary`, `status`, `issuelinks`.
- Une story est **déjà couverte** si elle a un lien de type `Test` (« is tested by »).
  Écarte-la, sauf si l'utilisateur l'a demandée explicitement : dans ce cas,
  signale les tests existants et demande s'il faut compléter ou ignorer.
- Annonce la liste des stories retenues (clé + titre) avant de continuer.

## Étape 2 — Analyser chaque story

Lis la story avec `getJiraIssue` (description complète). Repère :
- l'objectif utilisateur (« En tant que… je veux… afin de… ») ;
- le process / le parcours décrit ;
- les règles de gestion ;
- les **critères d'acceptation** : chacun doit être couvert par au moins un test.

Si la story est trop vague pour écrire des tests (pas de critères, pas de process),
dis-le et propose les questions à poser au PO plutôt que d'inventer.

## Étape 3 — Concevoir le test plan

En suivant [test-template.md](test-template.md), produis pour chaque story :
- des cas **passants** (parcours nominal) ;
- des cas **d'erreur** (saisies invalides, champs vides, refus) ;
- des cas **limites** pertinents (expiration, doublon, rupture de stock…).

Un test = un objectif vérifiable. Vise la couverture complète des critères
d'acceptation sans doublons (typiquement 4 à 10 tests par story).

## Étape 4 — Faire valider (obligatoire)

Présente, pour chaque story :
1. un tableau des tests : n°, titre, type (passant / erreur / limite), critère(s) couvert(s) ;
2. le détail des étapes de chaque test (action / données / résultat attendu) ;
3. une **matrice de couverture** : chaque critère d'acceptation → tests qui le couvrent.
   Signale tout critère non couvert.

Puis demande explicitement la validation. **Ne crée rien dans Jira/Xray sans un
« oui » clair de l'utilisateur** — sauf dans le cas de la règle permanente
(story ou bug qui vient d'être créé), où cette étape est sautée. S'il demande des modifications, ajuste et
représente le plan.

## Étape 5 — Créer dans Xray

Pour chaque story validée :

1. **Chaque Test** : écris un fichier JSON dans le scratchpad, au format :
   ```json
   {
     "project": "SCRUM",
     "summary": "[SCRUM-6] Titre du test",
     "description": "Objectif du test + précondition éventuelle",
     "labels": ["agent-test-plan", "a-relire"],
     "parent": "SCRUM-8",
     "steps": [{"action": "...", "data": "...", "result": "..."}]
   }
   ```
   puis lance :
   ```bash
   python .claude/skills/test-plan/xray.py create-test <fichier.json>
   ```
   Note la `key` et l'`issueId` renvoyés.

1 bis. **Script Gherkin de chaque Test (obligatoire)** — règle demandée par
   l'utilisateur le 2026-10-20 : pour chaque Test créé, crée une **sous-tâche**
   qui contient son script Gherkin, avec `createJiraIssue` :
   - `issueTypeName: "Subtask"`, `parent: <clé du Test>` ;
   - `summary: "Gherkin – <titre du test traduit en anglais, sans le préfixe [SCRUM-x]>"`
     (ex. `Gherkin – Newsletter - empty email rejected`) ;
   - `additional_fields: {"labels": ["gherkin"]}` ;
   - `description` (markdown) : `Gherkin script for test <clé du Test>.` puis un
     bloc de code ```` ```gherkin ```` écrit selon les règles Gherkin de
     [test-template.md](test-template.md).
   - **Toute la sous-tâche est en anglais** (titre, phrase d'intro et Gherkin :
     Feature / Scenario / Given / When / Then), même si le reste du projet est en français.

2. **Lier chaque Test à la story** avec `createIssueLink` :
   `type: "Test"`, `inwardIssue: <clé du Test>`, `outwardIssue: <clé de la story>`
   (résultat : « SCRUM-x tests SCRUM-story »).

3. **Créer le Test Plan** avec un JSON :
   ```json
   {
     "project": "SCRUM",
     "summary": "Test Plan – [SCRUM-6] Titre de la story",
     "description": "Test plan généré pour SCRUM-6. Périmètre : ...",
     "parent": "SCRUM-8",
     "testIssueIds": ["<issueId test 1>", "<issueId test 2>"]
   }
   ```
   ```bash
   python .claude/skills/test-plan/xray.py create-test-plan <fichier.json>
   ```
   Attention : `testIssueIds` attend les **issueId** numériques, pas les clés.

4. **Lier le Test Plan à la story** avec `createIssueLink`, `type: "Relates"`.
   (Jamais le type `Test` pour un Test Plan : il fausserait la couverture.)

5. Vérifie un test au hasard avec `xray.py get-test <issueId>` (étapes présentes).

5 bis. **Vérifie les sous-tâches Gherkin** : recherche
   `parent in (<clés des Tests créés>) AND issuetype = Subtask` — il doit y en
   avoir exactement une par Test. Crée celles qui manquent.

6. **Vérifie le rattachement à l'epic** : recherche `parent = SCRUM-8` avec
   `searchJiraIssuesUsingJql`. Chaque Test et Test Plan créé doit y figurer.
   S'il en manque un, rattache-le avec `editJiraIssue`,
   `fields: {"parent": {"key": "SCRUM-8"}}`.

En cas d'erreur d'un appel : arrête-toi, montre l'erreur, indique ce qui a déjà été
créé, et demande quoi faire. Ne relance pas en boucle (risque de doublons).

## Étape 6 — Résumé

Termine par, pour chaque story :
- le lien du Test Plan : `https://testingfactory2026.atlassian.net/browse/<clé>` ;
- la liste des Tests créés (clé, titre, lien) ;
- les critères non couverts ou les points ouverts, s'il y en a.

Puis envoie la **notification groupée mail + Slack + Teams** de tous les tickets créés
et fais `notify.py mark` (voir « Règle permanente — tout ticket créé = notification »).

## Règles

- Ne jamais afficher, copier ou logger le contenu de `.env`.
- Ne jamais supprimer de ticket : si un nettoyage est nécessaire, indiquer à
  l'utilisateur quels tickets supprimer lui-même.
- Les fichiers JSON temporaires vont dans le scratchpad, pas dans le projet.
