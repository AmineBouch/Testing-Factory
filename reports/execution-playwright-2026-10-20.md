# Rapport d'exécution automatisée – SCRUM-101 (site de démo)

| | |
|---|---|
| **Date** | 20/10/2026, vers 15h10 (heure de Paris) |
| **Story** | [SCRUM-101](https://testingfactory2026.atlassian.net/browse/SCRUM-101) – [DEMO] Parcours client automatisé sur automationexercise.com |
| **Test Plan** | [SCRUM-118](https://testingfactory2026.atlassian.net/browse/SCRUM-118) |
| **Site testé** | https://automationexercise.com (site d'entraînement à l'automatisation) |
| **Outil** | Playwright 1.64 + playwright-bdd 9.2 (Gherkin des sous-tâches Jira) |
| **Navigateur** | Chromium (Desktop Chrome), mode headless, 1 worker, 1 relance en cas d'échec |
| **Durée totale** | 32,4 s |

## Résultat global

| Total | ✅ Réussis | ❌ Échoués | ⏭️ Ignorés | Taux de réussite |
|---|---|---|---|---|
| 8 | 7 | 1 | 0 | **87,5 %** |

## Détail par test

| Test Xray | Scénario | Résultat | Durée |
|---|---|---|---|
| [SCRUM-102](https://testingfactory2026.atlassian.net/browse/SCRUM-102) | Page d'accueil et navigation principale | ✅ PASS | 2,6 s |
| [SCRUM-103](https://testingfactory2026.atlassian.net/browse/SCRUM-103) | Recherche d'un produit avec résultats | ❌ **FAIL** (2 essais) | 6,8 s |
| [SCRUM-104](https://testingfactory2026.atlassian.net/browse/SCRUM-104) | Recherche sans résultat | ✅ PASS | 2,9 s |
| [SCRUM-105](https://testingfactory2026.atlassian.net/browse/SCRUM-105) | Ajout d'un produit au panier | ✅ PASS | 3,9 s |
| [SCRUM-106](https://testingfactory2026.atlassian.net/browse/SCRUM-106) | Suppression d'un produit du panier | ✅ PASS | 3,1 s |
| [SCRUM-107](https://testingfactory2026.atlassian.net/browse/SCRUM-107) | Inscription à la newsletter | ✅ PASS | 2,5 s |
| [SCRUM-108](https://testingfactory2026.atlassian.net/browse/SCRUM-108) | Connexion avec identifiants invalides | ✅ PASS | 2,1 s |
| [SCRUM-109](https://testingfactory2026.atlassian.net/browse/SCRUM-109) | Création puis suppression d'un compte | ✅ PASS | 5,6 s |

## Analyse de l'échec – SCRUM-103

- **Étape en échec :** `And every listed product name contains "dress"`
- **Attendu :** chaque produit trouvé pour « dress » contient « dress » dans son nom.
- **Obtenu :** la recherche renvoie aussi **« Sleeves Top and Short - Blue & Pink »**, qui ne contient pas « dress ».
- **Reproductible :** oui (échec au 1er essai et à la relance) → ce n'est pas un test instable.
- **Diagnostic probable :** la recherche du site ne porte pas seulement sur le nom du produit (sans doute aussi sur la catégorie, ex. « Dress »).
- **Décision à prendre :**
  1. c'est un **défaut** (résultat non pertinent) → créer un Bug et garder le test tel quel ;
  2. c'est le **comportement voulu** → ajuster le critère d'acceptation et le Gherkin de SCRUM-103.
- **Preuves :** capture d'écran, vidéo et trace Playwright dans `automation/test-results/` (dossier « …returns-matching-products-chromium-retry1 »).

## Points d'attention

- Les tests **Bottega Veneta** ne sont **pas automatisables** sur la production : le site bloque les navigateurs automatisés (HTTP 403, anti-robot Akamai). Ils restent en exécution **manuelle**.
- Les publicités du site de démo sont bloquées pendant les tests pour éviter les faux échecs.
- Les données utilisées sont fictives (emails `@example.com`) ; le compte créé par SCRUM-109 est supprimé à la fin du test.
- Les résultats **ne sont pas encore remontés dans Xray** (Test Execution) : prochaine étape.

## Rapport détaillé

Rapport HTML Playwright (étapes, captures, vidéos, traces) : `automation/playwright-report/index.html`
(à ouvrir avec `npm run report` dans le dossier `automation`).
