// Sonde ponctuelle du site d'entraînement automationexercise.com :
// vérifie l'accès et liste les éléments utiles pour écrire les sélecteurs.
import { chromium } from '@playwright/test';

const browser = await chromium.launch();
const page = await browser.newPage();
const resp = await page.goto('https://automationexercise.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(3000);

const texts = (sel, n = 30) => page.locator(sel).evaluateAll(
  (els, n) => els.map(e => (e.getAttribute('aria-label') || e.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, n), n);

const out = {
  status: resp?.status(),
  title: await page.title(),
  consentButtons: await page.getByRole('button', { name: /consent|accept|agree|do not consent/i }).allInnerTexts(),
  headerNav: await texts('.shop-menu a'),
  hasSubscribe: await page.locator('#susbscribe_email').count(),
  footer: await texts('footer h2'),
};
console.log(JSON.stringify(out, null, 2));

// Pages clés
for (const path of ['/products', '/login', '/view_cart']) {
  const r = await page.goto('https://automationexercise.com' + path, { waitUntil: 'domcontentloaded' });
  console.log(path, r?.status(), await page.title());
}
await page.goto('https://automationexercise.com/products');
console.log('search input:', await page.locator('#search_product').count(), '| products:', await page.locator('.productinfo').count());
await page.goto('https://automationexercise.com/login');
console.log('signup form:', await page.locator('[data-qa="signup-name"]').count(), await page.locator('[data-qa="signup-email"]').count(),
  '| login form:', await page.locator('[data-qa="login-email"]').count());
await page.screenshot({ path: 'test-results/probe-demo.png' });
await browser.close();
