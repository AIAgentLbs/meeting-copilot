// Real UI, synthetic API only: interface language in Settings and the hideable transcript,
// both saved in the shared preferences (config.json) and restored after a reload.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({headless: true});
  const root = path.resolve(__dirname, '../copilot/web');
  const errors = [], saved = [];
  let preferences = {interface_language: 'ru'}, slowNextSave = false;
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 900}});
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(String(error)));
    await context.route('http://preferences-ui.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/api/preferences') {
        const change = route.request().postDataJSON();
        if (slowNextSave) { slowNextSave = false; await new Promise(resolve => setTimeout(resolve, 1500)); }
        saved.push(change);
        preferences = {...preferences, ...change};
        return route.fulfill({json: {ok: true, preferences: change}});
      }
      if (url.pathname === '/api/state') return route.fulfill({json: {preferences,
        transcript: {meeting_id: 'test', meeting: 'Test call', status: 'recording', live: true, segments: [], speakers: []},
        copilot: {messages: [], busy: false, analysis: {state: 'idle'}}, journal: [], frames: [], meeting_chat: [], project: {}}});
      if (url.pathname.startsWith('/api/')) return route.fulfill({json: {ok: true}});
      const file = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
      if (!['index.html', 'app.js', 'styles.css'].includes(file)) return route.abort();
      const type = file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html';
      return route.fulfill({contentType: type, body: await fs.readFile(path.join(root, file))});
    });
    const transcript = page.locator('.transcript-pane'), copilot = page.locator('.copilot-pane');
    const hide = page.locator('#transcript-hide'), show = page.locator('#transcript-show');
    await page.goto('http://preferences-ui.test/');
    await page.waitForFunction(() => document.documentElement.lang === 'ru');

    // Main screen: no language switch, no helper lines the owner removed.
    assert.equal(await page.locator('header select, header [data-language], header .language-switch').count(), 0,
      'the interface language lives in Settings only, not in the header');
    assert.equal(await page.locator('#new-meeting-help, #copilot-meta, #analysis-status').count(), 0,
      'main screen carries no new-meeting help, AI-context subtitle or analysis status line');

    // Language: one labelled control in Settings, saved to the shared preferences.
    await page.locator('#settings-open').click();
    const language = page.getByRole('combobox', {name: 'Язык интерфейса', exact: true});
    assert.equal(await language.count(), 1, 'Settings has one labelled interface language control');
    assert.equal(await language.inputValue(), 'ru');
    await language.selectOption('en');
    await page.waitForFunction(() => document.documentElement.lang === 'en');
    assert.deepEqual(saved, [{interface_language: 'en'}]);
    await page.locator('#settings-close').click();

    // Transcript: one click hides it, the other panel takes the width, a slim control brings it back.
    assert.equal(await hide.textContent(), 'Hide');
    assert.equal(await show.isVisible(), false);
    const fullWidth = (await page.locator('.workspace').boundingBox()).width;
    await hide.click();
    await transcript.waitFor({state: 'hidden'});
    assert.equal(await show.textContent(), 'Show transcript');
    assert.equal(await show.isVisible(), true);
    assert(Math.abs((await copilot.boundingBox()).width - fullWidth) < 2, 'freed width goes to the other panel');
    assert.deepEqual(saved.at(-1), {transcript_hidden: true});

    // Both choices come back from config.json, even in a browser with no local copy.
    const fresh = await context.newPage();
    fresh.on('pageerror', error => errors.push(String(error)));
    await page.close();
    await fresh.goto('http://preferences-ui.test/');
    await fresh.evaluate(() => localStorage.clear());
    await fresh.reload();
    await fresh.waitForFunction(() => document.documentElement.lang === 'en');
    await fresh.locator('.transcript-pane').waitFor({state: 'hidden'});
    assert.equal(await fresh.locator('#interface-language').inputValue(), 'en');

    // Another browser changing config.json wins over this browser's earlier choice.
    preferences = {...preferences, interface_language: 'ru'};
    await fresh.reload();
    await fresh.waitForFunction(() => document.documentElement.lang === 'ru');
    assert.equal(await fresh.locator('#transcript-show').textContent(), 'Показать расшифровку');

    // Narrow screen: the show control stays reachable and nothing scrolls sideways.
    await fresh.setViewportSize({width: 390, height: 844});
    assert.equal(await fresh.locator('#transcript-show').isVisible(), true);
    assert.equal(await fresh.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await fresh.locator('#transcript-show').click();
    await fresh.locator('.transcript-pane').waitFor({state: 'visible'});
    assert.equal(await fresh.locator('#transcript-show').isVisible(), false);
    assert.deepEqual(saved.at(-1), {transcript_hidden: false});
    await fresh.reload();
    await fresh.waitForFunction(() => document.documentElement.lang === 'ru');
    await fresh.locator('.transcript-pane').waitFor({state: 'visible'});
    assert.equal(await fresh.locator('#transcript-hide').getAttribute('aria-label'), 'Скрыть расшифровку');

    // Hide then show quickly while the first save is slow: the last click is what stays saved.
    const before = saved.length;
    slowNextSave = true;
    await fresh.locator('#transcript-hide').click();
    await fresh.locator('#transcript-show').click();
    for (let wait = 0; saved.length < before + 2 && wait < 100; wait++) await new Promise(resolve => setTimeout(resolve, 100));
    assert.deepEqual(saved.slice(before), [{transcript_hidden: true}, {transcript_hidden: false}], 'saves keep click order');
    assert.equal(preferences.transcript_hidden, false);
    await fresh.waitForTimeout(2500);  // a poll after the saves must not fold the panel again
    assert.equal(await fresh.locator('.transcript-pane').isVisible(), true);
    assert.deepEqual(errors, []);
    console.log('PASS: no header language switch, no removed helper lines, language in Settings saved and restored, transcript hide/persist/show, narrow width');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
