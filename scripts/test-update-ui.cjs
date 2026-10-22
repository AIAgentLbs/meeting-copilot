// Real UI, synthetic releases only; never connects to a user's meeting service.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({headless: true});
  const root = path.resolve(__dirname, '../copilot/web');
  const errors = [];
  let updates = {version: '0.1.9', platform: 'macos', channel: 'technical-beta', enabled: true,
    checked_at: 1000, checking: false, notify: true, latest: {version: '0.1.10',
      url: 'https://github.com/AIAgentLbs/meetontrack/releases/tag/v0.1.10',
      notes: 'Better recording.\n<script>window.UNSAFE = true</script>'}};
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    page.on('pageerror', error => errors.push(String(error)));
    await page.route('http://update-ui.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname.startsWith('/api/')) {
        if (url.pathname === '/api/updates/settings') {
          const data = route.request().postDataJSON();
          if ('enabled' in data) updates.enabled = data.enabled;
          if (data.dismiss || !updates.enabled) updates.notify = false;
          return route.fulfill({json: {ok: true, updates}});
        }
        if (url.pathname === '/api/updates/check') return route.fulfill({json: {ok: true, updates}});
        return route.fulfill({json: url.pathname === '/api/state' ? {
          updates, transcript: {meeting_id: 'test', meeting: 'Test call', status: 'finished', live: false,
            segments: [], speakers: []}, copilot: {messages: [], busy: false, analysis: {state: 'idle'}},
          journal: [], frames: [], meeting_chat: [], project: {}} : {ok: true}});
      }
      const file = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
      if (!['index.html', 'app.js', 'updates.js', 'styles.css'].includes(file)) return route.abort();
      const type = file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html';
      return route.fulfill({contentType: type, body: await fs.readFile(path.join(root, file))});
    });
    await page.goto('http://update-ui.test/');
    await page.locator('#updates-notice').waitFor({state: 'visible'});
    assert.equal(await page.title(), 'MeetOnTrack by aiagentlbs.com');
    assert.equal(await page.locator('.brand').textContent(), 'MeetOnTrack');
    assert.equal(await page.locator('.brand-company').getAttribute('href'), 'https://aiagentlbs.com/');
    assert.equal(await page.evaluate(() => {
      const brand = document.querySelector('.brand-lockup').getBoundingClientRect();
      const controls = document.querySelector('.status-strip').getBoundingClientRect();
      return brand.right > controls.left && brand.left < controls.right && brand.bottom > controls.top && brand.top < controls.bottom;
    }), false, 'brand and header controls must not overlap');
    await page.locator('#updates-notice').click();
    await page.locator('#updates-notes').waitFor({state: 'visible'});
    assert((await page.locator('#updates-notes').textContent()).includes('<script>'));
    assert.equal(await page.evaluate(() => window.UNSAFE), undefined);
    await page.locator('#interface-language').selectOption('en');
    await page.locator('#updates-check').getByText('Check for updates', {exact: true}).waitFor();
    assert((await page.locator('#updates-safe-install').textContent()).includes('Finish your call'));
    await page.screenshot({path: '/tmp/meetontrack-updates-desktop.png', fullPage: true});
    await page.locator('#updates-check').click();
    await page.locator('#updates-dismiss').click();
    await page.locator('#updates-notice').waitFor({state: 'hidden'});
    assert.equal(await page.locator('#updates-release').isVisible(), true);
    await page.locator('#updates-enabled').uncheck();
    await page.waitForFunction(() => !document.getElementById('updates-enabled').checked);
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: '/tmp/meetontrack-updates-mobile.png', fullPage: true});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    console.log('PASS: brand, platform notice, settings, notes XSS safety, language switch, dismiss, opt-out, responsive layout');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
