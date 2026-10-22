// Fact-check strip against the shipped UI files with a synthetic state; never a live call.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const root = path.resolve(__dirname, '../copilot/web');
  const server = http.createServer((request, response) => {
    const name = request.url === '/' ? 'index.html' : path.basename(request.url);
    const type = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' }[path.extname(name)];
    if (!type || !fs.existsSync(path.join(root, name))) { response.writeHead(404); return response.end(); }
    response.writeHead(200, { 'Content-Type': type });
    response.end(fs.readFileSync(path.join(root, name)));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true });
  const row = (id, status, extra = {}) => ({ id, status, claim: `Claim ${id}`, segment: { source: 'system', speaker: 'Anna' }, ...extra });
  const facts = {
    web: false, provider: 'Ollama', web_providers: ['Codex', 'Claude Code'],
    items: [
      row('red', 'refuted', { claim: 'У Higgsfield есть свои модели генерации', segment: { source: 'microphone' },
        fact: 'Higgsfield uses partner models.', sources: [{ kind: 'web', url: 'https://news.example/a', quote: 'q' }] }),
      row('green', 'confirmed', { sources: [{ kind: 'web', url: 'https://source.example/b', quote: 'q' }] }),
      row('yellow', 'unclear', { note: 'no_source', sources: [{ kind: 'web', url: 'https://never.example/c' }] }),
      row('failed', 'unclear', { error: 'AI_NETWORK: Traceback (most recent call last) socket.gaierror' }),
      row('pending', 'checking'),
    ],
  };
  const payload = {
    preferences: { interface_language: 'ru' },
    transcript: { meeting_id: 'fact-test', meeting: 'Synthetic meeting', status: 'recording', live: true,
      started_at: '2026-10-22T10:00:00Z', segments: [], speakers: [] },
    copilot: { messages: [], busy: false, analysis: { state: 'idle' } }, journal: [], frames: [], meeting_chat: [], project: {},
    fact_checks: facts, recording_health: { capture: { audio_recording: true } },
  };
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const errors = [];
    // Other panels get a bare {ok: true} stub here; only errors raised by app.js are this test's business.
    page.on('pageerror', error => /app\.js/.test(error.stack || '') && errors.push(String(error.stack)));
    await page.route('**/api/**', route => route.fulfill({ json: new URL(route.request().url()).pathname === '/api/state' ? payload : { ok: true } }));
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    const strip = page.locator('#fact-strip');
    await strip.locator('.fact-row').first().waitFor();
    assert.equal(await strip.isVisible(), true, 'the strip is on the main screen, not behind a tab');
    assert.equal(await strip.locator('h3').textContent(), 'Проверка фактов');
    assert.equal(await strip.locator('.fact-row').count(), 3, 'newest three by default');

    const red = strip.locator('.fact-row.refuted');
    assert.equal(await red.locator('.fact-icon').getAttribute('aria-label'), 'Опровергнуто');
    assert.equal(await red.locator('.fact-speaker').textContent(), 'Вы', 'microphone speaker is the person');
    assert.match(await red.textContent(), /У Higgsfield есть свои модели генерации/);
    assert.equal(await red.locator('.fact-actual').textContent(), 'На самом деле: Higgsfield uses partner models.');
    assert.equal(await red.locator('a').getAttribute('href'), 'https://news.example/a');

    const green = strip.locator('.fact-row.confirmed');
    assert.equal(await green.locator('.fact-icon').getAttribute('aria-label'), 'Подтверждено');
    assert.equal(await green.locator('.fact-speaker').textContent(), 'Anna');
    assert.equal(await green.locator('a').getAttribute('href'), 'https://source.example/b');
    assert.equal(await green.locator('.fact-actual').count(), 0);

    const yellow = strip.locator('.fact-row.unclear').first();
    assert.equal(await yellow.locator('.fact-icon').getAttribute('aria-label'), 'Нет ни подтверждения, ни опровержения');
    assert.equal(await yellow.locator('a').count(), 0, 'a yellow row never shows a source');
    assert.match(await yellow.textContent(), /Источник не открылся/);

    const notice = strip.locator('.fact-notice');
    assert.equal(await notice.textContent(),
      'Проверка в интернете недоступна с Ollama. Чтобы ее включить, выберите Codex или Claude Code в разделе «Начать работу». Проверка по базе знаний работает.');

    await strip.getByRole('button', { name: 'Показать все (5)' }).click();
    assert.equal(await strip.locator('.fact-row').count(), 5);
    const failed = strip.locator('.fact-row.unclear').nth(1);
    assert.doesNotMatch(await failed.textContent(), /Traceback|gaierror/, 'errors go through plainError');
    assert.match(await failed.textContent(), /ИИ не ответил/);
    assert.equal(await strip.locator('.fact-row.checking .fact-icon').getAttribute('aria-label'), 'Проверяется');

    const text = await strip.textContent();
    assert.doesNotMatch(text, /[—ё]/, 'RU copy: no em dashes, no ё');

    await page.locator('[data-language="en"]').click();
    await page.waitForFunction(() => document.querySelector('#fact-strip h3').textContent === 'Fact check');
    assert.equal(await strip.locator('.fact-row.refuted .fact-speaker').textContent(), 'You');
    assert.match(await strip.locator('.fact-notice').textContent(), /Web checking is unavailable with Ollama\. To turn it on, choose Codex or Claude Code/);

    facts.web_providers = [];  // no web-capable AI installed and signed in: never name one
    await page.waitForFunction(() => /choose an AI with web search in Getting started/.test(
      document.querySelector('#fact-strip .fact-notice')?.textContent || ''));
    assert.doesNotMatch(await strip.locator('.fact-notice').textContent(), /Codex|Claude/);

    facts.web = true;
    await page.waitForFunction(() => !document.querySelector('#fact-strip .fact-notice'));
    assert.deepEqual(errors, []);
    console.log('Fact-check UI: three states, checking row, show all, web notice, plain errors, RU/EN: OK');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
