// speech.js composes the recorder's name_parts in the page language, as the Mac windows do.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('copilot/web/speech.js', 'utf8');
const body = source.match(/  function modelName\(parts, count = true\) \{[\s\S]*?\n  \}\n/)[0];
const document = {documentElement: {lang: 'en'}};
const word = (english, russian) => document.documentElement.lang === 'en' ? english : russian;
const modelName = new Function('document', 'word', `${body}; return modelName;`)(document, word);
const v3 = {base: 'Parakeet v3', variant: '', language_count: 25, language: null};
const ja = {base: 'Parakeet 0.6B', variant: '', language_count: 1, language: 'ja'};
const ship = {base: 'Nemotron 3.5', variant: 'latin, 1120 ms', language_count: 16, language: null};
assert.equal(modelName(v3), 'Parakeet v3 (25 languages)');
assert.equal(modelName(ja), 'Parakeet 0.6B (Japanese)');
assert.equal(modelName(ship, false), 'Nemotron 3.5, latin, 1120 ms');
assert.equal(modelName(ja, false), 'Parakeet 0.6B (Japanese)');  // the picker keeps the one language
document.documentElement.lang = 'ru';
assert.equal(modelName(v3), 'Parakeet v3 (языков: 25)');
assert.equal(modelName(ja), 'Parakeet 0.6B (японский)');
assert.equal(modelName(null), '');
console.log('speech names ok');
