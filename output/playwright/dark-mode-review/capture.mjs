import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE = 'http://localhost:5001';

const PAGES = [
  ['/', 'dashboard'],
  ['/products', 'products'],
  ['/sellers', 'sellers'],
  ['/ads', 'ads'],
  ['/url-scraper', 'url-scraper'],
  ['/video-transcripts', 'video-transcripts'],
  ['/json-editor', 'json-editor'],
  ['/category-explorer', 'category-explorer'],
];

async function main() {
  const browser = await chromium.launch();

  for (const mode of ['light', 'dark']) {
    for (const [route, name] of PAGES) {
      const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(1000);

      if (mode === 'dark') {
        await page.evaluate(() => {
          document.documentElement.classList.add('dark');
          localStorage.setItem('theme', 'dark');
        });
        await page.waitForTimeout(500);
      }

      const fname = `${name}-${mode}-desktop.png`;
      await page.screenshot({ path: path.join(__dirname, fname), fullPage: false });
      console.log(`  Captured: ${fname}`);

      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForTimeout(300);
      const fnameM = `${name}-${mode}-mobile.png`;
      await page.screenshot({ path: path.join(__dirname, fnameM), fullPage: false });
      console.log(`  Captured: ${fnameM}`);

      await page.close();
    }
  }

  await browser.close();
  console.log('\nDone! All screenshots saved.');
}

main().catch(console.error);
