// speech.js composes the recorder's name_parts in the page language, as the Mac windows do.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('copilot/web/speech.js', 'utf8');
const start = source.indexOf('  // A language by its name in the page language');
const body = source.slice(start, source.indexOf('  function describe(model)'));
const document = {documentElement: {lang: 'en'}};
const en = () => document.documentElement.lang === 'en';
const {modelName, languageCount} = new Function('en', `${body}; return {modelName, languageCount};`)(en);
const v3 = {base: 'Parakeet v3', variant: '', language_count: 25, language: null};
const ja = {base: 'Parakeet 0.6B', variant: '', language_count: 1, language: 'ja'};
const ship = {base: 'Nemotron 3.5', variant: 'latin, 1120 ms', language_count: 16, language: null};
assert.equal(modelName(v3), 'Parakeet v3 (25 languages)');
assert.equal(languageCount(1), '1 language');
assert.equal(modelName(ja), 'Parakeet 0.6B (Japanese)');
assert.equal(modelName(ship, false), 'Nemotron 3.5, latin, 1120 ms');
assert.equal(modelName(ja, false), 'Parakeet 0.6B (Japanese)');  // the picker keeps the one language
document.documentElement.lang = 'ru';
assert.equal(modelName(v3), 'Parakeet v3 (25 языков)');
for (const [n, text] of [[1, '1 язык'], [2, '2 языка'], [5, '5 языков'], [21, '21 язык']]) assert.equal(languageCount(n), text);
assert.equal(modelName(ja), 'Parakeet 0.6B (японский)');
assert.equal(modelName(null), '');
console.log('speech names ok');
