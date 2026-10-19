// Static comparison acceptance: no calls, recordings or paid services are started.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../docs');
const content=require('../docs/compare/content.json');
const presentation=require('../docs/compare/presentation.json');
const logoAssets=require('../docs/comparison-logo-assets.json').assets;
const noComparisonLinks=html=>assert(!/<a\b[^>]*href=["'][^"']*\/compare\//i.test(html),'Comparison links must not appear in visible navigation');
const homepageLinksOnly=html=>{
 const allowed=new Set(['https://meetontrack.com/','https://aiagentlbs.com',...logoAssets.map(a=>a.sourcePage)]);
 for(const [,url] of html.matchAll(/<a\b[^>]*href="(https?:[^"]+)"/g)){
  assert(allowed.has(url),`Only official homepages may be linked: ${url}`);
 }
 assert(!/source-ref|cell-sources|id="sources"|Details &amp; sources|"citation":/.test(html),'Source links and citations belong in repository evidence, not published pages');
};
const ids=new Set(content.criteria.map(item=>item.id));
assert.equal(ids.size,12);
assert.equal(content.criteria[0].id,'open-source');
assert.deepEqual(content.competitors.map(item=>item.slug),['meetscribe','granola','fireflies','bluedot','tldv']);
assert.deepEqual(new Set(Object.keys(presentation.products)),new Set(['meetontrack',...content.competitors.map(v=>v.slug)]));
for(const product of Object.values(presentation.products)){
 assert.deepEqual(new Set(Object.keys(product)),ids);
 for(const [status,summary] of Object.values(product)){
  assert(Object.hasOwn(presentation.labels,status));
  assert(summary.length>0&&summary.length<=100);
 }
}
for(const asset of logoAssets){
 assert.equal(asset.file,`${asset.id}.png`);
 assert.match(asset.sha256,/^[a-f0-9]{64}$/);
 assert(asset.url.startsWith('https://')&&asset.sourcePage.startsWith('https://'));
}
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
  const date=vendor.checkedAt||content.checkedAt;
  assert(html.includes(`<time datetime="${date}">${date}</time>`));
  assert(html.includes(`"dateModified":"${date}"`));
  assert(html.includes('https://schema.org'));
  assert(html.includes('/#install-windows')&&html.includes('/#install'));
  assert(!/\b(?:src|href)="http:\/\//.test(html));
  for(const ref of html.matchAll(/href="#([^"]+)"/g))assert(html.includes(`id="${ref[1]}"`),`Broken anchor ${ref[1]}`);
  noComparisonLinks(html);
  assert(!html.includes('MeetOnTrack public beta'));
  assert.match(html,/href="\/styles\.css\?v=[a-f0-9]{12}"/,'Changed styles must invalidate the browser cache');
  assert(html.includes('Not verified does not mean unavailable'));
  assert.equal((html.match(/class="comparison-detail"/g)||[]).length,24);
  assert.equal((html.match(/<summary aria-label="Details for /g)||[]).length,24);
  homepageLinksOnly(html);
  assert(html.includes(`href="${logoAssets.find(a=>a.id===vendor.slug).sourcePage}"`));
  assert(html.includes(`/media/logos/${vendor.slug}.png`));
  assert(html.includes('src="/favicon.svg"'));
  assert(html.includes('stroke="currentColor"')&&html.includes('aria-hidden="true"'));
  assert(logoAssets.some(a=>a.id===vendor.slug));
}
const hub=fs.readFileSync(path.join(root,'compare/index.html'),'utf8');
const sitemap=fs.readFileSync(path.join(root,'sitemap.xml'),'utf8');
for(const vendor of content.competitors){
 assert(hub.includes(vendor.name));
 assert(sitemap.includes(`https://meetontrack.com/compare/${vendor.slug}/`));
}
noComparisonLinks(hub);
homepageLinksOnly(hub);
const workflow=fs.readFileSync(path.resolve(root,'../.github/workflows/pages.yml'),'utf8');
assert(!workflow.includes('cp -R docs/compare'),'Do not publish comparison evidence JSON');
assert(workflow.includes('for page in docs/compare/*/index.html'));
for(const file of ['index.html','ru/index.html'])noComparisonLinks(fs.readFileSync(path.join(root,file),'utf8'));
const meetscribe=content.competitors.find(v=>v.slug==='meetscribe');
assert(meetscribe.rows['open-source'].refs.includes('meetily-license'));
assert(meetscribe.rows['open-source'].refs.includes('meetscribe-terms'));
assert(meetscribe.rows.processing.refs.includes('meetscribe-privacy'));
assert(meetscribe.tradeoff.includes('separate codebase'));
assert(!hub.includes('Sources checked <time datetime="2026-10-16"'));
assert.equal(presentation.products.granola.recordings[0],'no');
assert.equal(presentation.products.fireflies.recordings[0],'partial');
assert.equal(presentation.products.meetontrack.readiness[0],'partial');
for(const vendor of content.competitors)assert.equal(presentation.products[vendor.slug]['open-source'][0],'unknown','Unverified source rights must not become a cross');
console.log(`PASS: ${content.competitors.length+1} routes, 12 criteria, explicit marks, qualifiers, accessible disclosures, logos, neutral branding and no visible comparison links.`);
