// Handler regression test, not a substitute for visual verification in Chrome.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const web = path.resolve(__dirname, '../copilot/web');
const html = fs.readFileSync(path.join(web, 'index.html'), 'utf8');
class Element {
  constructor() { this.children=[]; this.value=''; this.hidden=false; this.disabled=false; this.listeners={}; }
  setAttribute(key,value) {this[key]=value;}
  addEventListener(key,fn) {this.listeners[key]=fn;}
  replaceChildren(...children) {this.children=children;}
  append(...children) {this.children.push(...children);}
  focus() {this.focused=true;}
  scrollIntoView() {}
  close() {this.open=false;}
  click() {return this.onclick?.() || this.listeners.click?.();}
}
const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const el = id => {assert(elements.has(id), `Missing real HTML element: ${id}`); return elements.get(id);};
const document = {documentElement:{lang:'en'},getElementById:el,createElement:()=>new Element(),createTextNode:text=>({textContent:text})};
let folders=[], calls=[];
const fetch = async (url,options) => {
  const data=options?.body ? JSON.parse(options.body):{};
  calls.push([url,data]);
  let result={ok:true};
  if(url==='/api/getting-started') result={...result,folders,capture_installed:true,live_enabled:true};
  else if(url==='/api/context-folders/choose') result.path='/synthetic/project';
  else if(url==='/api/context-folders/add') {
    assert.equal(data.path,'/synthetic/project');
    folders=[{id:'one',name:'project',path:data.path}]; result.folders=folders;
  } else if(url==='/api/context-folders/remove') {folders=[];result.folders=folders;}
  else if(url==='/api/ai') result={...result,providers:[],purposes:{}};
  else if(url==='/api/getting-started/check-ai') result.ai={state:'error',message:'AI_LIMIT: quota'};
  return {ok:true,json:async()=>result};
};
const window={addEventListener(){}};
const localStorage={getItem:()=>null,setItem(){}};
vm.runInNewContext(fs.readFileSync(path.join(web,'getting-started.js'),'utf8'),{
  document,window,fetch,localStorage,MutationObserver:class {observe(){}},setTimeout,console
});
(async()=>{
  await new Promise(resolve=>setImmediate(resolve));
  assert(!html.includes('context-document-input'), 'No upload input');
  assert.equal(el('context-folders-title').textContent,'Folders on this computer');
  await el('context-folder-choose').click();
  assert.equal(el('context-folder-path').value,'/synthetic/project');
  assert.equal(folders.length,0,'Selecting a folder must not authorize reading before Connect');
  await el('context-folder-add').click();
  assert.equal(folders.length,1);
  assert.equal(el('context-folder-list').children.length,1);
  await el('context-folder-list').children[0].children[1].click();
  assert.equal(folders.length,0);
  let settingsOpened=false;
  el('settings-open').onclick=()=>{settingsOpened=true;};
  el('project-dialog').open=true;
  el('context-google-open').click();
  assert(settingsOpened);
  assert.equal(el('project-dialog').open,false);
  assert.equal(el('google-context-settings').open,true);
  document.documentElement.lang='ru';
  await el('startup-ai-check').click();
  assert.equal(el('context-folder-add').textContent,'Подключить папку (только чтение)');
  assert(el('startup-ai-status').textContent.includes('Лимит аккаунта ИИ'));
  assert(!calls.some(([url])=>url.includes('context-documents')));
  console.log('PASS: real HTML controls, choose/confirm, connect/disconnect, Google settings, RU labels, AI error, no upload API');
})().catch(error=>{console.error(error);process.exitCode=1;});
