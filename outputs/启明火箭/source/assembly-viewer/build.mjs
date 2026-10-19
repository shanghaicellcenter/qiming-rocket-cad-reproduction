import {existsSync,readFileSync,writeFileSync,createReadStream,createWriteStream} from 'node:fs';
import {once} from 'node:events';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';

const here=dirname(fileURLToPath(import.meta.url));
if(Number(process.versions.node.split('.')[0])<18)throw new Error('Node.js 18 or newer is required.');
const require=createRequire(import.meta.url);
const prep=spawnSync('python3',[resolve(here,'prepare_data.py')],{encoding:'utf8'});
if(prep.status!==0)throw new Error(prep.stderr||prep.stdout);
const {PUBLIC_PROJECT_NAME}=await import(pathToFileURL(resolve(here,'source/public-project.js')));
const config=JSON.parse(readFileSync(resolve(here,'assets.json'),'utf8'));
const assets=[...(config.models||[]),...(config.library||[])];
const missing=assets.filter(x=>!existsSync(resolve(here,x.path)));
if(missing.length)throw new Error('Missing original geometry: '+missing.map(x=>x.path).join(', '));
if(!assets.length)throw new Error('No real GLB input is present. No placeholder geometry is generated.');
const runtime=process.env.MACHINE_NODE_MODULES?resolve(process.env.MACHINE_NODE_MODULES):null;
const esbuildEntry=runtime?resolve(runtime,'esbuild/lib/main.js'):require.resolve('esbuild');
const esbuild=await import(pathToFileURL(esbuildEntry));
const three=runtime?resolve(runtime,'three'):resolve(dirname(require.resolve('three')),'..');
const threeVersion=JSON.parse(readFileSync(resolve(three,'package.json'),'utf8')).version;
if(threeVersion!=='0.170.0'||esbuild.version!=='0.27.7')throw new Error('Rebuild versions must be three 0.170.0 and esbuild 0.27.7.');
const notices='/*! Machine Skill / Air Supply Technologies Inc. (Airsup)\n'+readFileSync(resolve(here,'../vendor/machine/LICENSE'),'utf8')+'\nThree.js\n'+readFileSync(resolve(here,'../vendor/machine/THREE-LICENSE.txt'),'utf8')+'\nSource CAD: Half Cat Rocketry; GPL-3.0-or-later with source attribution terms. See ../../LICENSE-Half-Cat.txt. */';
const built=await esbuild.build({entryPoints:[resolve(here,'source/viewer.js')],bundle:true,write:false,format:'iife',target:'es2022',minify:true,banner:{js:notices},alias:{'three/addons':resolve(three,'examples/jsm'),three:resolve(three,'build/three.module.js')},legalComments:'inline'});
const dev=process.argv.includes('--dev');
const outputFlag=process.argv.indexOf('--output');
if(outputFlag>=0&&!process.argv[outputFlag+1])throw new Error('--output requires a destination path.');
const output=resolve(here,outputFlag>=0?process.argv[outputFlag+1]:dev?'viewer-dev.html':'../../整箭原件检视-rebuilt.html');
const report={node:process.versions.node,three:threeVersion,esbuild:esbuild.version,
  metadata_preparation_executed:true,asset_count:assets.length,
  assets:assets.map(a=>({id:a.id,path:a.path})),esbuild_write:false,
  bundle_bytes:built.outputFiles[0].contents.length,
  bundle_sha256:createHash('sha256').update(built.outputFiles[0].contents).digest('hex'),
  mode:process.argv.includes('--validate')?'validate-only':dev?'development':'embedded-single-html',
  planned_output:output,html_written:false,
  conversion_scope:'Original CAD curves were tessellated upstream. This build packages existing visual geometry; it does not solve native mates or physical reliability.'};
if(process.argv.includes('--validate')){
  writeFileSync(resolve(here,'rebuild-validation.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
  process.exit(0);
}
const stream=createWriteStream(output);
async function write(s){if(!stream.write(s))await once(stream,'drain');}
await write('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><link rel="icon" href="data:,"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+PUBLIC_PROJECT_NAME+' · 源装配检视</title><meta name="description" content="'+PUBLIC_PROJECT_NAME+'原始CAD装配转换的中文检视页，包含源层级、实例身份和离线模型。"></head><body><div id="loading" role="status" aria-live="polite" style="position:fixed;inset:0;background:#f3f2ee;z-index:99;display:grid;place-items:center;font:14px system-ui"><div>正在读取源装配…<small id="loading-detail" style="display:block;margin-top:14px;color:#888">模型直接包含在此文件中</small></div></div>');
for(const asset of dev?[]:assets){
  await write(`<script id="model-${asset.id}" type="application/octet-stream">`);
  let carry=Buffer.alloc(0);
  for await(const chunk of createReadStream(resolve(here,asset.path),{highWaterMark:3*1024*1024})){
    const buf=carry.length?Buffer.concat([carry,chunk]):chunk;
    const end=buf.length-buf.length%3;
    await write(buf.subarray(0,end).toString('base64'));
    carry=buf.subarray(end);
  }
  if(carry.length)await write(carry.toString('base64'));
  await write('</script>');
}
await write('<script>'+built.outputFiles[0].text.replace(/<\/script/gi,'<\\/script')+'</script></body></html>');
stream.end();await once(stream,'finish');
report.html_written=true;writeFileSync(resolve(here,'rebuild-validation.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({html:output,asset_count:assets.length,offline:true}));
