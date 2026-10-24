// Capture une image d’une scène animée à un instant donné (contrôle visuel avant rendu).
// Usage : node scripts/snap-scene.mjs <dossier> <scene.html>@<ms> [...]
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
const [, , outDir, ...items] = process.argv;
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
for (const it of items) {
  const [file, ms] = it.split('@');
  await p.goto(pathToFileURL(file).href); await p.evaluate(() => document.fonts.ready);
  await p.evaluate((t) => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = t; } }, Number(ms));
  await p.screenshot({ path: `${outDir}/${file.split(/[\/]/).pop().replace('.html','')}-${ms}.png` });
}
await b.close();
