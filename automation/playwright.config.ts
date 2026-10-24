import { defineConfig, devices } from '@playwright/test';
import { defineBddConfig } from 'playwright-bdd';

// Les fichiers .feature sont générés en specs Playwright dans .features-gen/
const testDir = defineBddConfig({
  features: 'features/**/*.feature',
  steps: 'steps/**/*.ts',
});

export default defineConfig({
  testDir,
  // Site de production tiers : on reste sobre (pas de parallélisme agressif).
  workers: 1,
  retries: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    // Lu par .claude/skills/test-plan/exec_report.py pour le rapport d'exécution.
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  use: {
    baseURL: 'https://www.bottegaveneta.com',
    locale: 'en-GB',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // Vidéo de chaque test : sert au montage de 10 s envoyé avec le rapport d'exécution.
    video: { mode: 'on', size: { width: 1280, height: 720 } },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
