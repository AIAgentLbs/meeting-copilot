// DOM contract tests without a browser or network; no installer is ever run.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
const html = fs.readFileSync('copilot/web/index.html', 'utf8');
const document = {documentElement: {lang: 'en'}, getElementById(id) {
  assert(html.includes(`id="${id}"`), `missing HTML element ${id}`);
  if (!elements.has(id)) elements.set(id, {textContent: '', hidden: false, handlers: {},
    addEventListener(name, handler) { this.handlers[name] = handler; },
    removeAttribute(name) { delete this[name]; }});
  return elements.get(id);
}};
let clipboard = '';
const context = {document, window: {}, navigator: {clipboard: {writeText: async text => {clipboard = text;}}},
  MutationObserver: class {observe() {}}, AbortSignal,
  fetch() {throw new Error('Unexpected network request');}};
vm.runInNewContext(fs.readFileSync('copilot/web/updates.js', 'utf8'), context);
(async () => {
  const render = context.window.renderReleaseUpdates;
  const get = id => document.getElementById(id);
  for (const [platform, command] of [['macos', 'curl -fsSL https://meetontrack.com/install.sh | bash'],
    ['windows', 'irm https://meetontrack.com/install.ps1 | iex']]) {
    render({version: '0.1.9', platform, enabled: true});
    assert.equal(get('updates-manual').hidden, false);
    assert.equal(get('updates-command').textContent, command);
    await get('updates-copy').handlers.click();
    assert.equal(clipboard, command);
  }
  render({version: '0.1.9', platform: 'macos', enabled: true, notify: true,
    latest: {version: '0.1.10', url: 'https://github.com/AIAgentLbs/meetontrack/releases/tag/v0.1.10', notes: '<script>bad()</script>'}});
  assert.equal(get('updates-notice').hidden, false);
  assert.equal(get('updates-notes').textContent, '<script>bad()</script>');
  document.documentElement.lang = 'ru';
  render({platform: 'windows'});
  assert.equal(get('updates-copy').textContent, 'Скопировать команду обновления');
  context.navigator.clipboard.writeText = async () => {throw new Error('denied');};
  await get('updates-copy').handlers.click();
  assert.match(get('updates-copy-status').textContent, /Не удалось/);
  render({platform: 'untrusted'});
  assert.equal(get('updates-manual').hidden, true);
  assert.equal(get('updates-command').textContent, '');
  console.log('PASS: Mac/Windows commands, copy/failure, RU, notice, safe notes, unsupported platform');
})().catch(error => {console.error(error); process.exitCode = 1;});
