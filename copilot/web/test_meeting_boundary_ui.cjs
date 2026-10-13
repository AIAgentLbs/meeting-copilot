// Real browser against actual UI files, synthetic API only; never a live call.
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');

(async () => {
  let identity = 'physical', requests = [], conflict = false, loseResponse = false;
  const state = () => ({
    transcript: { meeting_id: identity, physical_meeting_id: 'physical', meeting: identity === 'physical' ? 'Example' : 'Second',
      status: 'recording', started_at: new Date().toISOString(), segments: [{timestamp:new Date().toISOString(),source:'system',text:'Synthetic crossing',spans_boundary:true}], live: true, latest_age_seconds: 0 },
    copilot: { busy: false, messages: [], analysis: { state: 'idle' } },
    recording_health: { meeting_id: 'physical', checked_at: Date.now()/1000, state: 'healthy', capture: { audio_recording: true, state: 'recording' } },
    frames: [], journal: [], meeting_chat: [], project: { repositories: [], kind: 'all' }, preferences: { interface_language: 'ru' }, delivery: {},
  });
  const server = http.createServer((req, res) => {
    if (req.url === '/api/state') { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify(state())); }
    if (req.url === '/api/archive') return res.end(JSON.stringify({ok:true,meetings:[{meeting_id:'second',title:'Second',started_at:new Date().toISOString(),transcript_count:1,journal_count:0,frame_count:0}]}));
    if (req.url === '/api/archive/second') return res.end(JSON.stringify({ok:true,meeting:{meeting_id:'second',title:'Second',started_at:new Date().toISOString(),duration_seconds:300,explicit_boundary:true,audio_range:{start_seconds:300,end_seconds:600},transcript:state().transcript.segments,journal:[],frames:[],meeting_chat:[]}}));
    if (req.url === '/api/meeting/new') {
      let body = ''; req.on('data', data => body += data); req.on('end', () => {
        const request = JSON.parse(body); requests.push(request);
        res.setHeader('Content-Type', 'application/json');
        if (conflict) { res.statusCode = 409; return res.end(JSON.stringify({error:'Meeting changed'})); }
        identity = 'second';
        if (loseResponse) { loseResponse = false; res.statusCode = 504; return res.end('{}'); }
        res.end(JSON.stringify({meeting_id:identity, physical_meeting_id:'physical', title:'Second'}));
      }); return;
    }
    if (req.url.startsWith('/api/')) return res.end('{}');
    const file = req.url === '/' ? 'index.html' : req.url.slice(1);
    if (!['index.html','styles.css','app.js'].includes(file)) { res.statusCode=404; return res.end(); }
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html');
    res.end(fs.readFileSync(path.join(__dirname,file)));
  });
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const browser = await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    const button = page.locator('#new-meeting-button');
    await button.waitFor({timeout:3000});
    await page.locator('.boundary-provenance').filter({hasText:'Реплика пересекает границу'}).waitFor({timeout:3000});
    await button.click();
    await page.locator('#new-meeting-cancel').click();
    assert.equal(requests.length,0,'Cancel must not write');
    await button.click();
    loseResponse = true;
    await page.locator('#new-meeting-title').fill('Second');
    await page.locator('#new-meeting-confirm').click();
    await page.locator('#new-meeting-error').filter({hasText:/./}).waitFor();
    await page.locator('#new-meeting-confirm').click();
    await page.waitForFunction(() => !document.querySelector('#new-meeting-dialog').open);
    assert.equal(requests.length,2);
    assert.equal(requests[0].request_id,requests[1].request_id,'Ambiguous retry must use same token');
    assert.equal(requests[1].expected_meeting_id,'physical');
    await page.waitForFunction(() => document.querySelector('#new-meeting-status').textContent.includes('Second'));
    assert.equal(await button.isDisabled(),false,'Physical health must still match logical meeting');
    conflict = true;
    await button.click(); await page.locator('#new-meeting-confirm').click();
    await page.locator('#new-meeting-error').filter({hasText:/./}).waitFor();
    assert.equal(await page.locator('#new-meeting-dialog').evaluate(el=>el.open),true);
    await page.locator('#new-meeting-cancel').click();
    await page.locator('#archive-button').click();
    await page.locator('.archive-item').first().click();
    await page.locator('#archive-detail .archive-audio-range').filter({hasText:'5:00'}).waitFor();
    assert.equal(await page.locator('#archive-detail .boundary-provenance').count(),1,'History must disclose crossing speech');
    await page.locator('#archive-close').click();
    await page.locator('[data-language="en"]').click();
    await button.click();
    assert.equal(await page.locator('#new-meeting-heading').textContent(),'Start new meeting');
    if (process.env.MEETING_UI_SCREENSHOT_DIR) {
      await page.screenshot({path:path.join(process.env.MEETING_UI_SCREENSHOT_DIR,'meeting-boundary-desktop.png')});
      await page.setViewportSize({width:390,height:844});
      await page.screenshot({path:path.join(process.env.MEETING_UI_SCREENSHOT_DIR,'meeting-boundary-mobile.png')});
    }
    assert.deepEqual(errors,[], 'UI must run without JavaScript errors');
    console.log('PASS: cancel, ambiguous retry, success, physical health, conflict, English, responsive screenshots');
  } finally { await browser.close(); await new Promise(resolve=>server.close(resolve)); }
})().catch(error=>{ console.error(error); process.exitCode=1; });
