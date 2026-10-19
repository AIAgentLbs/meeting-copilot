// Prevent application source/build workflows from returning to the website tree.
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const files = execFileSync('git', ['ls-files', '-z'], {cwd: root, encoding: 'utf8'}).split('\0').filter(Boolean);
assert.deepEqual(files.filter(p => /^(capture|copilot)\//.test(p)), []);
assert.deepEqual(files.filter(p => p.startsWith('.github/workflows/')), ['.github/workflows/pages.yml']);
for (const required of ['AGENTS.md', 'SITE_TODO.md', 'install.sh', 'docs/install.ps1', 'docs/index.html']) {
  assert(files.includes(required), `Missing website/distribution file: ${required}`);
}
console.log('PASS: website-only tracked tree, Pages-only workflow, installer snapshots retained.');
