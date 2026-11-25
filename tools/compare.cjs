// Render the migrated site like tools/capture.js rendered Wix, blocking every non-local request.
// Usage: node compare.js <base-url> <outdir> <page...>   (page = slug, "index" for /)
const { chromium, devices } = require('playwright');
const fs = require('fs'); const path = require('path');
const [base, out, ...pages] = process.argv.slice(2);
const modes = {
  desktop: { viewport: { width: 1440, height: 900 }, userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', deviceScaleFactor: 1 },
  mobile: { ...devices['iPhone 13'], deviceScaleFactor: 1 },
};
(async () => {
  const browser = await chromium.launch(); const report = {};
  const host = new URL(base).host;
  for (const [mode, opts] of Object.entries(modes)) {
    const ctx = await browser.newContext(opts);
    for (const slug of pages) {
      const page = await ctx.newPage(); const external = new Set(); const errors = []; const failed = [];
      await page.route('**/*', r => { const u = new URL(r.request().url()); if (u.host === host || u.protocol === 'data:') return r.continue(); external.add(u.origin + u.pathname.slice(0, 60)); return r.abort(); });
      page.on('console', m => m.type() === 'error' && errors.push(m.text()));
      page.on('pageerror', e => errors.push(String(e)));
      page.on('response', r => r.status() >= 400 && failed.push(r.status() + ' ' + r.url()));
      await page.goto(base + (slug === 'index' ? '/' : '/' + slug), { waitUntil: 'load' });
      await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 50)); } window.scrollTo(0, 0); });
      await page.waitForTimeout(800);
      const dir = path.join(out, mode); fs.mkdirSync(dir, { recursive: true });
      await page.screenshot({ path: path.join(dir, slug + '.png'), fullPage: true });
      const view = await page.evaluate(() => document.documentElement.dataset.lxView);
      report[mode + '/' + slug] = { view, external: [...external], errors, failed };
      await page.close();
    }
    await ctx.close();
  }
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
  await browser.close();
})();
