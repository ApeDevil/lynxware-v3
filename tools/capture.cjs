// Usage: node capture.js <outdir> <url...>
const { chromium, devices } = require('playwright');
const fs = require('fs'); const path = require('path');
const out = process.argv[2]; const urls = process.argv.slice(3);
const modes = {
  desktop: { viewport: { width: 1440, height: 900 }, userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', deviceScaleFactor: 1 },
  mobile: { ...devices['iPhone 13'], deviceScaleFactor: 1 },
};
(async () => {
  const browser = await chromium.launch();
  for (const [mode, opts] of Object.entries(modes).filter(([m]) => !process.env.MODE || m === process.env.MODE)) {
    const ctx = await browser.newContext(opts);
    for (const url of urls) {
      const slug = (new URL(url).pathname.replace(/^\/|\/$/g, '') || 'index');
      const dir = path.join(out, mode); fs.mkdirSync(dir, { recursive: true });
      const page = await ctx.newPage(); const reqs = new Set(); const errs = [];
      page.on('request', r => reqs.add(r.resourceType() + ' ' + r.url()));
      page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
      await page.goto(url, { waitUntil: 'load', timeout: 90000 });
      // scroll to trigger lazy loading / animations
      await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 150)); } window.scrollTo(0, 0); });
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {}); await page.waitForTimeout(1500);
      fs.writeFileSync(path.join(dir, slug + '.html'), await page.content());
      fs.writeFileSync(path.join(dir, slug + '.reqs.txt'), [...reqs].join('\n'));
      fs.writeFileSync(path.join(dir, slug + '.errors.txt'), errs.join('\n'));
      await page.screenshot({ path: path.join(dir, slug + '.png'), fullPage: true });
      console.log(mode, slug, reqs.size, 'reqs');
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();
})();
