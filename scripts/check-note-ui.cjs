// Run against a synthetic meeting: never writes to the user's live meeting.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/Users/m/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const root = path.resolve(__dirname, '../copilot/web');
  const server = http.createServer((request, response) => {
    const files = { '/': ['index.html', 'text/html'], '/app.js': ['app.js', 'text/javascript'], '/styles.css': ['styles.css', 'text/css'] };
    const file = files[request.url];
    if (!file) { response.writeHead(404); return response.end(); }
    response.writeHead(200, { 'Content-Type': file[1] });
    response.end(fs.readFileSync(path.join(root, file[0])));
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
    const analysisHelp = page.locator('#analysis-help');
    assert.equal(await analysisHelp.isVisible(), true, 'analysis controls need a permanent explanation');
    assert.match(await analysisHelp.textContent(), /вопросы, риски и решения/);
    assert.equal(await page.locator('#auto-analysis').getAttribute('aria-describedby'), 'analysis-help');
    assert.equal(await page.locator('#analyze-button').getAttribute('aria-describedby'), 'analysis-help');
    const company = page.getByRole('link', { name: 'by aiagentlbs.com', exact: true });
    assert.equal(await company.count(), 1, 'company URL must be a keyboard-accessible link');
    assert.equal(await company.getAttribute('href'), 'https://aiagentlbs.com/');
    assert.equal(await company.getAttribute('target'), '_blank');
    assert.match(await company.getAttribute('rel'), /noopener/);
    const hint = page.locator('#note-help');
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
    assert.match(await analysisHelp.textContent(), /questions, risks and decisions/);
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
