# Rapport d'exécution automatisée – 20/10/2026 15:51

| | |
|---|---|
| **Date** | 20/10/2026 à 15:51 (heure locale) |
| **Story / ticket** | [SCRUM-101](https://testingfactory2026.atlassian.net/browse/SCRUM-101) |
| **Test Plan** | [SCRUM-118](https://testingfactory2026.atlassian.net/browse/SCRUM-118) |
| **Outil** | Playwright + playwright-bdd (Gherkin des sous-tâches Jira) |
| **Navigateur(s)** | chromium |
| **Durée totale** | 33,7 s |

## Résultat global

| Total | ✅ Réussis | ⚠️ Instables | ❌ Échoués | ⏭️ Ignorés | Taux de réussite |
|---|---|---|---|---|---|
| 8 | 7 | 0 | 1 | 0 | **87,5 %** |

## Détail par test

| Test Xray | Scénario | Résultat | Essais | Durée |
|---|---|---|---|---|
| [SCRUM-102](https://testingfactory2026.atlassian.net/browse/SCRUM-102) | Home page loads with the main navigation | ✅ PASS | 1 | 3,2 s |
| [SCRUM-103](https://testingfactory2026.atlassian.net/browse/SCRUM-103) | Product search returns matching products | ❌ **FAIL** | 2 | 7,3 s |
| [SCRUM-104](https://testingfactory2026.atlassian.net/browse/SCRUM-104) | Product search with no match shows no products | ✅ PASS | 1 | 2,8 s |
| [SCRUM-105](https://testingfactory2026.atlassian.net/browse/SCRUM-105) | A product added to the cart is shown with its price and quantity | ✅ PASS | 1 | 2,3 s |
| [SCRUM-106](https://testingfactory2026.atlassian.net/browse/SCRUM-106) | A product removed from the cart is no longer listed | ✅ PASS | 1 | 4,6 s |
| [SCRUM-107](https://testingfactory2026.atlassian.net/browse/SCRUM-107) | Newsletter subscription with a valid email | ✅ PASS | 1 | 2,5 s |
| [SCRUM-108](https://testingfactory2026.atlassian.net/browse/SCRUM-108) | Login with invalid credentials is rejected | ✅ PASS | 1 | 1,7 s |
| [SCRUM-109](https://testingfactory2026.atlassian.net/browse/SCRUM-109) | Create an account then delete it | ✅ PASS | 1 | 6,1 s |

## Échecs

### SCRUM-103 – Product search returns matching products

```
Error: expect(received).toContain(expected) // indexOf

Expected substring: "dress"
Received string:    "sleeves top and short - blue & pink"
```
Preuves (capture, vidéo, trace) : `automation/test-results/`.


## Rapport détaillé
Rapport HTML Playwright : `automation/playwright-report/index.html` (`npm run report` dans le dossier `automation`).
