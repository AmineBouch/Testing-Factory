// Opens a visible Chromium window; the user signs in to Jira themself.
// Once an issue page is loaded, takes sharp 1280x720 (@2x) captures for the CV video.
// Usage: node scripts/capture-jira.mjs <profile-dir> <out-dir>
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const [, , profile, outDir] = process.argv;
const BASE = 'https://testingfactory2026.atlassian.net/browse/';
const SHOTS = [
  ['SCRUM-101', '1-story'],     // user story
  ['SCRUM-102', '2-test'],      // Xray test with steps
  ['SCRUM-110', '3-gherkin'],   // Gherkin sub-task
  ['SCRUM-118', '4-testplan'],  // Xray Test Plan
];
fs.mkdirSync(outDir, { recursive: true });

const ctx = await chromium.launchPersistentContext(profile, {
  headless: false, channel: 'msedge', viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2, locale: 'en-GB',
});
const page = ctx.pages()[0] || (await ctx.newPage());
await page.goto(BASE + 'SCRUM-101');
console.log('WAITING_FOR_LOGIN');

// Wait (up to 15 min) until the real issue page is displayed: the issue summary heading
// only exists once signed in (the login page also has an <h1>, so it is not enough).
const SUMMARY = '[data-testid="issue.views.issue-base.foundation.summary.heading"]';
await page.locator(SUMMARY).waitFor({ timeout: 15 * 60_000 });
await page.waitForTimeout(3000);
console.log('LOGGED_IN');

async function dismissCookies() {
  for (const name of ['Uniquement nécessaires', 'Only necessary', 'Reject all']) {
    const b = page.getByText(name, { exact: true });
    if (await b.count()) { await b.first().click().catch(() => {}); return; }
  }
}

for (const [key, name] of SHOTS) {
  await page.goto(BASE + key);
  await page.locator(SUMMARY).waitFor({ timeout: 60_000 });
  await dismissCookies();
  await page.waitForTimeout(9000); // Xray panels load in iframes
  await page.screenshot({ path: path.join(outDir, `${name}.png`) });
  console.log('CAPTURED', key);
}
await ctx.close();
console.log('DONE');
