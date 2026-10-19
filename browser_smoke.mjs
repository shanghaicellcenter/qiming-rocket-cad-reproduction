import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const opts=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,all)=>i%2===0?[...a,[v.replace(/^--/,''),all[i+1]]]:a,[]));
if(!opts.silent||!opts.complete||!opts.out)throw new Error('--silent --complete --out paths are required');
if(!process.env.MACHINE_PLAYWRIGHT_MODULE||!process.env.MACHINE_CHROMIUM_EXECUTABLE)throw new Error('Explicit installed Playwright module URL and Chromium executable required. No original workspace fallback.');
const pw=await import(process.env.MACHINE_PLAYWRIGHT_MODULE),out=resolve(opts.out);mkdirSync(out,{recursive:true});
const browser=await pw.chromium.launch({executablePath:process.env.MACHINE_CHROMIUM_EXECUTABLE,headless:true,args:['--ignore-gpu-blocklist','--enable-gpu-rasterization',...(process.platform==='darwin'?['--use-angle=metal']:[])]});
const rows=[];
try{
 for(const kind of ['silent','complete']){
  const page=await browser.newPage({viewport:{width:1280,height:720}}),errors=[],external=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.route(/^https?:\/\//,route=>{external.push(route.request().url());return route.abort();});
  await page.goto(pathToFileURL(resolve(opts[kind])).href,{waitUntil:'load',timeout:60000});
  await page.waitForFunction(()=>document.body.dataset.ready==='true',{timeout:60000});
  const initial=await page.evaluate(()=>({evidence:window.assemblyFilmEvidence,audio:window.assemblyFilm.audioState()}));
  if(Boolean(initial.audio)!==(kind==='complete'))throw new Error('Unexpected audio presence: '+kind);
  if(kind==='complete')await page.waitForFunction(()=>window.assemblyFilm.audioState().duration>200);
  await page.locator('#play').click();await page.waitForTimeout(500);
  const playing=await page.evaluate(()=>({evidence:window.assemblyFilmEvidence,audio:window.assemblyFilm.audioState()}));
  if(!(playing.evidence.currentTime>0))throw new Error('Clock did not advance: '+kind);
  await page.locator('#play').click();
  await page.evaluate(()=>{const t=window.assemblyFilm.timeline.clips[10].end-1;window.assemblyFilm.seek(t);});
  await page.waitForTimeout(200);
  const sought=await page.evaluate(()=>({evidence:window.assemblyFilmEvidence,audio:window.assemblyFilm.audioState()}));
  await page.screenshot({path:resolve(out,kind+'-stage10.png')});
  await page.locator('#stage').selectOption('15');await page.waitForTimeout(100);
  const chapter=await page.evaluate(()=>({stage:window.assemblyFilmEvidence.stage,time:window.assemblyFilmEvidence.currentTime}));
  if(chapter.stage!==15||external.length||errors.length)throw new Error(JSON.stringify({kind,chapter,external,errors}));
  rows.push({kind,initial,playing,sought,chapter,errors,external,passed:true});await page.close();
 }
}finally{await browser.close();}
writeFileSync(resolve(out,'browser-smoke.json'),JSON.stringify({actual_file_protocol:true,installed_runtime_explicitly_supplied:true,silent_and_complete_actual_play_seek_chapter_passed:true,downloaded_assets_test_claimed:false,rows},null,2));
console.log(JSON.stringify({passed:rows.length===2,rows:rows.map(r=>({kind:r.kind,clockAdvanced:r.playing.evidence.currentTime,chapter:r.chapter.stage,errors:r.errors.length,external:r.external.length}))}));
