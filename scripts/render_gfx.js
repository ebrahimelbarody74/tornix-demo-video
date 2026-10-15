// Renders the branded graphics for one video: frame overlays per section, rounded mask, thumbnail,
// intro frames (thumbnail with gentle motion) and outro frames.
// usage: node render_gfx.js <config.json> <workdir>
const fs = require('fs');
const path = require('path');

function loadPlaywright() {
  const candidates = [
    process.env.PLAYWRIGHT_MODULE,
    path.join(require('os').homedir(), 'atlas-e2e/pw/node_modules/@playwright/test'),
    
    'playwright', '@playwright/test', 'playwright-core',
  ].filter(Boolean);
  for (const c of candidates) { try { return require(c); } catch {} }
  throw new Error('Playwright not found — set PLAYWRIGHT_MODULE to a playwright / @playwright/test / playwright-core folder');
}

(async () => {
  const [cfgPath, work] = process.argv.slice(2);
  if (!cfgPath || !work) throw new Error('usage: node render_gfx.js <config.json> <workdir>');
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const skill = path.resolve(__dirname, '..');
  const gfx = path.join(work, 'gfx'); const out = path.join(work, 'gfx-out');
  fs.mkdirSync(path.join(gfx, 'assets'), { recursive: true });
  for (const d of ['intro', 'outro']) { fs.rmSync(path.join(out, d), { recursive: true, force: true }); fs.mkdirSync(path.join(out, d), { recursive: true }); }
  for (const f of fs.readdirSync(path.join(skill, 'assets'))) {
    if (f === 'gfx.html') continue;
    fs.copyFileSync(path.join(skill, 'assets', f), path.join(gfx, 'assets', f));
  }
  fs.copyFileSync(path.join(skill, 'assets', 'gfx.html'), path.join(gfx, 'gfx.html'));
  const thumb = { ...(cfg.thumbnail || {}) };
  if (thumb.card_image) {
    fs.copyFileSync(path.resolve(path.dirname(cfgPath), thumb.card_image), path.join(gfx, 'assets', 'card' + path.extname(thumb.card_image)));
    thumb.card_image = 'assets/card' + path.extname(thumb.card_image);
  }

  const { chromium } = loadPlaywright();
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 2560, height: 1440 }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.join(gfx, 'gfx.html'));
  await p.evaluate((c) => applyConfig(c), { ...cfg, thumbnail: thumb });
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(500);
  for (let s = 0; s < cfg.sections.length; s++) {
    await p.evaluate((s) => show('frame', s), s);
    await p.screenshot({ path: `${out}/bg${s}.png` });
  }
  await p.evaluate(() => show('maskscene'));
  await p.screenshot({ path: `${out}/mask.png`, clip: { x: 0, y: 0, width: 2400, height: 1125 } });
  await p.evaluate(() => thumbAt(0)); await p.screenshot({ path: `${out}/thumb.png` });
  const fps = 30;
  const introSec = cfg.intro_seconds ?? 2.4, outroSec = cfg.outro_seconds ?? 3.0;
  for (let i = 0; i < introSec * fps; i++) { await p.evaluate((t) => thumbAt(t), i / fps); await p.screenshot({ path: `${out}/intro/${String(i).padStart(4, '0')}.png` }); }
  for (let i = 0; i < outroSec * fps; i++) { await p.evaluate((t) => outroAt(t), i / fps); await p.screenshot({ path: `${out}/outro/${String(i).padStart(4, '0')}.png` }); }
  await b.close();
  console.log('graphics ->', out);
})().catch((e) => { console.error(e); process.exit(1); });
