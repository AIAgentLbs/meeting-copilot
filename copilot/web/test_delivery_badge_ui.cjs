// Real browser against actual UI files, synthetic API only: the header delivery pill
// names the concrete problem and offers one action; closed failures show nothing.
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');

const channel = (state, extra = {}) => ({ configured: true, state, sent: 0, pending: 0, waiting: 0, failed: 0, action_required: 0, issues: [], ...extra });
const healthy = { state: 'sent', notifications: [], undelivered: [], issue_count: 0,
  channels: { drive: channel('sent', { sent: 1 }), gmail: channel('idle'), telegram: channel('sent', { sent: 1 }) } };
const weekly = { meeting_id: 'm1', channels: ['email'], title: 'Weekly sync', started_at: '2026-10-16T10:00:00+00:00' };
const undelivered = (...items) => ({ ...healthy, state: 'action_required', undelivered: items,
  channels: { ...healthy.channels, gmail: channel('action_required', { action_required: items.length,
    issues: items.map(item => ({ meeting_id: item.meeting_id, reason: 'retry_expired' })) }) } });
const auth = { ...healthy, state: 'action_required',
  channels: { ...healthy.channels, gmail: channel('action_required', { action_required: 1, issues: [{ meeting_id: 'm2', reason: 'auth_required' }] }) } };

(async () => {
  let delivery = healthy, retries = [], recreated = [], jobPolls = 0, language = 'ru', jobReport = { mail_status: 'sent' };
  const json = (res, value) => { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(value)); };
  const state = () => ({
    transcript: { meeting_id: 'idle', meeting: '', status: 'idle', segments: [], live: false },
    copilot: { busy: false, messages: [], analysis: { state: 'idle' } },
    recording_health: { checked_at: Date.now() / 1000, state: 'idle', capture: {} },
    frames: [], journal: [], meeting_chat: [], project: { repositories: [], kind: 'all' }, preferences: { interface_language: language }, delivery,
  });
  const server = http.createServer((req, res) => {
    if (req.url === '/api/state') return json(res, state());
    if (req.url === '/api/delivery') return json(res, { ok: true, delivery });
    if (req.url.startsWith('/api/archive?') || req.url === '/api/archive') return json(res, { ok: true, meetings: [], delivery });
    if (req.url === '/api/delivery/job') {
      jobPolls += 1;
      if (jobReport.mail_status === 'sent') delivery = healthy;
      return json(res, { ok: true, job: { state: 'complete', request_id: retries.at(-1).request_id, report: jobReport } });
    }
    if (req.url === '/api/archive/report') {
      let body = ''; req.on('data', data => body += data);
      req.on('end', () => { recreated.push(JSON.parse(body)); delivery = healthy; json(res, { ok: true, report: {} }); });
      return;
    }
    if (req.url === '/api/delivery/retry') {
      let body = ''; req.on('data', data => body += data);
      req.on('end', () => { const request = JSON.parse(body); retries.push(request);
        json(res, { ok: true, job: { state: 'sending', request_id: request.request_id, meeting_id: request.meeting_id } }); });
      return;
    }
    if (req.url.startsWith('/api/')) return json(res, { ok: true });
    const file = req.url === '/' ? 'index.html' : req.url.slice(1);
    if (!['index.html', 'styles.css', 'app.js', 'updates.js', 'delivery.js', 'getting-started.js'].includes(file)) { res.statusCode = 404; return res.end(); }
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html');
    res.end(fs.readFileSync(path.join(__dirname, file)));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    const pill = page.locator('#delivery-alert');
    const pillIs = text => page.waitForFunction(value => document.querySelector('#delivery-alert').textContent === value, text, { timeout: 6000 });
    const reload = async value => { delivery = value; await page.reload(); };

    // Mike's real case: Drive and Telegram delivered, email expired. Nothing to act on.
    await pillIs('Доставка');
    assert.equal(await pill.getAttribute('data-state'), 'idle');
    assert.equal(await page.locator('#delivery-notice').isHidden(), true);

    await reload(undelivered(weekly, { ...weekly, meeting_id: 'm3' }));
    await pillIs('2 отчета не отправлены');
    assert.equal(await pill.getAttribute('data-state'), 'action_required');
    await reload(undelivered(weekly, { ...weekly, meeting_id: 'm3', uncertain: true }));
    await pillIs('2 отчета могли не дойти');

    await reload(auth);
    await pillIs('Почта: войдите снова');
    await pill.click();
    await page.locator('#settings-panel').waitFor({ state: 'visible', timeout: 3000 });
    assert.equal(await page.locator('#archive-dialog').isHidden(), true, 'Auth pill goes straight to settings');

    await reload(undelivered(weekly));
    await pillIs('Отчет по встрече «Weekly sync» от 16 октября не отправлен');
    const all = await page.evaluate(() => document.body.innerText);
    assert.doesNotMatch(all, /проблем:|issues:/, 'No generic issue counter anywhere');
    await pill.click();
    const resend = page.locator('#delivery-undelivered button');
    await resend.waitFor({ timeout: 3000 });
    assert.equal(await resend.textContent(), 'Отправить снова');
    assert.equal(await page.locator('.delivery-explanation').count(), 0, 'Expired report has one action, not a second explanation');
    await resend.click();
    await pillIs('Доставка');
    assert.equal(retries.length, 1);
    assert.deepEqual({ ...retries[0], request_id: undefined }, { meeting_id: 'm1', channels: ['email'], confirm: true, request_id: undefined });
    assert.ok(jobPolls >= 1);
    assert.equal(await page.locator('#delivery-undelivered button').count(), 0);

    // An uncertain outcome is never stated as a failure; a resend blocked by
    // sign-in offers the sign-in fix instead of "check the internet".
    jobReport = { mail_status: 'failed', mail_error: { provider: 'gws', reason: 'authorization_expired' } };
    await reload(undelivered({ ...weekly, uncertain: true }));
    await pillIs('Отчет по встрече «Weekly sync» от 16 октября мог не дойти');
    await pill.click();
    await page.locator('#delivery-undelivered').filter({ hasText: 'Возможно, он уже пришел' }).waitFor({ timeout: 3000 });
    await page.locator('#delivery-undelivered button').click();
    const settings = page.locator('#delivery-undelivered button', { hasText: 'Открыть настройки' });
    await settings.waitFor({ timeout: 6000 });
    assert.doesNotMatch(await page.locator('#delivery-undelivered').innerText(), /интернет/);
    await settings.click();
    await page.locator('#settings-panel').waitFor({ state: 'visible', timeout: 3000 });

    // MEETONTRACK-92: a report whose file is gone offers to create it again, not "check the archive".
    await reload(undelivered({ ...weekly, missing: true }));
    await pillIs('Отчет по встрече «Weekly sync» от 16 октября не найден');
    await pill.click();
    const recreate = page.locator('#delivery-undelivered button');
    await recreate.waitFor({ timeout: 3000 });
    assert.equal(await recreate.textContent(), 'Создать отчет заново');
    await recreate.click();
    await pillIs('Доставка');
    assert.deepEqual(recreated, [{ meeting_id: 'm1' }]);
    assert.doesNotMatch(await page.evaluate(() => document.body.innerText), /локальный архив/);

    language = 'en';
    await reload(undelivered(weekly));
    await pillIs('Report for “Weekly sync” on October 16 was not sent');
    assert.deepEqual(errors, [], 'UI must run without JavaScript errors');
    console.log('PASS: closed failure silent, plural count, auth to settings, named report + one resend, English');
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
