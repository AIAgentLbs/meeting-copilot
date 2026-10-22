// Fact-check column of Call overview against the shipped UI files with a synthetic state; never a live call.
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
    const strip = page.locator('#call-board .board-column.facts');
    await strip.locator('.fact-row').first().waitFor();
    assert.equal(await page.locator('#fact-strip').count(), 0, 'no separate strip above the tabs');
    assert.equal(await strip.isVisible(), true, 'fact check is on Call overview, the default tab');
    const columns = page.locator('#call-board .board-column');
    assert.equal(await columns.count(), 4, 'Call overview has four columns');
    assert.equal(await columns.nth(3).locator('h3').textContent(), 'Проверка фактов', 'fact check is the fourth column');
    const boxes = await columns.evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().toJSON()));
    assert(boxes.every(box => Math.abs(box.top - boxes[0].top) < 2), 'four columns side by side at 1440 px');
    assert.equal(await strip.locator('.board-column-header p').textContent(), '1 подтверждено · 2 неясно · 1 опровергнуто');
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

    payload.preferences.interface_language = 'en';  // what the real server saves; state() re-applies it
    await page.locator('#settings-open').click();  // the interface language lives in Settings
    await page.locator('#interface-language').selectOption('en');
    await page.locator('#settings-close').click();
    await page.waitForFunction(() => document.querySelector('#call-board .facts h3').textContent === 'Fact check');
    assert.equal(await strip.locator('.board-column-header p').textContent(), '1 confirmed · 2 unclear · 1 refuted');
    assert.equal(await strip.locator('.fact-row.refuted .fact-speaker').textContent(), 'You');
    assert.match(await strip.locator('.fact-notice').textContent(), /Web checking is unavailable with Ollama\. To turn it on, choose Codex or Claude Code/);

    facts.web_providers = [];  // no web-capable AI installed and signed in: never name one
    await page.waitForFunction(() => /choose an AI with web search in Getting started/.test(
      document.querySelector('#call-board .facts .fact-notice')?.textContent || ''));
    assert.doesNotMatch(await strip.locator('.fact-notice').textContent(), /Codex|Claude/);

    facts.web = true;
    await page.waitForFunction(() => !document.querySelector('#call-board .facts .fact-notice'));

    // A verdict landing while the owner reads further down keeps the list where it was.
    facts.items.push(...Array.from({ length: 15 }, (_, i) => row(`long${i}`, 'checking', { claim: `Long claim ${i} `.repeat(12) })));
    const factList = strip.locator('.board-list');
    await page.waitForFunction(() => document.querySelectorAll('#call-board .facts .fact-row').length === 20);
    await factList.evaluate(node => { node.scrollTop = 300; });
    facts.items.at(-1).status = 'confirmed';
    await page.waitForFunction(() => document.querySelectorAll('#call-board .facts .fact-row.confirmed').length === 2);
    assert.equal(await factList.evaluate(node => node.scrollTop), 300, 'fact list scroll survives an update');

    for (const width of [900, 700, 390]) {  // narrower panes wrap the columns, never scroll sideways
      await page.setViewportSize({ width, height: 900 });
      const overflow = await page.evaluate(() => [...document.querySelectorAll('html, #call-board, .board-columns')]
        .some(node => node.scrollWidth > node.clientWidth + 1));
      assert.equal(overflow, false, `no horizontal scroll at ${width} px`);
      assert.equal(await strip.isVisible(), true);
    }
    assert.deepEqual(errors, []);
    console.log('Fact-check UI: fourth Call overview column, three states, checking row, show all, web notice, plain errors, RU/EN: OK');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
