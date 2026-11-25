// Functional checks against a running copy of the site: node test_functional.cjs <base-url>
const { chromium, devices } = require('playwright');
const assert = require('assert');
const base = process.argv[2];
const results = [];
const check = async (name, fn) => { try { await fn(); results.push(['PASS', name]); } catch (e) { results.push(['FAIL', name, e.message.split('\n')[0]]); } };
(async () => {
  const b = await chromium.launch();
  const mob = await b.newContext({ ...devices['iPhone 13'] });
  const desk = await b.newContext({ viewport: { width: 1440, height: 900 } });

  await check('mobile UA gets mobile layout, desktop UA gets desktop', async () => {
    const p1 = await mob.newPage(); await p1.goto(base + '/diy'); assert.equal(await p1.evaluate(() => document.documentElement.dataset.lxView), 'mobile');
    const p2 = await desk.newPage(); await p2.goto(base + '/diy'); assert.equal(await p2.evaluate(() => document.documentElement.dataset.lxView), 'desktop');
  });
  await check('mobile menu opens, lists all pages, closes', async () => {
    const p = await mob.newPage(); await p.goto(base + '/');
    assert.equal(await p.isVisible('#MENU_AS_CONTAINER'), false);
    await p.click('#MENU_AS_CONTAINER_TOGGLE'); await p.waitForTimeout(600);
    assert.equal(await p.isVisible('#MENU_AS_CONTAINER'), true);
    const links = await p.$$eval('#MENU_AS_CONTAINER a', as => as.map(a => a.getAttribute('href')));
    for (const s of ['/diy', '/tutorials', '/downloads', '/contact', '/application', '/partnership']) assert(links.includes(s), 'menu lacks ' + s + ' in ' + links);
    await p.click('#MENU_AS_CONTAINER_TOGGLE'); await p.waitForTimeout(600);
    assert.equal(await p.isVisible('#MENU_AS_CONTAINER'), false);
    await p.screenshot({ path: '/home/user/work/peek/menu_new.png' });
  });
  await check('video loads nothing from YouTube until clicked, then embeds youtube-nocookie', async () => {
    const p = await desk.newPage(); const yt = [];
    p.on('request', r => /youtube|ytimg|googlevideo/.test(r.url()) && yt.push(r.url()));
    await p.route(/youtube|ytimg|googlevideo/, r => r.fulfill({ status: 204, body: '' }));
    await p.goto(base + '/tutorials'); await p.waitForTimeout(500);
    assert.equal(yt.length, 0, 'requests before consent: ' + yt);
    assert.equal(await p.locator('.lx-video').count(), 3);
    let clicked = false;
    for (const btn of await p.locator('.lx-video__play').all()) { const bb = await btn.boundingBox(); if (bb && bb.y >= 0) { await btn.click(); clicked = true; break; } }
    assert(clicked, 'no on-page video');
    const src = await p.locator('.lx-video iframe').first().getAttribute('src', { timeout: 5000 });
    assert.equal(yt.filter(u => !u.includes('youtube-nocookie.com/embed')).length, 0, 'non-embed YouTube requests: ' + yt);
    assert(src.startsWith('https://www.youtube-nocookie.com/embed/'), src);
  });
  for (const [path, mode] of [['/contact', 'desktop'], ['/application', 'desktop'], ['/partnership', 'mobile']]) {
    await check(`form ${path} (${mode}) posts all fields and shows its success message`, async () => {
      const p = await (mode === 'mobile' ? mob : desk).newPage(); let payload;
      await p.route('**/api/form', async r => { payload = JSON.parse(r.request().postData()); await r.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' }); });
      await p.goto(base + path); await p.waitForTimeout(2600);
      const form = p.locator('form').first();
      for (const el of await form.locator('input:not(.lx-hp), textarea').all()) {
        const t = await el.getAttribute('type');
        await el.fill(t === 'email' ? 'test@example.com' : t === 'url' ? 'https://example.com' : 'Test value');
      }
      const sel = form.locator('select'); if (await sel.count()) await sel.selectOption({ index: 1 });
      await form.locator('button').click(); await p.waitForTimeout(800);
      assert(payload, 'no request sent');
      assert(['Contact', 'Application', 'Partnership Request'].includes(payload.form), 'form title ' + payload.form);
      assert(payload.fields.some(f => f.type === 'email' && f.value === 'test@example.com'));
      assert.equal(payload.company_website, '');
      const success = form.locator('[data-testid="richTextElement"]').last();
      assert.equal(await success.evaluate(e => getComputedStyle(e).visibility), 'visible');
    });
  }
  await check('required fields block an empty submit', async () => {
    const p = await desk.newPage(); let sent = false; await p.route('**/api/form', r => { sent = true; r.abort(); });
    await p.goto(base + '/partnership'); await p.locator('form button').click(); await p.waitForTimeout(300); assert.equal(sent, false);
  });
  await check('all 11 downloads respond and match link count', async () => {
    const p = await desk.newPage(); await p.goto(base + '/downloads');
    const hrefs = [...new Set(await p.$$eval('a[href*="/_files/archives/"]', as => as.map(a => a.getAttribute('href'))))];
    assert.equal(hrefs.length, 11);
    for (const h of hrefs) { const r = await p.request.head(base + h); assert.equal(r.status(), 200, h); }
  });
  await check('every internal link resolves (desktop + mobile pages)', async () => {
    const p = await desk.newPage(); const seen = new Set();
    for (const s of ['/', '/diy', '/tutorials', '/downloads', '/contact', '/application', '/partnership', '/impressum']) {
      for (const ctx of [desk, mob]) { const q = await ctx.newPage(); await q.goto(base + s);
        for (const h of await q.$$eval('a[href^="/"]', as => as.map(a => a.getAttribute('href').split('#')[0]))) seen.add(h); await q.close(); }
    }
    for (const h of seen) { const r = await p.request.get(base + h, { maxRedirects: 0 }); assert(r.status() < 400, h + ' -> ' + r.status()); }
  });
  await check('unknown path returns 404 page', async () => {
    const p = await desk.newPage(); const r = await p.goto(base + '/does-not-exist'); assert.equal(r.status(), 404);
  });
  await b.close();
  for (const r of results) console.log(r.join(' | '));
  process.exit(results.some(r => r[0] === 'FAIL') ? 1 : 0);
})();
