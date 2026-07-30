// Screenshot a page for quick visual verification.
//
//   node dev-scripts/screenshot.mjs http://localhost:8000/reports
//   node dev-scripts/screenshot.mjs http://localhost:8000/calendar /tmp/cal.png 800
//
// For interactive flows (clicking, filling forms) write a one-off script in
// scripts/dev/ that imports { chromium } from ../../dev-scripts/pw.mjs.
import { chromium } from './pw.mjs';

const [, , url, out = '/tmp/bb-shot.png', wait = '500'] = process.argv;
if (!url) {
  console.error('usage: node dev-scripts/screenshot.mjs <url> [outfile] [waitMs]');
  process.exit(1);
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(Number(wait));
await page.screenshot({ path: out });
await browser.close();
console.log('screenshot ->', out);
