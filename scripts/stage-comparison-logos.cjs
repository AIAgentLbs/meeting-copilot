// Stage verified official identity icons without committing binary media.
const fs=require('node:fs/promises');
const path=require('node:path');
const {createHash}=require('node:crypto');
const {assets}=require('../docs/comparison-logo-assets.json');
const hosts=new Set(['www.meetscribeapp.com','www.granola.ai','fireflies.ai','cdn.prod.website-files.com','tldv.io']);
async function main(){
 const output=path.resolve(process.argv[2]||'_site/media/logos');
 await fs.mkdir(output,{recursive:true});
 for(const asset of assets){
  if(!/^[a-z]+\.png$/.test(asset.file)||!/^[a-f0-9]{64}$/.test(asset.sha256))throw Error('Invalid logo manifest');
  const url=new URL(asset.url);
  if(url.protocol!=='https:'||!hosts.has(url.hostname))throw Error('Unexpected logo host');
  const r=await fetch(url,{signal:AbortSignal.timeout(30000)});
  if(!r.ok)throw Error(`${asset.id}: HTTP ${r.status}`);
  const bytes=Buffer.from(await r.arrayBuffer());
  if(bytes.length>500000||bytes.subarray(0,8).toString('hex')!=='89504e470d0a1a0a')throw Error('Invalid logo image');
  if(createHash('sha256').update(bytes).digest('hex')!==asset.sha256)throw Error(`${asset.id}: checksum mismatch`);
  await fs.writeFile(path.join(output,asset.file),bytes);
  console.log(`Verified ${asset.id}: ${bytes.length} bytes`);
 }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
