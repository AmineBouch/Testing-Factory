// Convertit un fichier HTML en PDF A4 avec le Chromium de Playwright.
// Usage : node scripts/render-pdf.mjs <entree.html> <sortie.pdf> ["<texte du pied de page>"]
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const [, , input, output, footerLabel = "Testing Factory · Rapport d'exécution automatisée"] = process.argv;
if (!input || !output) {
  console.error('usage : node scripts/render-pdf.mjs <entree.html> <sortie.pdf>');
  process.exit(1);
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.resolve(input)).href, { waitUntil: 'load' });
  await page.pdf({
    path: output,
    format: 'A4',
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate:
      '<div style="width:100%;font-size:8px;color:#7A8094;font-family:Segoe UI,Arial;padding:0 14mm;display:flex;justify-content:space-between">' +
      '<span>' + footerLabel + '</span>' +
      '<span>Page <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
    margin: { top: '12mm', bottom: '14mm', left: '12mm', right: '12mm' },
  });
} finally {
  await browser.close();
}
