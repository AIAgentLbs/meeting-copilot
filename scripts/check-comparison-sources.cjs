// On-demand evidence check, deliberately not a scheduled network dependency in CI.
const {sources}=require('../docs/compare/content.json');
const needles={
 'mot-license':['MIT License'],
 'granola-security':['It does not add a bot to your video call','transcription providers','temporarily cached audio'],
 'fireflies-desktop':['Audio and video files are not saved','Live Assist','Speaker 1'],
 'fireflies-terms':['revocable license'],
 'bluedot-security':['Data is stored in AWS'],
 'bluedot-pricing':['5 meetings'],
 'bluedot-terms':['owned by Bluedot'],
 'tldv-product':['NO BOT REQUIRED'],
 'tldv-security':['All our data centers are located in Europe'],
 'tldv-terms':['tldx owns the Services'],
 'tldv-review':['Multi-language meetings','Business']
};
const normalize=s=>s.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,' ').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,' ').replace(/<[^>]*>/g,' ').replace(/&(?:nbsp|amp|quot|#39|apos);/g,' ').replace(/\s+/g,' ').toLowerCase();
(async()=>{
 const entries=Object.entries(sources),results=[];
 for(let offset=0;offset<entries.length;offset+=3){
  results.push(...await Promise.all(entries.slice(offset,offset+3).map(async([id,source])=>{
   try{
    const r=await fetch(source.url,{signal:AbortSignal.timeout(25000)});
    const text=normalize(await r.text());
    const missing=(needles[id]||[]).filter(q=>!text.includes(normalize(q)));
    return {id,url:source.url,status:r.status,pass:r.ok&&!missing.length,missing};
   }catch(error){return{id,url:source.url,pass:false,error:error.message};}
  })));
 }
 console.log(JSON.stringify({checkedAt:new Date().toISOString(),results},null,2));
 if(results.some(item=>!item.pass))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
