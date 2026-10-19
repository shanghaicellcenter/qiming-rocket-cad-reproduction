import {readFileSync,createReadStream,createWriteStream,existsSync} from 'node:fs';
import {once} from 'node:events';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../..');
const candidates=[process.env.MACHINE_NODE_MODULES,resolve(here,'node_modules'),resolve(here,'../node_modules')].filter(Boolean),runtime=candidates.find(p=>existsSync(resolve(p,'esbuild/lib/main.js'))&&existsSync(resolve(p,'three/build/three.module.js')));
if(!runtime)throw new Error('Install the pinned package dependencies here, or set MACHINE_NODE_MODULES.');
const esbuild=await import(pathToFileURL(resolve(runtime,'esbuild/lib/main.js'))),three=resolve(runtime,'three');
const built=await esbuild.build({entryPoints:[resolve(here,'source/film.js')],bundle:true,write:false,format:'iife',target:'es2022',minify:true,alias:{'three/addons':resolve(three,'examples/jsm'),three:resolve(three,'build/three.module.js')},legalComments:'inline'});
const out=resolve(root,'逐步虚拟归位.html'),s=createWriteStream(out+'.tmp');async function w(t){if(!s.write(t))await once(s,'drain');}
await w('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><link rel="icon" href="data:,"><meta name="viewport" content="width=device-width,initial-scale=1"><title>启明火箭 · 十五组逐步虚拟归位</title><body>');
await w('<script id="narration-audio" type="application/octet-stream">data:audio/mpeg;base64,'+readFileSync(resolve(root,'media/逐步虚拟归位旁白.mp3')).toString('base64')+'</script>');
await w('<script id="overview-image" type="application/octet-stream">data:image/png;base64,'+readFileSync(resolve(root,'library/assembly-previews/A12-side.png')).toString('base64')+'</script><script id="model-browse" type="application/octet-stream">');
let carry=Buffer.alloc(0);for await(const chunk of createReadStream(resolve(root,'assembly/vehicle-browse.compact.glb'),{highWaterMark:3145728})){const b=carry.length?Buffer.concat([carry,chunk]):chunk,e=b.length-b.length%3;await w(b.subarray(0,e).toString('base64'));carry=b.subarray(e);}if(carry.length)await w(carry.toString('base64'));
await w('</script><script>'+built.outputFiles[0].text.replace(/<\/script/gi,'<\\/script')+'</script></body></html>');s.end();await once(s,'finish');
const {renameSync}=await import('node:fs');renameSync(out+'.tmp',out);console.log(out);
