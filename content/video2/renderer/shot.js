// Full-resolution screenshot of one scene at one timestamp (for inspection).
// Usage: node content/video2/renderer/shot.js <sceneType|id> <t> <out>
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const { chromium } = require('playwright-core');
const exe = process.env.CHROME_PATH || require('os').homedir() + '/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome';

(async () => {
  const id = process.argv[2] || 'question';
  const t = Number(process.argv[3] || 5);
  const out = process.argv[4] || path.join(ROOT, 'tmp/full_' + id + '.png');
  const html = fs.readFileSync(path.join(__dirname, 'frames.html'), 'utf8');
  const plan = JSON.parse(fs.readFileSync(path.join(ROOT, 'content/video2/plan.preview.json'), 'utf8'));
  const browser = await chromium.launch({ executablePath: exe });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.setContent(html, { waitUntil: 'load' });
  const scene = plan.scenes.find(s => s.type === id || String(s.id) === id);
  await page.evaluate(({ sc }) => window.setPlan({ scenes: [Object.assign({}, sc, { start: 0, end: 999 })] }), { sc: scene });
  await page.evaluate(tt => window.renderFrame(tt), t);
  await page.evaluate(() => {
    const src = document.getElementById('c');
    const small = document.createElement('canvas');
    small.width = 1280; small.height = 720;
    const cx = small.getContext('2d');
    cx.imageSmoothingQuality = 'high';
    cx.drawImage(src, 0, 0, 1280, 720);
    document.body.innerHTML = '';
    document.body.appendChild(small);
  });
  await page.screenshot({ path: out });
  console.log('wrote', out);
  await browser.close();
})();
