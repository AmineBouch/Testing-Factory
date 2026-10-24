// Sonde ponctuelle : ouvre la page d'accueil et résume ce qu'on y trouve
// (bannière cookies, header, menu, footer) pour écrire des sélecteurs fiables.
import { chromium } from '@playwright/test';

const browser = await chromium.launch();
const page = await browser.newPage({ locale: 'en-GB' });
const resp = await page.goto('https://www.bottegaveneta.com/en-en', { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(5000);

const out = {
  status: resp?.status(),
  url: page.url(),
  title: await page.title(),
  cookieButtons: await page.getByRole('button', { name: /accept|reject|refuse|cookie|allow|decline/i }).allInnerTexts(),
  oneTrust: await page.locator('#onetrust-banner-sdk').count(),
  headerCount: await page.locator('header').count(),
  headerLinks: (await page.locator('header a, header button').evaluateAll(els =>
    els.map(e => (e.getAttribute('aria-label') || e.textContent || '').trim()).filter(Boolean))).slice(0, 40),
  navLinks: (await page.locator('nav a').evaluateAll(els => els.map(e => e.textContent.trim()).filter(Boolean))).slice(0, 30),
  footerCount: await page.locator('footer').count(),
  footerLinks: (await page.locator('footer a').evaluateAll(els => els.map(e => e.textContent.trim()).filter(Boolean))).slice(0, 30),
  captchaHint: /captcha|access denied|are you a robot|blocked/i.test(await page.content()),
};
console.log(JSON.stringify(out, null, 2));
await page.screenshot({ path: 'test-results/probe-home.png' });
await browser.close();
