# Format d'un cas de test

## Titre

`[<clé story>] <Fonctionnalité> - <ce qui est vérifié>`

Exemples :
- `[SCRUM-6] Forgot password - demande avec un email valide`
- `[SCRUM-6] Forgot password - email au format invalide refusé`
- `[SCRUM-5] Panier - ajout impossible sans sélection de taille`

Le titre dit **ce qui est vérifié**, pas comment.

## Description

Deux ou trois lignes maximum :
- **Objectif** : ce que le test prouve (renvoie au critère d'acceptation).
- **Précondition** (si besoin) : état de départ, ex. « un compte de test existe »,
  « l'utilisateur est déconnecté », « le panier est vide ».

## Étapes

Chaque étape a trois champs :

| Champ | Contenu |
|---|---|
| `action` | Ce que fait le testeur, un verbe à l'impératif : « Cliquer sur… », « Saisir… » |
| `data` | Les données utilisées (email, mot-clé, taille…). Vide si aucune. |
| `result` | Le résultat attendu, **observable et vérifiable** : ce qui s'affiche, change, est reçu. |

Règles :
- Une action par étape. 3 à 8 étapes en général.
- La première étape part d'un point d'entrée clair (URL ou page).
- Chaque étape a un résultat attendu, pas seulement la dernière.
- Pas de résultat vague (« ça marche », « OK ») : décrire ce qu'on voit.
- Données de test génériques et fictives (ex. `test.qa+forgot@example.com`),
  jamais de vraies données personnelles ni de vrais mots de passe.

## Types de tests à couvrir

| Type | Question à se poser |
|---|---|
| Passant | Le parcours nominal décrit dans la story fonctionne-t-il ? |
| Erreur | Que se passe-t-il avec un champ vide, un format invalide, une action interdite ? |
| Limite | Expiration, doublon, valeur maximale, rupture de stock, lien déjà utilisé… |

## Script Gherkin (sous-tâche obligatoire)

Chaque Test a une sous-tâche « Gherkin – <titre en anglais> » qui contient son script.
La sous-tâche est entièrement en anglais : titre, phrase d'intro
(`Gherkin script for test SCRUM-x.`) et Gherkin.

Règles :
- Gherkin **toujours en anglais** (pas de ligne `# language`) :
  `Feature`, `Scenario` (ou `Scenario Outline` + `Examples`),
  `Given`, `When`, `Then`, `And`.
- `Feature:` = le sujet de la story ou du bug en anglais, suivi de sa clé, par ex.
  `Feature: Newsletter subscription (SCRUM-2)`.
- `Scenario:` = ce que le test vérifie, en une phrase.
- Les préconditions de la description deviennent des `Given`.
- Chaque étape du test devient un `When` (action, à la 1re personne : « I click… »)
  suivi d'un `Then` (résultat attendu observable).
- Plusieurs jeux de données (ex. plusieurs emails invalides) → `Scenario Outline`
  avec un tableau `Examples`.
- Les libellés du site restent tels quels (« Forgot password? », « Add to bag »).
- Mêmes données fictives que le test ; jamais de vrai mot de passe.

Exemple :

```gherkin
Feature: Forgotten password reset (SCRUM-6)

  Scenario Outline: The request is rejected with an invalid email format
    Given the "Forgot password?" form is open
    When I enter the email "<email>"
    And I submit
    Then an invalid email format error is displayed
    And no confirmation message is displayed

    Examples:
      | email               |
      | test.qa@@example    |
      | test.qa.example.com |
```

## Exemple complet

```json
{
  "project": "SCRUM",
  "summary": "[SCRUM-6] Forgot password - email au format invalide refusé",
  "description": "Objectif : vérifier que le formulaire refuse un email mal formé (critère 3).\nPrécondition : l'utilisateur est déconnecté.",
  "labels": ["agent-test-plan", "a-relire"],
  "parent": "SCRUM-8",
  "steps": [
    {
      "action": "Ouvrir https://www.bottegaveneta.com/en-en et cliquer sur l'icône compte",
      "data": "",
      "result": "La page de connexion s'affiche"
    },
    {
      "action": "Cliquer sur « Forgot password? »",
      "data": "",
      "result": "Le formulaire de réinitialisation s'affiche avec un champ email"
    },
    {
      "action": "Saisir un email au format invalide et valider",
      "data": "email : test.qa@@example",
      "result": "Un message d'erreur indique que le format de l'email est invalide ; aucun message de confirmation n'apparaît"
    }
  ]
}
```
