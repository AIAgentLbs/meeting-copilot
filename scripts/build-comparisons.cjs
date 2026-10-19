// Deterministic static pages. Claims and evidence live in the reviewed dataset.
const fs=require('node:fs');
const path=require('node:path');
const data=require('../docs/compare/content.json');
const styleVersion=require('node:crypto').createHash('sha256').update(fs.readFileSync(path.resolve(__dirname,'../docs/styles.css'))).digest('hex').slice(0,12);
const presentation=require('../docs/compare/presentation.json');
const logos=require('../docs/comparison-logo-assets.json');
const checkedAt=vendor=>vendor.checkedAt||data.checkedAt;
const latestCheck=[data.checkedAt,...data.competitors.map(checkedAt)].sort().at(-1);
const names=data.competitors.map(v=>v.name).join(', ');
const root=path.resolve(__dirname,'../docs/compare');
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const homepage=id=>id==='meetontrack'?'https://meetontrack.com/':logos.assets.find(a=>a.id===id).sourcePage;

function logo(id){
 const src=id==='meetontrack'?'/favicon.svg':'/media/logos/'+logos.assets.find(a=>a.id===id).file;
 return `<img class="product-logo" src="${src}" width="32" height="32" alt="">`;
}
const symbols={
 yes:'<path d="m5 12 4 4 10-10"/>',
 no:'<path d="m6 6 12 12M18 6 6 18"/>',
 partial:'<circle cx="12" cy="12" r="8"/><path d="M12 4v16"/>',
 unknown:'<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 4 2l-1.5 1v1M12 16v.1"/>',
 different:'<path d="M4 8h16m-4-4 4 4-4 4M20 16H4m4-4-4 4 4 4"/>'
};
const mark=status=>`<span class="comparison-mark mark-${status}"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${symbols[status]}</svg><span>${escape(presentation.labels[status])}</span></span>`;
const legend=`<div class="comparison-legend" aria-label="Comparison key">${Object.keys(presentation.labels).map(mark).join('')}</div><p class="comparison-key-note">Marks summarize reviewed documentation, not quality scores. Not verified does not mean unavailable. Different approach is not a disadvantage. Important conditions stay visible; expand a cell for details.</p>`;
function cell(product,name,row,text){
 const entry=presentation.products[product]?.[row.id];
 if(!entry||!presentation.labels[entry[0]]||!entry[1])throw Error(`Missing comparison verdict: ${product}/${row.id}`);
 return `<td><span class="column-label" aria-hidden="true">${logo(product)} ${escape(name)}</span>${mark(entry[0])}<p class="comparison-short">${escape(entry[1])}</p><details class="comparison-detail"><summary aria-label="Details for ${escape(name)}: ${escape(row.label)}">Details</summary><div><p>${escape(text)}</p></div></details></td>`;
}

