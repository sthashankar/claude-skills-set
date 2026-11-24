// Screenshot an HTML or SVG file with Playwright.
// usage: node render.js IN.(html|svg) OUT.png [--w 1400] [--h 900] [--eval "js"] [--wait ms] [--full] [--sel "#id"]
// three.js CDN requests are served from a local npm pack when the CDN is blocked (set THREE_DIR or it runs `npm pack three@0.160.0`).
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path'), cp = require('child_process');
const a = process.argv.slice(2); const inp = path.resolve(a[0]), out = path.resolve(a[1]);
const opt = k => { const i = a.indexOf('--' + k); return i > 0 ? a[i + 1] : null; };
const W = +(opt('w') || 1400), H = +(opt('h') || 900), wait = +(opt('wait') || 1500);
function threeDir() {
  if (process.env.THREE_DIR && fs.existsSync(process.env.THREE_DIR)) return process.env.THREE_DIR;
  const d = path.join(require('os').tmpdir(), 'hd_three'); const p = path.join(d, 'package');
  if (!fs.existsSync(p)) { fs.mkdirSync(d, { recursive: true }); cp.execSync('npm pack three@0.160.0 --silent', { cwd: d });
    cp.execSync('tar xzf three-0.160.0.tgz', { cwd: d }); }
  return p;
}
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: +(opt('dpr') || 1) });
  pg.on('pageerror', e => console.error('PAGEERROR', e.message));
  await pg.route(/cdn\.jsdelivr\.net\/npm\/three@[^/]+\/(.*)$/, async r => {
    const m = r.request().url().match(/three@[^/]+\/(.*)$/); const f = path.join(threeDir(), m[1]);
    if (fs.existsSync(f)) r.fulfill({ path: f, contentType: 'application/javascript' }); else r.continue(); });
  await pg.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await pg.goto('file://' + inp); await pg.waitForTimeout(wait);
  if (opt('eval')) { const res = await pg.evaluate(opt('eval')); if (res !== undefined) console.log(JSON.stringify(res)); await pg.waitForTimeout(+(opt('wait2') || 1200)); }
  const sel = opt('sel');
  if (sel) await (await pg.$(sel)).screenshot({ path: out }); else await pg.screenshot({ path: out, fullPage: a.includes('--full') });
  await b.close(); console.log('wrote', out);
})();
