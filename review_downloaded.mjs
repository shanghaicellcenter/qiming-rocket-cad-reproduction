// Runtime acceptance against the separately downloaded and verified Release tree.
// Explicit installed runtime paths are required; no original project inputs are used.
import {readFileSync,writeFileSync,mkdirSync,existsSync,realpathSync} from 'node:fs';
import {resolve,relative,isAbsolute,sep} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
const argv=process.argv.slice(2),opt={};for(let i=0;i<argv.length;i+=2)opt[argv[i].replace(/^--/,'')]=argv[i+1];
if(!opt.root||!opt.out||!process.env.MACHINE_PLAYWRIGHT_MODULE||!process.env.MACHINE_CHROMIUM_EXECUTABLE)throw new Error('Need --root --out and explicit installed Playwright/Chromium paths.');
const root=realpathSync(resolve(opt.root)),out=resolve(opt.out),project=resolve(root,'outputs/启明火箭');mkdirSync(out,{recursive:true});
const {chromium}=await import(process.env.MACHINE_PLAYWRIGHT_MODULE);
const browser=await chromium.launch({executablePath:process.env.MACHINE_CHROMIUM_EXECUTABLE,headless:true,args:['--disable-background-networking','--no-first-run','--ignore-gpu-blocklist',...(process.platform==='darwin'?['--use-angle=metal']:[])]});
const report={created_utc:new Date().toISOString(),root,actual_download_tree:true,original_workspace_inputs_used:false,pages:[],passed:false};
const check=(v,m)=>{if(!v)throw new Error(m)};
function localPathState(url){
 if(!url.startsWith('file:'))return null;
 const path=fileURLToPath(new URL(url)),exists=existsSync(path),actual=exists?realpathSync(path):resolve(path),rel=relative(root,actual);
 return {url,path,realPath:actual,exists,inside:rel!== '..'&&!rel.startsWith('..'+sep)&&!isAbsolute(rel)};
}
async function open(relative){
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],external=[],failed=[],outsideRootFileRequests=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('requestfailed',r=>failed.push({url:r.url(),error:r.failure()?.errorText}));
 page.on('request',r=>{const s=localPathState(r.url());if(s&&!s.inside)outsideRootFileRequests.push(s)});
 await page.route(/^https?:\/\//,r=>{external.push(r.request().url());return r.abort()});
 await page.goto(pathToFileURL(resolve(project,relative)).href,{waitUntil:'load',timeout:90000});
 return {page,row:{relative,errors,external,failed,outsideRootFileRequests}};
}
async function decode(page,jobs){
 for(const job of jobs){const s=localPathState(new URL(job.url,page.url()).href);check(s?.exists&&s.inside,'Image is missing or references outside the downloaded root: '+job.url)}
 return page.evaluate(async jobs=>{
 const result=[];for(let i=0;i<jobs.length;i+=12)result.push(...await Promise.all(jobs.slice(i,i+12).map(async job=>{const image=new Image();image.src=job.url;try{await image.decode();return {...job,width:image.naturalWidth,height:image.naturalHeight,passed:image.naturalWidth>0&&image.naturalHeight>0&&(!job.expected||(image.naturalWidth===job.expected[0]&&image.naturalHeight===job.expected[1]))}}catch(e){return {...job,passed:false,error:String(e)}}})));return result;
},jobs)}
async function finish(page,row,shot){
 const links=await page.locator('a[href]').evaluateAll(a=>a.map(x=>x.href));
 row.missingLocalLinks=links.map(localPathState).filter(s=>s&&!s.exists);
 row.outsideRootLocalLinks=links.map(localPathState).filter(s=>s&&!s.inside);
 row.passed=!row.errors.length&&!row.external.length&&!row.failed.length&&!row.missingLocalLinks.length&&!row.outsideRootLocalLinks.length&&!row.outsideRootFileRequests.length;
 if(shot)await page.screenshot({path:resolve(out,shot)});report.pages.push(row);await page.close();check(row.passed,'Page/link/offline failure: '+row.relative);
}
try{
 {
  const {page,row}=await open('打开项目.html');row.title=await page.title();check(row.title.includes('启明火箭'),'Landing title');await finish(page,row,'downloaded-home.png');
 }
 {
  const {page,row}=await open('library/逐件原件预览.html');await page.waitForFunction(()=>window.previewData?.length===170);
  const jobs=await page.evaluate(()=>previewData.flatMap(r=>Object.entries(r.views).map(([view,v])=>({id:r.id,view,url:v.image,expected:r.resolution}))));
  row.images=await decode(page,jobs);check(row.images.length===510&&row.images.every(x=>x.passed),'510 originals decode');
  await page.locator('#kind').selectOption('stl');check(await page.locator('.card').count()===36,'STL source filter');
  await page.locator('#kind').selectOption('');await finish(page,row,'downloaded-original-gallery.png');
 }
 {
  const {page,row}=await open('library/exchange-source/交换格式来源图册.html');const jobs=await page.locator('img').evaluateAll(a=>a.map(x=>({url:x.getAttribute('src')})));
  row.images=await decode(page,jobs);check(row.images.length===109&&row.images.every(x=>x.passed),'105 STEP +4 DXF decode');
  await page.locator('#search').fill('STEP-001');check(await page.locator('#stepgrid .card:not([hidden])').count()===1,'STEP search');await page.locator('#search').fill('');await finish(page,row,'downloaded-exchange-gallery.png');
 }
 {
  const {page,row}=await open('library/source-drawings/原图纸浏览.html');const jobs=await page.locator('img[src]').evaluateAll(a=>a.map(x=>({url:x.getAttribute('src')})));row.images=await decode(page,jobs);check(row.images.length===13&&row.images.every(x=>x.passed),'13 PDF pages decode');await finish(page,row);
 }
 {
  const {page,row}=await open('library/部件说明图册/部件说明图册.html');
  await page.waitForFunction(()=>window.atlasReview?.recordCount===206);
  const data=await page.locator('#atlas-data').evaluate(e=>JSON.parse(e.textContent));check(data.records.length===206,'206 atlas');
  const jobs=data.records.flatMap(r=>r.images.map(i=>({id:r.id,url:i.localPath})));row.images=await decode(page,jobs);check(row.images.every(x=>x.passed)&&jobs.length>=206,'Atlas images decode');
  row.evidence=await page.evaluate(()=>atlasReview);await page.locator('#query').fill('A1-01');check(await page.locator('.card').count()===1,'Atlas exact ID search');
  await page.locator('.pictures img').first().click();check(await page.locator('#lightbox').evaluate(e=>e.open),'Atlas zoom');await page.locator('#large').evaluate(i=>i.decode());await page.screenshot({path:resolve(out,'downloaded-atlas-zoom.png')});await page.locator('#close').click();await page.locator('#query').fill('');
  await page.setViewportSize({width:390,height:844});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Atlas phone overflow');await finish(page,row,'downloaded-atlas-mobile.png');
 }
 {
  const {page,row}=await open('整箭原件检视.html');await page.waitForFunction(()=>document.body.dataset.ready==='true',null,{timeout:90000});
  row.initial=await page.evaluate(()=>assemblyEvidence);check(row.initial.sourceMeshIdentitiesLoaded===688&&row.initial.sourceHiddenMeshObjects===3,'688 source meshes/3 source hidden');
  row.hidden=await page.evaluate(()=>{assemblyReview.setHidden(true);return assemblyEvidence});check(row.hidden.visibleMeshes>row.initial.visibleMeshes,'Show source hidden pieces');
  row.selected=await page.evaluate(()=>{assemblyReview.setHidden(false);const e=assemblyReview.getEntries().find(x=>x.filename?.startsWith('PSTN-2XO238')&&x.kind!=='mesh');if(!e)throw new Error('Piston source missing');assemblyReview.select(e.id,{isolate:true,camera:true});return assemblyEvidence});check(row.selected.isolated&&row.selected.visibleMeshes>0,'Isolate actual source');
  await page.screenshot({path:resolve(out,'downloaded-piston-source.png')});await page.evaluate(()=>assemblyReview.restore());row.restored=await page.evaluate(()=>assemblyEvidence);check(!row.restored.isolated&&row.restored.sourceMeshIdentitiesLoaded===688,'Restore full source');await finish(page,row,'downloaded-main-viewer.png');
 }
 report.total3DViewImagesDecoded=report.pages[1].images.length+report.pages[2].images.filter(x=>x.url.endsWith('.png')).length;
 check(report.total3DViewImagesDecoded===615,'615 complete actual source views');report.passed=true;
}finally{await browser.close();writeFileSync(resolve(out,'downloaded-browser-review.json'),JSON.stringify(report,null,2));}
console.log(JSON.stringify({passed:report.passed,pages:report.pages.length,source3DViews:report.total3DViewImagesDecoded,atlasImages:report.pages.find(x=>x.relative.includes('部件说明图册'))?.images.length}));
