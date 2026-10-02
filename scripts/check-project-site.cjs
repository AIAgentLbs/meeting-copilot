// Site acceptance only; never executes the installation command.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/Users/m/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const review = path.join(root, '.impeccable/review');
  fs.mkdirSync(review, { recursive: true });
  const server = http.createServer((req, res) => {
    const routes = {
      '/meeting-copilot/': ['docs/index.html', 'text/html'],
      '/meeting-copilot/ru/': ['docs/ru/index.html', 'text/html'],
      '/meeting-copilot/styles.css': ['docs/styles.css', 'text/css'],
      '/meeting-copilot/site.js': ['docs/site.js', 'text/javascript'],
      '/meeting-copilot/install.sh': ['install.sh', 'text/plain'],
    };
    const target = routes[new URL(req.url, 'http://localhost').pathname];
    if (!target) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': target[1] + '; charset=utf-8' });
    res.end(fs.readFileSync(path.join(root, target[0])));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true });
  try {
    const local = `http://127.0.0.1:${server.address().port}/meeting-copilot/`;
    const base = process.env.SITE_URL || local;
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: async text => { if (window.rejectClipboard) throw new Error('Denied'); window.copiedCommand = text; } },
    }));
    for (const language of ['en', 'ru']) {
      const url = new URL(language === 'ru' ? 'ru/' : './', base).href;
      await page.setViewportSize({ width: 1440, height: 1000 });
      await page.goto(url, { waitUntil: 'networkidle' });
      await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.locator('html').getAttribute('lang'), language);
      assert.equal(await page.locator('h1').count(), 1);
      const command = await page.locator('#install-command').textContent();
      assert.equal(command.trim(), 'curl -fsSL https://aiagentlbs.github.io/meeting-copilot/install.sh | bash');
      assert((await page.locator('#install').textContent()).includes('v0.1.7'));
      await page.locator('[data-copy]').click();
      assert.equal(await page.evaluate(() => window.copiedCommand), command.trim());
      await page.waitForFunction(() => !document.querySelector('[data-copy]').disabled);
      await page.evaluate(() => { window.rejectClipboard = true; });
      await page.locator('[data-copy]').click();
      assert.equal(await page.evaluate(() => window.getSelection().toString()), command.trim());
      await page.waitForFunction(() => !document.querySelector('[data-copy]').disabled);
      await page.locator('.install-help summary').click();
      assert.equal(await page.locator('.install-help').getAttribute('open'), '');
      await page.locator('.install-help summary').click();
      for (const [device, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
        await page.setViewportSize({ width, height });
        await page.evaluate(() => { window.getSelection().removeAllRanges(); scrollTo(0, 0); });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${language}/${device} overflow`);
        assert(await page.locator('.language-link').isVisible());
        if (!process.env.NO_SCREENSHOTS) {
          await page.screenshot({ path: path.join(review, `${language}-${device}.png`), fullPage: true });
          if (language === 'ru') await page.locator('#install').screenshot({ path: path.join(review, `ru-install-${device}.png`) });
        }
      }
      const broken = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')].filter(a => !document.querySelector(a.getAttribute('href'))).map(a => a.getAttribute('href')));
      assert.deepEqual(broken, []);
    }
    const response = await page.request.get(new URL('install.sh', base).href);
    assert.equal(response.status(), 200);
    assert.equal(await response.text(), fs.readFileSync(path.join(root, 'install.sh'), 'utf8'));
    assert.deepEqual(errors, []);
    console.log('Site OK: EN/RU, desktop/mobile, copy success/denial, update details, language switch, installer bytes, no overflow or JS errors.');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
