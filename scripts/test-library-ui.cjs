// Isolated library/live-call acceptance. All meeting data is synthetic.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({headless: true});
  const root = path.resolve(__dirname, '../copilot/web');
  const errors = [], writes = [];
  const meetings = [{meeting_id: 'past', title: 'Integration pilot', started_at: '2026-10-16T10:00:00Z', duration_seconds: 1200,
    transcript_count: 40, journal_count: 2, frame_count: 0, library_status: 'analysis_ready', preview: 'Discussed the rollout.',
    // MEETONTRACK-94: the other side's audio stopped 70 s before the end of the call.
    audio_gap: {started_at: '2026-10-16T10:18:50+00:00', ended_at: '', count: 1, seconds: 70},
    // MEETONTRACK-98: Chrome could not save the PDF three times.
    report_failure: {reason: 'pdf', attempts: 3, failed_at: '2026-10-22T21:19:52+00:00', message: 'Chrome PDF'}},
    {meeting_id: 'empty', title: 'Audio check', started_at: '2026-10-15T10:00:00Z', duration_seconds: 300,
      transcript_count: 0, journal_count: 0, frame_count: 0, library_status: 'no_speech'}];
  const detail = { ...meetings[0], status: 'finished', overview: {points: ['Discussed the rollout.'], questions: ['Who approves the pilot?']},
    transcript: [{speaker: 'Alice', timestamp: '2026-10-16T10:01:00Z', text: 'Discussed the rollout.'}],
    journal: [], frames: [], meeting_chat: [], report: {delivery_on_request: true}, recording_dir: '/synthetic/recordings/past', audio_file: '/synthetic/recordings/past/audio.wav'};
  let rewriteState = 'idle';
  const delivery = () => ({channels: {gmail: {configured: true, state: 'idle', issues: []}}, notifications: [],
    undelivered: meetings[0].report_failure ? [{meeting_id: 'past', channels: [], missing: true, failed: meetings[0].report_failure,
      title: 'Integration pilot', started_at: '2026-10-16T10:00:00Z'}] : []});
  const payload = {preferences: {interface_language: 'en'},
    transcript: {meeting_id: 'current', meeting: 'Current call', status: 'finished', live: false, segments: [], speakers: []},
    recording_health: {capture: {audio_recording: false}},
    copilot: {messages: [], busy: false, analysis: {state: 'idle'}}, journal: [], frames: [], meeting_chat: [], project: {}};
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}, timezoneId: 'Europe/Berlin'});
    page.on('pageerror', error => errors.push(String(error)));
    await page.route('http://library-ui.test/**', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.pathname.startsWith('/api/')) {
        if (request.method() === 'POST') writes.push(url.pathname);
        if (url.pathname === '/api/state') return route.fulfill({json: payload});
        if (url.pathname === '/api/summary-rewrite') return route.fulfill({json: {ok: true, rewrite: {state: rewriteState}}});
        if (url.pathname === '/api/archive') {
          const q = (url.searchParams.get('q') || '').toLowerCase();
          return route.fulfill({json: {ok: true, meetings: meetings.filter(item => item.title.toLowerCase().includes(q)), delivery: delivery()}});
        }
        if (url.pathname === '/api/archive/open-local') return route.fulfill({json: {ok: true}});
        if (url.pathname === '/api/delivery') return route.fulfill({json: {ok: true, delivery: delivery()}});
        if (url.pathname === '/api/archive/report') {
          meetings[0].report_failure = null; detail.report_failure = null;
          return route.fulfill({json: {ok: true, report: {}}});
        }
        if (url.pathname === '/api/archive/rewrite') {
          detail.overview.points = ['Approval is pending.'];
          rewriteState = 'done';
          return route.fulfill({json: {ok: true, rewrite: {state: 'done'}}});
        }
        if (url.pathname === '/api/archive/rename') {
          detail.title = request.postDataJSON().title;
          meetings[0].title = detail.title;
          return route.fulfill({json: {ok: true, meeting: detail}});
        }
        if (url.pathname.startsWith('/api/archive/')) return route.fulfill({json: {ok: true, meeting: detail}});
        return route.fulfill({json: {ok: true}});
      }
      const file = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
      if (!['index.html', 'app.js', 'updates.js', 'styles.css'].includes(file)) return route.abort();
      return route.fulfill({contentType: file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html', body: await fs.readFile(path.join(root, file))});
    });
    await page.goto('http://library-ui.test/');
    await page.locator('#archive-dialog').waitFor({state: 'visible', timeout: 4000});
    assert.equal(await page.locator('.workspace').isVisible(), false);
    await page.getByText('Who approves the pilot?', {exact: true}).waitFor();
    assert((await page.locator('#archive-list').textContent()).includes('No recognized speech'));
    const gap = "The other side's audio stopped at 12:18:50 and did not return before the recording ended (1:10): their last words may be missing.";
    assert.equal(await page.locator('.archive-item .archive-audio-gap').first().textContent(), gap);
    assert.equal(await page.locator('#archive-detail .archive-audio-gap').textContent(), gap);
    assert(!(await page.locator('#archive-list').textContent()).includes('needs attention'));
    assert((await page.locator('#archive-detail .archive-delivery').textContent()).includes('Send with a button below: the meeting is older than 3 days'));
    assert.equal(await page.locator('.archive-item .archive-report-failure').first().textContent(),
      'Report not created. Open the meeting and press Create the report again.');
    assert.equal(await page.locator('#archive-detail .archive-report-failure-detail p').textContent(),
      'The report was not created: Chrome could not save the PDF. Attempts: 3, last at 23:19. The app tries again by itself in 30 minutes, or press Create the report again.');
    await page.waitForFunction(() => document.querySelector('#delivery-alert')?.textContent.includes('was not created'));
    assert.equal(await page.locator('#delivery-alert').getAttribute('data-state'), 'action_required');
    await page.locator('#archive-detail .archive-report-failure-detail').getByRole('button', {name: 'Create the report again', exact: true}).click();
    await page.locator('#archive-detail .archive-report-failure-detail').waitFor({state: 'detached'});
    assert.equal(await page.locator('.archive-item .archive-report-failure').first().textContent(), '');
    assert(writes.includes('/api/archive/report'));
    await page.locator('#archive-search').fill('Integration');
    await page.waitForFunction(() => document.querySelectorAll('.archive-item').length === 1);
    await page.locator('#archive-search').fill('');
    await page.waitForFunction(() => document.querySelectorAll('.archive-item').length === 2);
    await page.screenshot({path: '/tmp/meetontrack-library-desktop.png', fullPage: true});
    payload.transcript.status = 'recording'; payload.transcript.live = true;
    payload.recording_health.capture.audio_recording = true;
    await page.locator('#refresh-button').click();
    await page.locator('#archive-dialog').waitFor({state: 'hidden'});
    assert.equal(await page.locator('.workspace').isVisible(), true);
    writes.length = 0;
    await page.locator('#question').fill('Keep this unsent note');
    await page.locator('#archive-button').click();
    await page.locator('#archive-dialog').waitFor({state: 'visible'});
    assert.equal(await page.locator('.workspace').isVisible(), true);
    assert.equal(await page.locator('#archive-dialog').getAttribute('data-mode'), 'drawer');
    await page.locator('.archive-item').first().click();
    await page.getByText('Who approves the pilot?', {exact: true}).waitFor();
    await page.locator('#archive-rename-button').click();
    await page.locator('#archive-title-input').fill('Confirmed pilot');
    await page.locator('#archive-title-save').click();
    await page.locator('#archive-detail h2').getByText('Confirmed pilot', {exact: true}).waitFor();
    await page.locator('#archive-detail').getByRole('button', {name: 'Open recording', exact: true}).click();
    await page.locator('#archive-detail').getByRole('button', {name: 'Open meeting folder', exact: true}).click();
    await page.locator('#archive-feedback-input').fill('Focus on approval.');
    await page.locator('#archive-detail').getByRole('button', {name: 'Update summary', exact: true}).click();
    await page.getByText('Approval is pending.', {exact: true}).waitFor();
    await page.keyboard.press('Escape');
    await page.locator('#archive-dialog').waitFor({state: 'hidden'});
    assert.equal(await page.locator('#question').inputValue(), 'Keep this unsent note');
    assert.deepEqual(writes, ['/api/archive/rename', '/api/archive/open-local', '/api/archive/open-local', '/api/archive/rewrite']);
    assert.equal(await page.locator('#meeting-title').textContent(), 'Current call');
    payload.transcript.status = 'finished'; payload.transcript.live = false;
    payload.recording_health.capture.audio_recording = false;
    await page.locator('#refresh-button').click();
    await page.locator('#archive-dialog').waitFor({state: 'visible'});
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: '/tmp/meetontrack-library-mobile.png', fullPage: true});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.locator('#archive-close').click();
    await page.locator('#refresh-button').click();
    assert.equal(await page.locator('#archive-dialog').isVisible(), false);
    assert.deepEqual(errors, []);
    console.log('PASS: idle library, live drawer, search, statuses, report failure and retry, overview, rename, preserved call/draft, close, responsive layout');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
