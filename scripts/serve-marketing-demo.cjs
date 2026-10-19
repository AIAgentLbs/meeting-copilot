// Isolated, synthetic screenshot fixture. Never reads user settings or recordings.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
// Read application assets from the software checkout or an unpacked release.
// Never use the site's historical copy of the application as a product source.
const root = process.env.MEETONTRACK_WEB_ROOT
  ? path.resolve(process.env.MEETONTRACK_WEB_ROOT)
  : path.resolve(__dirname, '../../meeting-copilot-private-copy/copilot/web');
if (!fs.existsSync(path.join(root, 'index.html'))) {
  throw new Error('Set MEETONTRACK_WEB_ROOT to the application web directory');
}
const at = '2026-10-16T12:32:00Z';
const conversation = [
  ['self', 'Me', 'What still needs to happen before we launch the pilot?'],
  ['alice', 'Alice', 'The integration is ready. We still need someone to approve the access review.'],
  ['self', 'Me', 'Who owns that review, and when can we confirm it?'],
  ['alice', 'Alice', 'I will own the review. Let us make the decision on Friday.'],
  ['self', 'Me', 'Agreed. Keep the pilot limited to the test workspace until then.'],
  ['alice', 'Alice', 'Can you share the launch checklist with the team?'],
  ['self', 'Me', 'Yes. I will share the checklist after this call.'],
];
const journal = [
  {id:'ask', category:'ASK', text:'What must be approved before the pilot can launch?', status:'clarify'},
  {id:'incoming', category:'INCOMING_QUESTION', text:'Can you share the launch checklist with the team?', status:'open'},
  {id:'risk', category:'RISK', text:'Access review is still pending. Keep the pilot in the test workspace until it is approved.', status:'open'},
  {id:'decision', category:'DECISION', text:'Alice owns the access review. The team will decide on Friday.', status:'resolved'},
].map(item=>({...item, timestamp:at, source:'transcript', evidence:'Synthetic demonstration conversation.'}));
const meeting = {meeting_id:'demo-pilot', title:'Pilot launch review', started_at:at, duration_seconds:1500,
  transcript_count:conversation.length, journal_count:journal.length, frame_count:0, library_status:'analysis_ready',
  preview:'Access review, pilot scope and next steps.'};
const detail = {...meeting, status:'finished', overview:{points:[
  'Integration is ready for a pilot in the test workspace.',
  'Alice owns the access review. The decision is planned for Friday.',
  'The launch checklist will be shared after the call.'
],questions:['Who approves the access review before launch?']}, transcript:[], journal, frames:[], meeting_chat:[], report:{}};
const payload = {preferences:{interface_language:'en'},
  transcript:{meeting_id:meeting.meeting_id, meeting:meeting.title, status:'recording', live:true, updated_at:at,
    latest_age_seconds:1, started_at:at, speakers:[], segments:conversation.map(([speaker_id,speaker,text],i)=>({
      segment_id:'demo-'+i, speaker_id, speaker, speaker_name:speaker, source:speaker_id==='self'?'microphone':'system',
      timestamp:new Date(Date.parse(at)+i*15000).toISOString(), text
    }))},
  recording_health:{capture:{audio_recording:true}},
  copilot:{messages:[],busy:false,analysis:{state:'signal',at}},
  project:{kind:'repository',name:'launch-demo',repositories:[{name:'launch-demo',path:'demo/launch-demo'}]},
  journal, frames:[], meeting_chat:[]};
const server = http.createServer((req,res)=>{
  const url=new URL(req.url,'http://localhost');
  const json = value => {res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};
  if(req.method!=='GET') return json({ok:true});
  if(url.pathname==='/api/state') return json(payload);
  if(url.pathname==='/api/archive') return json({ok:true,meetings:[meeting,{...meeting,meeting_id:'demo-design',title:'Design handoff',preview:'Navigation and accessibility review.'}]});
  if(url.pathname.startsWith('/api/archive/')) return json({ok:true,meeting:detail});
  if(url.pathname.startsWith('/api/')) return json({ok:true});
  const file=url.pathname==='/'?'index.html':url.pathname.slice(1);
  if(!['index.html','styles.css','app.js','updates.js'].includes(file)){res.writeHead(404);return res.end();}
  res.writeHead(200,{'Content-Type':file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html'});
  fs.createReadStream(path.join(root,file)).pipe(res);
});
server.listen(43991,'127.0.0.1',()=>console.log('Synthetic screenshot fixture: http://127.0.0.1:43991/'));
