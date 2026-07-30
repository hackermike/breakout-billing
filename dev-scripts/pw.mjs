// Resolve Playwright no matter how it was installed — local node_modules, a
// global install, or the npx cache (`npx playwright ...` leaves it under
// ~/.npm/_npx/<hash>/). Import this instead of hardcoding that hashed path.
//
//   import { chromium } from '../../dev-scripts/pw.mjs';   // from scripts/dev/
//   import { chromium } from './pw.mjs';                   // from dev-scripts/
import { existsSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { join } from 'node:path';

function resolveEntry() {
  const require = createRequire(import.meta.url);
  try {
    return require.resolve('playwright');
  } catch {
    // fall through to the npx cache
  }
  const cache = join(homedir(), '.npm', '_npx');
  if (existsSync(cache)) {
    for (const dir of readdirSync(cache)) {
      const candidate = join(cache, dir, 'node_modules', 'playwright', 'index.mjs');
      if (existsSync(candidate)) return candidate;
    }
  }
  throw new Error('Playwright not found. Run: npx playwright install chromium');
}

const playwright = await import(resolveEntry());
export const { chromium, firefox, webkit } = playwright;
export default playwright;
