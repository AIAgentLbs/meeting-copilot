// Media stays outside Git. Download pinned release assets into the Pages artifact.
const fs = require('node:fs/promises');
const path = require('node:path');
const {createHash} = require('node:crypto');
const manifest = require('../docs/screenshot-assets.json');
async function main() {
  const output = path.resolve(process.argv[2] || '_site/media');
  await fs.mkdir(output, {recursive:true});
  for (const asset of manifest.assets) {
    if (!/^[a-z0-9-]+\.jpg$/.test(asset.file) || !/^[a-f0-9]{64}$/.test(asset.sha256)) throw Error('Invalid screenshot manifest');
    if (!asset.url.startsWith('https://github.com/AIAgentLbs/meeting-copilot/releases/download/')) throw Error('Unexpected asset host');
    const response = await fetch(asset.url, {signal:AbortSignal.timeout(60000)});
    if (!response.ok) throw Error(`Screenshot ${asset.file}: HTTP ${response.status}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    if (bytes.length > 2_000_000 || bytes[0] !== 0xff || bytes[1] !== 0xd8) throw Error('Invalid screenshot image');
    if (createHash('sha256').update(bytes).digest('hex') !== asset.sha256) throw Error(`Screenshot checksum mismatch: ${asset.file}`);
    await fs.writeFile(path.join(output, asset.file), bytes);
    console.log(`Verified ${asset.file}: ${bytes.length} bytes`);
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
