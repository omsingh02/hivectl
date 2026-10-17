#!/usr/bin/env node
/**
 * Renders the brand social images from docs/brand/social-preview.html:
 *   - docs/brand/social-preview.png  (1280x640, GitHub Social Preview)
 *   - site/og.png                    (1200x630, High-res Open Graph)
 *   - site/og.jpg                    (1200x630, Ultra-compatible TrueColor JPEG <150KB)
 */
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const req = createRequire(path.join(ROOT, 'package.json'));

let playwright;
try {
  playwright = req('playwright');
} catch {
  // Fall back to leery's playwright if not in hivectl
  const leeryReq = createRequire('/home/faulter/dox/repos/leery/package.json');
  playwright = leeryReq('playwright');
}

const { chromium } = playwright;
const htmlPath = path.join(ROOT, 'docs/brand/social-preview.html');
const socialPng = path.join(ROOT, 'docs/brand/social-preview.png');
const ogPng = path.join(ROOT, 'site/og.png');
const ogJpg = path.join(ROOT, 'site/og.jpg');

async function run() {
  console.log('Rendering social previews via headless Chromium...');
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM || '/usr/bin/chromium',
    args: ['--no-sandbox', '--disable-gpu']
  });

  const page = await browser.newPage({ viewport: { width: 1280, height: 640 } });
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: socialPng });

  await page.setViewportSize({ width: 1200, height: 630 });
  await page.goto(pathToFileURL(htmlPath).href + '?og', { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: ogPng });

  await browser.close();

  // Convert to highly-compatible TrueColor JPEG (<150KB)
  execFileSync('magick', [ogPng, '-quality', '92', ogJpg]);

  // Optimize PNGs with optipng if available
  try {
    execFileSync('optipng', ['-quiet', '-o2', socialPng, ogPng]);
  } catch (err) {
    console.warn('optipng not run or skipped:', err.message);
  }

  const sPng = (fs.statSync(socialPng).size / 1024).toFixed(1);
  const sOgPng = (fs.statSync(ogPng).size / 1024).toFixed(1);
  const sOgJpg = (fs.statSync(ogJpg).size / 1024).toFixed(1);

  console.log(`✓ Generated ${socialPng} (${sPng} KB)`);
  console.log(`✓ Generated ${ogPng} (${sOgPng} KB)`);
  console.log(`✓ Generated ${ogJpg} (${sOgJpg} KB)`);
}

run().catch(err => {
  console.error('Export failed:', err);
  process.exit(1);
});
