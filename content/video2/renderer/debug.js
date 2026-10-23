// Capture console errors + per-scene crops so the failing scene can be seen at
// full resolution instead of guessed at.
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const { chromium } = require('playwright-core');
const exe = process.env.CHROME_PATH || require('os').homedir() + '/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome';

(async () => {
  const html = fs.readFileSync(path.join(ROOT, 'content/video2/renderer/frames.html'), 'utf8');
  const plan = JSON.parse(fs.readFileSync(path.join(ROOT, 'content/video2/plan.preview.json'), 'utf8'));
  const browser = await chromium.launch({ executablePath: exe });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  page.on('console', m => console.log('[page]', m.type(), m.text()));
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(p => window.setPlan(p), plan);
  for (const t of [3.2, 4.4, 15.0, 20.5]) {
    const info = await page.evaluate(tt => {
      const id = window.renderFrame(tt);
      return { id, t: tt };
    }, t);
    await page.screenshot({ path: path.join(ROOT, 'tmp/shot_' + t + '.png') });
    console.log('shot', JSON.stringify(info));
  }
  await browser.close();
})();
