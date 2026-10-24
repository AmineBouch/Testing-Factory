import { expect } from '@playwright/test';
import type { DataTable } from 'playwright-bdd';
import { Given, When, Then } from './fixtures';

const DEMO = 'https://automationexercise.com';

// ---------- Navigation ----------

Given('I am on the demo home page', async ({ page }) => {
  await page.goto(DEMO + '/');
});

Given('I am on the products page', async ({ page }) => {
  await page.goto(DEMO + '/products');
  await expect(page.locator('#search_product')).toBeVisible();
});

Given('I am on the login page', async ({ page }) => {
  await page.goto(DEMO + '/login');
});

Then('the page title is {string}', async ({ page }, title: string) => {
  await expect(page).toHaveTitle(title);
});

Then('the header menu shows the links:', async ({ page }, table: DataTable) => {
  const menu = page.locator('.shop-menu');
  for (const { link } of table.hashes()) {
    await expect(menu.getByRole('link', { name: link })).toBeVisible();
  }
});

// ---------- Recherche ----------

When('I search for {string}', async ({ page }, keyword: string) => {
  await page.locator('#search_product').fill(keyword);
  await page.locator('#submit_search').click();
});

Then('the {string} section is displayed', async ({ page }, title: string) => {
  await expect(page.locator('h2.title', { hasText: title })).toBeVisible();
});

const productNames = (page) => page.locator('.features_items .productinfo p');

Then('at least one product is listed', async ({ page }) => {
  await expect(productNames(page).first()).toBeVisible();
});

Then('no product is listed', async ({ page }) => {
  await expect(productNames(page)).toHaveCount(0);
});

Then('every listed product name contains {string}', async ({ page }, keyword: string) => {
  const names = await productNames(page).allInnerTexts();
  expect(names.length).toBeGreaterThan(0);
  for (const name of names) {
    expect(name.toLowerCase()).toContain(keyword.toLowerCase());
  }
});

// ---------- Panier ----------

When('I add the first product to the cart', async ({ page }) => {
  await page.locator('.productinfo a.add-to-cart').first().click();
  await expect(page.locator('#cartModal')).toBeVisible();
  await page.locator('#cartModal button.close-modal').click();
});

When('I open the cart', async ({ page }) => {
  await page.goto(DEMO + '/view_cart');
});

const cartRows = (page) => page.locator('#cart_info_table tbody tr');

Then('the cart contains {int} product', async ({ page }, count: number) => {
  await expect(cartRows(page)).toHaveCount(count);
});

Then('the product line shows a price and quantity {int}', async ({ page }, qty: number) => {
  const row = cartRows(page).first();
  await expect(row.locator('.cart_price p')).toHaveText(/Rs\.\s*\d+/);
  await expect(row.locator('.cart_quantity button')).toHaveText(String(qty));
});

When('I remove the product from the cart', async ({ page }) => {
  await cartRows(page).first().locator('.cart_quantity_delete').click();
});

// ---------- Newsletter ----------

When('I subscribe to the newsletter with a unique email', async ({ page, uniqueEmail }) => {
  await page.locator('#susbscribe_email').fill(uniqueEmail);
  await page.locator('#subscribe').click();
});

// ---------- Compte ----------

When('I log in with email {string} and password {string}', async ({ page }, email: string, password: string) => {
  await page.locator('[data-qa="login-email"]').fill(email);
  await page.locator('[data-qa="login-password"]').fill(password);
  await page.locator('[data-qa="login-button"]').click();
});

When('I sign up as {string} with a unique email', async ({ page, uniqueEmail }, name: string) => {
  await page.locator('[data-qa="signup-name"]').fill(name);
  await page.locator('[data-qa="signup-email"]').fill(uniqueEmail);
  await page.locator('[data-qa="signup-button"]').click();
  await expect(page.getByText('Enter Account Information')).toBeVisible();
});

When('I fill in the account information form with valid fictitious data', async ({ page }) => {
  await page.locator('#id_gender1').check();
  await page.locator('[data-qa="password"]').fill('QaDemo#2026');
  await page.locator('[data-qa="days"]').selectOption('15');
  await page.locator('[data-qa="months"]').selectOption('6');
  await page.locator('[data-qa="years"]').selectOption('1990');
  await page.locator('[data-qa="first_name"]').fill('QA');
  await page.locator('[data-qa="last_name"]').fill('Demo');
  await page.locator('[data-qa="address"]').fill('1 Test Street');
  await page.locator('[data-qa="country"]').selectOption('Canada');
  await page.locator('[data-qa="state"]').fill('Ontario');
  await page.locator('[data-qa="city"]').fill('Toronto');
  await page.locator('[data-qa="zipcode"]').fill('M5V 2T6');
  await page.locator('[data-qa="mobile_number"]').fill('+15550000000');
});

When('I submit the account creation form', async ({ page }) => {
  await page.locator('[data-qa="create-account"]').click();
});

When('I continue', async ({ page }) => {
  await page.locator('[data-qa="continue-button"]').click();
});

Then('I am logged in as {string}', async ({ page }, name: string) => {
  await expect(page.locator('.shop-menu')).toContainText(`Logged in as ${name}`);
});

When('I delete my account', async ({ page }) => {
  await page.locator('.shop-menu a[href="/delete_account"]').click();
});

// ---------- Commun ----------

Then('the message {string} is displayed', async ({ page }, message: string) => {
  await expect(page.getByText(message).first()).toBeVisible();
});
