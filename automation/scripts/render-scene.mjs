// Renders a CSS-animated HTML scene to PNG frames (sharp output, exact timing).
// Usage: node scripts/render-scene.mjs <scene.html> <out-dir> <seconds> [fps]
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';

const [, , input, outDir, seconds, fpsArg] = process.argv;
const fps = Number(fpsArg || 25);
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto(pathToFileURL(path.resolve(input)).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const total = Math.round(Number(seconds) * fps);
  for (let i = 0; i < total; i++) {
    const t = (i * 1000) / fps;
    await page.evaluate((ms) => {
      for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; }
    }, t);
    await page.screenshot({ path: path.join(outDir, `f${String(i).padStart(4, '0')}.png`) });
  }
} finally {
  await browser.close();
}
