// Render a contact sheet of representative frames from every scene type.
// Runs headless Chrome via Playwright, so the design is inspected as pixels.
//
// Usage: node content/video2/renderer/preview.js [out.png]
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../../..');
const html = fs.readFileSync(path.join(__dirname, 'frames.html'), 'utf8');

const PLAN = JSON.parse(fs.readFileSync(path.join(ROOT, 'content/video2/plan.preview.json'), 'utf8'));

// Pick one moment per scene: far enough in that the animations have settled.
const picks = PLAN.scenes.map((s, i) => ({ id: s.id, t: s.start + Math.min(s.end - s.start, (s.end - s.start) * 0.55) }));

async function main() {
  const { chromium } = require('playwright-core');
  const exe = process.env.CHROME_PATH || require('os').homedir() + '/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome';
  const out = process.argv[2] || path.join(ROOT, 'tmp/preview.png');
  const browser = await chromium.launch({ executablePath: exe, args: ['--allow-file-access-from-files', '--font-render-hinting=none'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  page.on('console', m => console.log('[page]', m.type(), m.text()));
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.setContent(html, { waitUntil: 'load' });
  await page.addStyleTag({ content: 'canvas{width:2560px;height:1440px}' });
  await page.evaluate(({ plan }) => { window.setPlan(plan); }, { plan: PLAN });

  // Contact sheet: 3 columns x 3 rows of quarter-size frames.
  const cols = 3, rows = Math.ceil(picks.length / cols), cw = 800, ch = 450;
  await page.setViewportSize({ width: cols * cw, height: rows * ch });
  const dataUrls = [];
  for (const p of picks) {
    const url = await page.evaluate((t) => {
      window.renderFrame(t);
      const src = document.getElementById('c');
      const small = document.createElement('canvas');
      small.width = 800; small.height = 450;
      small.getContext('2d').drawImage(src, 0, 0, 800, 450);
      return small.toDataURL('image/png');
    }, p.t);
    dataUrls.push(url);
    console.log('rendered scene', p.id, 'at', p.t.toFixed(1), 's');
  }
  await page.evaluate(({ urls, cols, cw, ch }) => {
    document.body.innerHTML = '<div id="sheet" style="display:grid;grid-template-columns:repeat(' + cols + ',1fr);gap:4px;background:#000"></div>';
    const sheet = document.getElementById('sheet');
    urls.forEach(u => { const i = new Image(); i.src = u; i.style.width = '100%'; sheet.appendChild(i); });
  }, { urls: dataUrls, cols, cw, ch });
  await page.waitForTimeout(400);
  await page.screenshot({ path: out, fullPage: true });
  console.log('wrote', out);
  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
