// Synthetic browser acceptance; never starts Capture, installs software or sends mail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/Users/m/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = path.resolve(__dirname, '../docs');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const external = [];
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname !== 'meetontrack.com') {
        if (/google-analytics|googletagmanager|web-analytics/.test(url.hostname)) external.push(url.href);
        return route.fulfill({ status: 200, body: '', contentType: 'text/javascript' });
      }
      if (url.pathname === '/analytics-config.json') return route.fulfill({ json: {
        ga4: 'G-TEST12345', umamiWebsiteId: '3f33997f-c79d-41b4-a5a9-e95cfa4f185e',
        umamiScript: 'https://web-analytics.aiagentlbs.app/script.js',
      } });
      const relative = url.pathname.endsWith('/') ? url.pathname + 'index.html' : url.pathname;
      const file = path.join(root, relative);
      if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'Not found' });
      const type = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.svg':'image/svg+xml', '.xml':'application/xml' }[path.extname(file)] || 'text/plain';
      return route.fulfill({ status: 200, body: fs.readFileSync(file), contentType: type });
    });
    const page = await context.newPage();
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('https://meetontrack.com/', { waitUntil:'networkidle' });
    assert((await page.title()).startsWith('MeetOnTrack'), 'EN title must identify the adopted brand');
    assert.equal(await page.locator('link[rel=canonical]').getAttribute('href'),'https://meetontrack.com/');
    assert.equal(await page.locator('a[href="mailto:contacts@meetontrack.com"]').count(),1);
    assert.equal(external.length,0,'No analytics request before consent');
    await page.getByRole('button',{name:'Reject analytics',exact:true}).click();
    await page.reload({waitUntil:'networkidle'});
    assert.equal(external.length,0,'Reject choice persists without analytics');
    await page.getByRole('button',{name:'Analytics settings',exact:true}).click();
    await page.getByRole('button',{name:'Allow analytics',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('script[data-site-analytics]').length===2);
    assert.equal(external.filter(u=>u.includes('googletagmanager.com')).length,1);
    assert.equal(external.filter(u=>u.includes('web-analytics.aiagentlbs.app')).length,1);
    await page.getByRole('button',{name:'Analytics settings',exact:true}).click();
    await page.getByRole('button',{name:'Reject analytics',exact:true}).click();
    await page.waitForLoadState('networkidle');
    const n=external.length;
    await page.reload({waitUntil:'networkidle'});
    assert.equal(external.length,n,'Revocation survives reload');
    await page.goto('https://meetontrack.com/ru/',{waitUntil:'networkidle'});
    assert.equal(await page.locator('link[rel=canonical]').getAttribute('href'),'https://meetontrack.com/ru/');
    assert.equal(await page.locator('html').getAttribute('lang'),'ru');
    assert.equal(await page.locator('h1').count(),1);
    const contrast = await page.evaluate(() => {
      const luminance = value => {
        const rgb=value.match(/[\d.]+/g).slice(0,3).map(v=>{
          const n=Number(v)/255; return n<=0.04045?n/12.92:((n+0.055)/1.055)**2.4;
        });
        return rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722;
      };
      const fg=luminance(getComputedStyle(document.querySelector('.flow > li > span')).color);
      const bg=luminance(getComputedStyle(document.body).backgroundColor);
      return (Math.max(fg,bg)+0.05)/(Math.min(fg,bg)+0.05);
    });
    assert(contrast>=4.5,'Small step numbers must remain readable against the page background');
    for(const width of [390,1440]) {
      await page.setViewportSize({width,height:900});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'No horizontal overflow');
    }
    assert.deepEqual(errors,[]);
    console.log('PASS: brand/canonical/contact, analytics blocked until consent, accept/reject/revoke, RU and mobile layout.');
    await context.close();
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
