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
      if (url.pathname.startsWith('/media/')) {
        const asset = require('../docs/screenshot-assets.json').assets.find(item=>url.pathname === '/media/'+item.file);
        if (!asset) return route.fulfill({status:404,body:'Unknown screenshot'});
        // Rendering/layout fixture only; live acceptance verifies actual JPEG bytes.
        return route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="1460" height="1083"><rect width="1460" height="1083" fill="#f3f4ef"/></svg>'});
      }
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
    for (const language of ['en','ru']) {
      await page.goto(language==='en'?'https://meetontrack.com/':'https://meetontrack.com/ru/');
      for(const width of [390,768,1440]) {
        await page.setViewportSize({width,height:844});
        await page.evaluate(()=>scrollTo(0,0));
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'No horizontal overflow');
        const buttons = await page.locator('.platform-actions a').evaluateAll(links=>links.map(a=>({href:a.getAttribute('href'),top:a.getBoundingClientRect().top,bottom:a.getBoundingClientRect().bottom})));
        assert.deepEqual(buttons.map(a=>a.href),['#install','#install-windows']);
        assert(buttons.every(a=>a.top>=0 && a.bottom<844),'Both install choices must be on the first screen');
        assert.equal(await page.locator('.product-shot img').count(),2,'Actual app views must remain present');
        assert.equal(await page.locator('.product-shot a[target="_blank"]').count(),2,'Screenshots must open at full size');
        await page.locator('.platform-actions a[href="#install-windows"]').click();
        await page.locator('#windows-install-command').waitFor();
        assert((await page.locator('#windows-install-command').innerText()).includes('irm https://meetontrack.com/install.ps1 | iex'));
        await page.evaluate(()=>scrollTo(0,0));
      }
    }
    for (const route of ['/compare/',...require('../docs/compare/content.json').competitors.map(v=>`/compare/${v.slug}/`)]) {
      await page.goto('https://meetontrack.com'+route);
      for (const width of [390,768,1440]) {
        await page.setViewportSize({width,height:844});
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${route} overflow at ${width}`);
        assert(await page.locator('.breadcrumbs a[href="/"]').isVisible(),'Breadcrumbs must not inherit hidden mobile header links');
        assert.equal(await page.locator('h1').count(),1);
        if(route!=='/compare/') {
          assert.equal(await page.locator('.comparison-table tbody tr').count(),12);
          assert.equal(await page.locator('.comparison-table thead th[scope="col"]').count(),3);
          if(width===390)assert(await page.locator('#open-source .column-label').first().isVisible());
          if(width===1440)assert.equal(await page.locator('.comparison-table thead th').first().evaluate(e=>getComputedStyle(e).position),'sticky');
        }
      }
    }
    assert.deepEqual(errors,[]);
    console.log('PASS: brand/consent, EN/RU, Windows + macOS above the fold at 390/768/1440px, install anchors, screenshots, no overflow.');
    await context.close();
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
