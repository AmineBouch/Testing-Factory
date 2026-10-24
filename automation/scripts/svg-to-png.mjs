// Exports an SVG file to PNG at its own size (transparent background kept).
// Usage: node scripts/svg-to-png.mjs <in.svg> <out.png> [scale]
import { chromium } from 'playwright';
import fs from 'node:fs';
const [, , input, output, scale = '1'] = process.argv;
const svg = fs.readFileSync(input, 'utf-8');
const w = Number(svg.match(/width="(\d+)"/)[1]); const h = Number(svg.match(/height="(\d+)"/)[1]);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: Number(scale) });
await p.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
await p.locator('svg').screenshot({ path: output, omitBackground: true });
await b.close();
