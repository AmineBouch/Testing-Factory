import { test as base, createBdd } from 'playwright-bdd';

// Domaines publicitaires du site de démo : bloqués pour éviter que des pubs
// plein écran (Google vignette) n'interceptent les clics et rendent les tests instables.
const AD_HOSTS = /googlesyndication|doubleclick|googleadservices|adservice\.google|googletagservices|fundingchoicesmessages/;

type Fixtures = {
  /** Email fictif unique pour ce scénario (newsletter, inscription). */
  uniqueEmail: string;
};

export const test = base.extend<Fixtures>({
  page: async ({ page }, use) => {
    await page.route(AD_HOSTS, (route) => route.abort());
    await use(page);
  },
  uniqueEmail: async ({}, use, testInfo) => {
    await use(`qa.demo+${Date.now()}-${testInfo.workerIndex}@example.com`);
  },
});

export const { Given, When, Then } = createBdd(test);
