// Run against a synthetic meeting: never writes to the user's live meeting.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/Users/m/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const root = path.resolve(__dirname, '../copilot/web');
  const server = http.createServer((request, response) => {
    // Serve every page script (updates.js, delivery.js, ...): app.js needs them.
    const name = request.url === '/' ? 'index.html' : path.basename(request.url);
    const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };
    const file = path.join(root, name);
    if (!types[path.extname(name)] || !fs.existsSync(file)) { response.writeHead(404); return response.end(); }
    response.writeHead(200, { 'Content-Type': types[path.extname(name)] });
    response.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const errors = [];
    const saved = [];
    page.on('pageerror', error => errors.push(String(error)));
    const payload = {
      preferences: { interface_language: 'ru' },
      transcript: { meeting_id: 'note-test', meeting: 'Synthetic meeting', status: 'finished', live: false,
        started_at: '2026-10-05T10:00:00Z', latest_at: '2026-10-05T10:02:44Z', segments: [], speakers: [] },
      copilot: { messages: [], busy: false, analysis: { state: 'idle' } }, journal: [], frames: [], meeting_chat: [], project: {},
      // Audio still recording keeps the main screen up; with no call the meeting library opens over it.
      recording_health: { capture: { audio_recording: true } },
    };
    await page.route('**/api/**', async route => {
      if (new URL(route.request().url()).pathname === '/api/preferences') return route.fulfill({ json: { ok: true } });
      if (new URL(route.request().url()).pathname === '/api/note') {
        saved.push(route.request().postDataJSON());
        return route.fulfill({ json: { ok: true, note: { timecode: '00:02:44' } } });
      }
      return route.fulfill({ json: payload });
    });
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    await page.waitForFunction(() => document.documentElement.lang === 'ru');
    // The Analyse now button, the auto-analysis switch and their helper line are gone;
    // the main screen keeps no explanation line for them.
    assert.equal(await page.locator('#analysis-help, #auto-analysis, #analyze-button').count(), 0);
    const company = page.getByRole('link', { name: 'by aiagentlbs.com', exact: true });
    assert.equal(await company.count(), 1, 'company URL must be a keyboard-accessible link');
    assert.equal(await company.getAttribute('href'), 'https://aiagentlbs.com/');
    assert.equal(await company.getAttribute('target'), '_blank');
    assert.match(await company.getAttribute('rel'), /noopener/);
    const hint = page.locator('#note-help');
    // The call time arrives with the first state poll, not with the page itself.
    await page.waitForFunction(() => document.querySelector('#note-help').textContent.includes('02:44'));
    assert.equal(await hint.isVisible(), true, 'note explanation must be permanently visible');
    assert.match(await hint.textContent(), /Мои заметки/);
    assert.match(await hint.textContent(), /02:44/);
    assert.match(await hint.textContent(), /начала/);
    assert.equal(await page.locator('#note-button').textContent(), 'Сохранить заметку');
    await page.locator('#question').fill('Follow up on the pilot');
    await page.locator('#note-button').click();
    await page.waitForFunction(() => document.querySelector('#question').value === '');
    assert.deepEqual(saved, [{ text: 'Follow up on the pilot' }]);
    assert.equal(await hint.isVisible(), true, 'saving feedback must not replace the explanation');
    await page.locator('#settings-open').click(); await page.locator('#interface-language').selectOption('en'); await page.locator('#settings-close').click();
    assert.equal(await page.locator('#note-button').textContent(), 'Save note');
    assert.match(await hint.textContent(), /My notes/);
    assert.match(await hint.textContent(), /02:44/);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await hint.isVisible(), true);
    await page.locator('#settings-open').click(); await page.locator('#interface-language').selectOption('ru'); await page.locator('#settings-close').click();
    await page.screenshot({ path: '/tmp/meeting-copilot-note-mobile.png', fullPage: true });
    assert.deepEqual(errors, []);
    console.log('Note UI: visible RU/EN explanation, timestamp, real save handler, mobile: OK');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
