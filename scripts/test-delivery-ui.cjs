// Exercise the shipped handlers with a synthetic DOM/provider, not a real account.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

async function main() {
  const nodes = new Map(), calls = [], opened = [];
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, {value:'', checked:false, hidden:false, disabled:false,
      dataset:{}, events:{}, files:[], textContent:'',
      addEventListener(type, fn) { this.events[type] = fn; },
      replaceChildren(...children) { this.children = children; },
      querySelector() { return null; }, removeAttribute(key) { delete this[key]; }});
    return nodes.get(id);
  };
  let settings = {profiles:[], email_provider:'smtp', email_enabled:false, drive_enabled:false, own_google:{permissions:[]}};
  let account = {state:'connecting', authorization_url:'https://accounts.google.com/o/oauth2/auth?synthetic=1'};
  const context = {URL, console, setTimeout, crypto:require('node:crypto').webcrypto,
    document:{documentElement:{lang:'en'}, getElementById:node,
      querySelector:selector => node(selector.slice(1)), querySelectorAll:() => []},
    Option:function(text, value) {this.textContent=text; this.value=value;},
    MutationObserver:class {observe() {}},
    window:{open:url => opened.push(url)},
    fetch:async (url, options) => {
      const body = options?.body ? JSON.parse(options.body) : undefined;
      calls.push({url, body});
      if (url.endsWith('/import')) settings = {...settings, google_profile:'custom',
        profiles:[{id:'custom', email:''}], own_google:{client_configured:true, permissions:[]}};
      if (url.endsWith('/disconnect')) settings = {...settings, google_profile:''};
      return {ok:true, json:async () => ({ok:true, settings, account})};
    }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../copilot/web/delivery.js'), 'utf8'), context);
  async function click(id) {
    node(id).events.click({currentTarget:node(id)});
    for(let i=0;i<10;i++) await new Promise(setImmediate);
  }
  const file = node('delivery-oauth-json');
  file.value='selected'; file.files=[{size:20000, text:async () => {throw Error('must not read');}}];
  await click('delivery-google-import');
  assert.equal(calls.length,0); assert.equal(file.value,'');
  assert.match(node('delivery-settings-status').textContent,/16 KB/);
  file.value='selected'; file.files=[{size:20, text:async () => 'not JSON'}];
  await click('delivery-google-import');
  assert.equal(calls.length,0); assert.equal(file.value,'');
  file.files=[{size:20, text:async () => '{"installed":{"client_id":"synthetic"}}'}];
  await click('delivery-google-import');
  assert.equal(calls[0].url,'/api/delivery/google/import');
  assert.equal(node('delivery-email-enabled').checked,false);
  assert.equal(node('delivery-drive-enabled').checked,false);
  assert.equal(node('delivery-own-google').hidden,false);
  assert.equal(file.value,'');
  node('delivery-email-enabled').checked=true; // unsaved draft must not be opted in
  node('delivery-google-email').value='synthetic@example.com';
  node('delivery-oauth-mail').checked=true;
  await click('delivery-google-connect');
  assert.deepEqual(calls.at(-2).body,{google_profile:'custom'});
  assert.deepEqual(calls.at(-1).body,{account:'synthetic@example.com',permissions:['mail']});
  assert.equal(opened.length,1);
  assert.equal(node('delivery-google-login-link').hidden,false);
  await click('delivery-google-disconnect');
  assert.equal(node('delivery-google-login-link').hidden,true);
  assert.equal(node('delivery-google-login-link').href,undefined);
  account={state:'connecting', authorization_url:'https://attacker.example/'};
  await click('delivery-google-connect');
  assert.equal(opened.length,1,'never open an untrusted provider URL');
  assert(calls.every(call => !/retry|send/.test(call.url)));
  console.log('PASS: JSON limits/errors/cleanup, explicit consent, draft isolation, account/permissions, disconnect, URL guard, no sends');
}
main().catch(error => {console.error(error); process.exitCode=1;});
