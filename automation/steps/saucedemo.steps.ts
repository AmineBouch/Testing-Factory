import { expect, type Locator, type Page } from '@playwright/test';
import { Given, When, Then } from './fixtures';

// Site public de démonstration de Sauce Labs. Le mot de passe de démo est affiché
// sur la page de connexion du site : ce n'est pas un secret.
const SAUCE = 'https://www.saucedemo.com';
const DEMO_PASSWORD = 'secret_sauce';

// Rythme « humain » : ces tests servent aussi à filmer la démo de la vidéo de
// présentation, on laisse donc le temps de voir chaque action.
const PACE = 700;

/** Entoure l'élément en orange, attend un instant, puis rend la main (effet « curseur »). */
async function show(page: Page, target: Locator) {
  await target.scrollIntoViewIfNeeded();
  await target.evaluate((el: HTMLElement) => {
    el.style.outline = '3px solid #E0713A';
    el.style.outlineOffset = '3px';
    el.style.borderRadius = el.style.borderRadius || '4px';
  });
  await page.waitForTimeout(PACE);
  await target.evaluate((el: HTMLElement) => { el.style.outline = ''; });
}

async function type(page: Page, field: Locator, text: string) {
  await show(page, field);
  await field.pressSequentially(text, { delay: 70 });
}

async function click(page: Page, target: Locator) {
  await show(page, target);
  await target.click();
  await page.waitForTimeout(PACE / 2);
}

async function login(page: Page, user: string) {
  await type(page, page.locator('[data-test="username"]'), user);
  await type(page, page.locator('[data-test="password"]'), DEMO_PASSWORD);
  await click(page, page.locator('[data-test="login-button"]'));
}

const item = (page: Page, name: string) =>
  page.locator('[data-test="inventory-item"]').filter({ hasText: name });

// ---------- Connexion ----------

Given('I open the Swag Labs login page', async ({ page }) => {
  await page.goto(SAUCE + '/');
  await expect(page.locator('[data-test="login-button"]')).toBeVisible();
  await page.waitForTimeout(PACE);
});

When('I log in to Swag Labs as {string}', async ({ page }, user: string) => {
  await login(page, user);
});

Given('I am logged in to Swag Labs as {string}', async ({ page }, user: string) => {
  await page.goto(SAUCE + '/');
  await login(page, user);
  await expect(page.locator('[data-test="title"]')).toHaveText('Products');
});

Then('the Swag Labs {string} page is displayed', async ({ page }, title: string) => {
  await expect(page.locator('[data-test="title"]')).toHaveText(title);
  await page.waitForTimeout(PACE);
});

Then('{int} products are listed in the catalogue', async ({ page }, count: number) => {
  await expect(page.locator('[data-test="inventory-item"]')).toHaveCount(count);
  await page.mouse.wheel(0, 500);
  await page.waitForTimeout(PACE * 1.5);
});

Then('the Swag Labs login error says {string}', async ({ page }, message: string) => {
  const error = page.locator('[data-test="error"]');
  await expect(error).toContainText(message);
  await show(page, error);
  await page.waitForTimeout(PACE);
});

// ---------- Catalogue et panier ----------

When('I sort the products by {string}', async ({ page }, option: string) => {
  const sort = page.locator('[data-test="product-sort-container"]');
  await show(page, sort);
  await sort.selectOption({ label: option });
  await page.waitForTimeout(PACE);
});

When('I add {string} to the cart', async ({ page }, name: string) => {
  await click(page, item(page, name).getByRole('button', { name: 'Add to cart' }));
});

Then('the cart badge shows {int}', async ({ page }, count: number) => {
  const badge = page.locator('[data-test="shopping-cart-badge"]');
  await expect(badge).toHaveText(String(count));
  await show(page, badge);
});

When('I open the Swag Labs cart', async ({ page }) => {
  await click(page, page.locator('[data-test="shopping-cart-link"]'));
  await expect(page.locator('[data-test="title"]')).toHaveText('Your Cart');
});

Then('the cart lists {string} and {string}', async ({ page }, first: string, second: string) => {
  const names = page.locator('[data-test="inventory-item-name"]');
  await expect(names).toHaveText([first, second], { useInnerText: true });
  await page.waitForTimeout(PACE * 1.5);
});

// ---------- Commande ----------

When('I check out as {string} {string} with postal code {string}',
  async ({ page }, first: string, last: string, zip: string) => {
    await click(page, page.locator('[data-test="checkout"]'));
    await type(page, page.locator('[data-test="firstName"]'), first);
    await type(page, page.locator('[data-test="lastName"]'), last);
    await type(page, page.locator('[data-test="postalCode"]'), zip);
    await click(page, page.locator('[data-test="continue"]'));
  });

Then('the order overview shows the total', async ({ page }) => {
  const total = page.locator('[data-test="total-label"]');
  await expect(total).toContainText('Total: $');
  await show(page, total);
});

When('I finish the order', async ({ page }) => {
  await click(page, page.locator('[data-test="finish"]'));
});

Then('the Swag Labs confirmation {string} is displayed', async ({ page }, message: string) => {
  const header = page.locator('[data-test="complete-header"]');
  await expect(header).toHaveText(message);
  await page.waitForTimeout(PACE * 2);
});
