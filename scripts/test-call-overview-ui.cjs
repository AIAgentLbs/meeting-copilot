// Real UI files, synthetic API only: the owner's Chat holds only his questions, notes and answers;
// auto-analysis lands on Call overview; one chat tab; status filters persist in shared preferences.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const errors = [];
(async () => {
  const browser = await chromium.launch({ headless: true });
  const root = path.resolve(__dirname, '../copilot/web');
  const saved = [];
  let preferences = { interface_language: 'ru' };
  const journal = [
    { id: 'n1', category: 'NOTE', source: 'user_note', text: 'Моя заметка про бюджет', meeting_id: 't', created_at: '2026-10-22T10:01:30+00:00' },
    { id: 'a1', category: 'ASK', source: 'copilot', text: 'Кто отвечает за пилот?', meeting_id: 't', status: 'open' },
    { id: 'a2', category: 'ASK', source: 'copilot', text: 'Какой бюджет?', meeting_id: 't', status: 'resolved' },
    { id: 'q1', category: 'OPEN_QUESTION', source: 'meeting_chat', text: 'Когда релиз?', meeting_id: 't', status: 'clarify' },
    { id: 'r1', category: 'RISK', source: 'copilot', text: 'Нет бюджета', meeting_id: 't', status: 'open' },
  ];
  const state = () => ({ preferences, journal, frames: [], project: {},
    transcript: { meeting_id: 't', meeting: 'Test call', status: 'recording', live: true, started_at: '2026-10-22T10:00:00Z', segments: [], speakers: [] },
    recording_health: { capture: { audio_recording: true } },
    meeting_chat: [{ id: 'c1', sender: 'Anna', text: 'Когда релиз?' }],
    copilot: { busy: true, analysis: { state: 'idle' }, messages: [  // busy = an auto-analysis is running
      { role: 'user', kind: 'answer', text: 'Что они сказали?', at: '2026-10-22T10:01:00+00:00' },
      { role: 'assistant', kind: 'answer', text: 'Про пилот в понедельник.', at: '2026-10-22T10:02:00+00:00' },
      // An older server could still send a stored analysis message: the Chat ignores it.
      { role: 'assistant', kind: 'insight', text: 'RISK — Нет бюджета\nSIGNAL_UPDATE: {"id":"r1"}', at: '2026-10-22T10:03:00+00:00' },
    ] },
    fact_checks: { web: true, items: [{ id: 'f1', status: 'confirmed', claim: 'Пилот в понедельник', segment: { source: 'system', speaker: 'Anna' } }] },
  });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await context.route('http://overview-ui.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/api/preferences') {
        const change = route.request().postDataJSON();
        saved.push(change);
        preferences = { ...preferences, ...change };
        return route.fulfill({ json: { ok: true, preferences: change } });
      }
      if (url.pathname === '/api/state') return route.fulfill({ json: state() });
      if (url.pathname.startsWith('/api/')) return route.fulfill({ json: { ok: true } });
      const file = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
      if (file.includes('/') || !/\.(html|js|css)$/.test(file)) return route.abort();
      const type = file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html';
      return route.fulfill({ contentType: type, body: await fs.readFile(path.join(root, file)) });
    });
    const open = async () => {
      const page = await context.newPage();
      // Other panels get a bare {ok: true} stub here; only errors raised by app.js are this test's business.
      page.on('pageerror', error => /app\.js/.test(error.stack || '') && errors.push(String(error.stack)));
      await page.goto('http://overview-ui.test/');
      await page.locator('#call-board .board-item').first().waitFor();
      return page;
    };
    let page = await open();

    // One chat tab only: the meeting chat tab, its counter and empty text are gone.
    const tabs = await page.locator('[data-content-view]').evaluateAll(nodes => nodes.filter(node => !node.hidden).map(node => node.textContent.trim()));
    assert.deepEqual(tabs.map(text => text.replace(/\d+$/, '')), ['Обзор звонка', 'Чат', 'Мои заметки', 'Ссылки и сервисы']);
    assert.equal(await page.locator('#meeting-chat, #meeting-chat-count, [data-content-view="meeting-chat"]').count(), 0);

    // Call overview still gets the analysis signals, including the question typed in the call's chat.
    const board = page.locator('#call-board');
    assert.match(await board.textContent(), /Кто отвечает за пилот\?/);
    assert.match(await board.textContent(), /Нет бюджета/);
    assert.match(await board.textContent(), /Когда релиз\?/);

    // Chat: the owner's question, his note and the answer, in time order; nothing else.
    await page.locator('[data-content-view="chat"]').click();
    const chat = page.locator('#chat');
    await chat.locator('.message').first().waitFor();
    const messages = await chat.locator('.message').evaluateAll(nodes => nodes.map(node => [
      node.querySelector('.message-label').textContent, node.querySelector('.message-text').textContent]));
    assert.deepEqual(messages, [['Вы', 'Что они сказали?'], ['Ваша заметка', 'Моя заметка про бюджет'],
      ['Copilot', 'Про пилот в понедельник.']], 'no auto-analysis and no thinking bubble for it');
    assert.doesNotMatch(await chat.textContent(), /SIGNAL_UPDATE|Автоанализ|RISK|\{"/);
    assert.doesNotMatch(await page.locator('body').textContent(), /SIGNAL_UPDATE/, 'protocol text is shown nowhere');

    // Status filters: all on by default, real toggle buttons with labels, keyboard operable.
    await page.locator('[data-content-view="board"]').click();
    const toggle = status => page.locator(`#call-board [data-status-filter="${status}"]`);
    for (const status of ['open', 'clarify', 'resolved']) assert.equal(await toggle(status).getAttribute('aria-pressed'), 'true');
    assert.equal(await toggle('open').textContent(), 'Открыто 2');
    const counts = async () => page.locator('#call-board .board-column-header p').allTextContents();
    const before = await counts();
    await toggle('resolved').focus();
    await page.keyboard.press('Enter');  // hide green
    assert.equal(await toggle('resolved').getAttribute('aria-pressed'), 'false');
    assert.equal(await page.evaluate(() => document.activeElement.dataset.statusFilter), 'resolved', 'focus stays on the toggle');
    assert.equal(await page.locator('#call-board .board-item.resolved').count(), 0);
    assert.equal(await page.locator('#call-board .board-item.open').count(), 2);
    assert.deepEqual(await counts(), before, 'column counts keep counting all items');
    assert.deepEqual(saved.at(-1), { call_overview_statuses: ['open', 'clarify'] });
    await toggle('open').click();  // only yellow
    assert.equal(await page.locator('#call-board .board-item').count(), 1);
    assert.equal(await page.locator('#call-board .board-item.clarify').count(), 1);
    assert.equal(await page.locator('#call-board .facts .fact-row').count(), 1, 'fact check is not filtered');

    // The choice survives a reload, from config.json and not from this browser.
    await page.evaluate(() => localStorage.clear());
    await page.close();
    page = await open();
    assert.equal(await page.locator('#call-board [data-status-filter="clarify"]').getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('#call-board [data-status-filter="open"]').getAttribute('aria-pressed'), 'false');
    assert.equal(await page.locator('#call-board .board-item').count(), 1);

    // All off: a short line in each column, not blank columns.
    await page.locator('#call-board [data-status-filter="clarify"]').click();
    assert.deepEqual(saved.at(-1), { call_overview_statuses: [] });
    const empty = await page.locator('#call-board .board-column:not(.facts) .board-empty').allTextContents();
    assert.deepEqual(empty, Array(3).fill('Все статусы скрыты. Включите хотя бы один статус выше.'));
    assert.doesNotMatch(empty.join(''), /[—ё]/, 'RU copy: no em dashes, no ё');
    assert.equal(await page.locator('#call-board .facts .fact-row').count(), 1);

    // English copy.
    preferences = { ...preferences, interface_language: 'en' };
    await page.reload();
    await page.waitForFunction(() => document.documentElement.lang === 'en');
    await page.locator('#call-board [data-status-filter="open"]').waitFor();
    assert.equal(await page.locator('#call-board .board-filters').getAttribute('aria-label'), 'Show items with status');
    assert.match(await page.locator('#call-board .board-empty').first().textContent(), /All statuses are hidden/);
    assert.deepEqual(errors, []);
    console.log('Call overview UI: owner-only chat, one chat tab, persistent status filters, RU/EN: OK');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error, errors); process.exitCode = 1; });
