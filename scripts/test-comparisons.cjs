// Static comparison acceptance: no calls, recordings or paid services are started.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../docs');
const content=require('../docs/compare/content.json');
const ids=new Set(content.criteria.map(item=>item.id));
assert.equal(ids.size,12);
assert.equal(content.criteria[0].id,'open-source');
assert.deepEqual(content.competitors.map(item=>item.slug),['granola','fireflies','bluedot','tldv']);
for(const vendor of content.competitors){
  assert.deepEqual(new Set(Object.keys(vendor.rows)),ids);
  for(const item of [...content.criteria,...Object.values(vendor.rows)]){
    assert(item.refs.length>0,'Every matrix cell needs evidence');
    for(const ref of item.refs)assert(content.sources[ref],`Missing source ${ref}`);
  }
  const url=`https://meetontrack.com/compare/${vendor.slug}/`;
  const html=fs.readFileSync(path.join(root,'compare',vendor.slug,'index.html'),'utf8');
  assert(html.includes(`<link rel="canonical" href="${url}">`));
  assert.equal((html.match(/<h1(?:>|\s)/g)||[]).length,1);
  assert(html.includes('scope="col"')&&html.includes('scope="row"'));
  assert(html.includes('id="open-source"'));
  assert(html.includes('vendor-authored comparison'));
  assert(html.includes('not an independent accuracy benchmark'));
  assert(html.includes('v0.1.9')&&html.includes('v0.1.4'));
  assert(html.includes('Sources checked'));
  assert(html.includes('https://schema.org'));
  assert(html.includes('/#install-windows')&&html.includes('/#install'));
  assert(!/\b(?:src|href)="http:\/\//.test(html));
  for(const ref of html.matchAll(/href="#([^"]+)"/g))assert(html.includes(`id="${ref[1]}"`),`Broken anchor ${ref[1]}`);
  for(const other of content.competitors.filter(item=>item.slug!==vendor.slug))assert(html.includes(`/compare/${other.slug}/`));
}
const hub=fs.readFileSync(path.join(root,'compare/index.html'),'utf8');
const sitemap=fs.readFileSync(path.join(root,'sitemap.xml'),'utf8');
for(const vendor of content.competitors){
 assert(hub.includes(`/compare/${vendor.slug}/`));
 assert(sitemap.includes(`https://meetontrack.com/compare/${vendor.slug}/`));
}
for(const file of ['index.html','ru/index.html'])assert(fs.readFileSync(path.join(root,file),'utf8').includes('href="/compare/"'));
console.log('PASS: 5 comparison routes, 12 consistent criteria, open-source first, cited cells, disclosures, beta scope, SEO and internal links.');