const header=`<header class="nav shell"><a class="brand" href="/">${logo("meetontrack")}<span>MeetOnTrack</span><small>AI AGENT LABS</small></a><nav aria-label="Primary"><a href="/#install-windows">Windows</a><a href="/#install">macOS</a><a href="/">Home</a></nav></header>`;
const footer=`<footer class="shell"><span>MeetOnTrack by <a href="https://aiagentlbs.com">AI Agent Labs</a></span><span><a href="/privacy.html">Privacy</a> · <button type="button" class="analytics-settings" data-analytics-settings>Analytics settings</button></span><span>Product marks identify their owners; no endorsement implied.</span></footer><script defer src="/analytics.js"></script>`;
const actions=`<div class="actions platform-actions"><a class="button" href="/#install">Install for macOS</a><a class="button" href="/#install-windows">Install for Windows</a></div>`;
function document(title,description,url,body,schema){
 return `<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(title)}</title><meta name="description" content="${escape(description)}"><link rel="canonical" href="${url}"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Geologica:wght@400;500;600;700&amp;family=Newsreader:opsz,wght@6..72,500&amp;display=swap" rel="stylesheet"><link rel="stylesheet" href="/styles.css?v=${styleVersion}"><meta property="og:type" content="article"><meta property="og:title" content="${escape(title)}"><meta property="og:description" content="${escape(description)}"><meta property="og:url" content="${url}"><meta name="twitter:card" content="summary"><script type="application/ld+json">${JSON.stringify(schema).replace(/</g,'\\u003c')}</script></head><body class="compare-page">${header}${body}${footer}</body></html>\n`;
}
const choices=items=>`<ul class="comparison-directory">${items.map(v=>`<li><strong>${logo(v.slug)} ${escape(v.name)}</strong><span>${escape(v.short)}</span></li>`).join('')}</ul>`;
const method=date=>`<section class="comparison-method" id="method"><h2>How this comparison was made</h2><p>Published by AI Agent Labs, maker of MeetOnTrack. This is a vendor-authored comparison, not an independent accuracy benchmark. Competitor capabilities come from official product, help, pricing and policy pages, checked on ${date}. We did not run comparative performance tests.</p><p>We use the same criteria for every product. An undocumented feature is marked unverified, not absent. Device capture, on-device speech recognition, cloud storage and cloud AI are separate questions. A free plan, public SDK or MCP endpoint is not an open-source licence for the whole application.</p><p>Check current plans on the product’s homepage. Plan limits and capture modes can change. Obtain the required participant consent regardless of whether a bot appears in the meeting.</p></section>`;
const beta=`<section class="comparison-method" id="beta-scope"><h2>Compare the package you can actually install</h2><p>The pinned packages are Mac v0.1.9 and Windows v0.1.4. They have different requirements and limitations. The source tree can be newer than either package. Development previews on the homepage do not extend the public beta's feature scope.</p><p>Automatic multilingual recognition, model choices, update notifications and newer integrations must be checked against the exact installed build. We do not claim tested parity between operating systems, guaranteed speaker attribution, fully offline AI or enterprise compliance certification.</p></section>`;
let changed=0;
function write(relative,html){
 const file=path.join(root,relative);const old=fs.existsSync(file)?fs.readFileSync(file,'utf8'):'';
 if(old===html)return;
 if(process.argv.includes('--check'))throw Error(`Generated comparison is stale: ${relative}`);
 fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,html);changed++;
}
for(const vendor of data.competitors){
 const date=checkedAt(vendor);
 const url=`https://meetontrack.com/compare/${vendor.slug}/`;
 const table=`<section id="criteria" class="criteria-section"><h2>At a glance</h2>${legend}<table class="comparison-table"><caption>MeetOnTrack and ${escape(vendor.name)}: documented capabilities and limitations</caption><thead><tr><th scope="col">Criterion</th><th scope="col">${logo('meetontrack')} MeetOnTrack</th><th scope="col">${logo(vendor.slug)} ${escape(vendor.name)}</th></tr></thead><tbody>${data.criteria.map(row=>`<tr id="${row.id}"><th scope="row">${escape(row.label)}</th>${cell('meetontrack','MeetOnTrack',row,row.ours)}${cell(vendor.slug,vendor.name,row,vendor.rows[row.id].text)}</tr>`).join('')}</tbody></table></section>`;
 const body=`<main class="shell comparison-main"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><span>Comparison</span><span>/</span><span>${escape(vendor.name)}</span></nav><article><header class="comparison-intro"><h1>${logo("meetontrack")} MeetOnTrack<br><em>vs ${logo(vendor.slug)} ${escape(vendor.name)}</em></h1><p class="lede">${escape(vendor.summary)}</p><p class="comparison-meta">Sources checked <time datetime="${date}">${date}</time> · By AI Agent Labs</p><p class="product-homepages"><a href="${homepage('meetontrack')}">MeetOnTrack homepage</a> · <a href="${homepage(vendor.slug)}">${escape(vendor.name)} homepage</a></p>${actions}<div class="article-jumps"><a href="#criteria">Compare criteria</a><a href="#open-source">Open-source licence</a></div></header><section class="choice-pair" aria-label="Which product fits"><div><h2>Choose MeetOnTrack if...</h2><p>${escape(vendor.chooseOurs)}</p></div><div><h2>Choose ${escape(vendor.name)} if...</h2><p>${escape(vendor.chooseTheirs)}</p></div></section>${table}<section class="comparison-method"><h2>${escape(vendor.tradeoffTitle)}</h2><p>${escape(vendor.tradeoff)}</p><h3>Try this before switching</h3><p>${escape(vendor.test)}</p></section>${beta}${method(checkedAt(vendor))}</article></main>`;
 const schema={'@context':'https://schema.org','@type':'Article',headline:`MeetOnTrack vs ${vendor.name}`,description:vendor.description,datePublished:date,dateModified:date,author:{'@type':'Organization',name:'AI Agent Labs',url:'https://aiagentlbs.com'},mainEntityOfPage:url};
 write(vendor.slug+'/index.html',document(vendor.title,vendor.description,url,body,schema));
}
const date=latestCheck;
const hubUrl='https://meetontrack.com/compare/';
const hubBody=`<main class="shell comparison-main"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><span>Comparisons</span></nav><header class="comparison-intro"><h1>Compare meeting assistants.<br><em>Keep the trade-offs visible.</em></h1><p class="lede">An open-source AI meeting assistant is a different choice from a managed cloud notetaker. Compare MeetOnTrack with ${names} on the same criteria, starting with source access and control over your meeting data.</p><p class="comparison-meta">Latest comparison review <time datetime="${date}">${date}</time> · Vendor-authored by AI Agent Labs</p>${actions}</header>${choices(data.competitors)}<section class="comparison-method"><h2>Open source is not a free-plan checkbox</h2><p>For MeetOnTrack, the public MIT licence gives you rights to inspect, modify and redistribute the application, subject to its terms and third-party notices. That does not make Codex or another connected AI provider open source, and it does not make every feature work offline.</p><p>For each alternative, we distinguish the complete product's licence from public SDKs, APIs, MCP connections and open-source dependencies. Where full-product source rights cannot be verified, the page says so rather than inventing a negative.</p><h3>The criteria</h3><ul class="criteria-list">${data.criteria.map(row=>`<li>${escape(row.label)}</li>`).join('')}</ul></section>${beta}${method('the dates shown on the individual comparisons')}</main>`;
write('index.html',document('Compare AI Meeting Assistants | MeetOnTrack',`Compare MeetOnTrack with ${names}. Open source, data control, multilingual calls, context, pricing and honest beta limits.`,hubUrl,hubBody,{'@context':'https://schema.org','@type':'CollectionPage',name:'AI meeting assistant comparisons',url:hubUrl,mainEntity:{'@type':'ItemList',itemListElement:data.competitors.map((v,i)=>({'@type':'ListItem',position:i+1,name:`MeetOnTrack vs ${v.name}`}))}}));
console.log(`${process.argv.includes('--check')?'Checked':'Built'} ${data.competitors.length+1} comparison pages (${changed} changed).`);
