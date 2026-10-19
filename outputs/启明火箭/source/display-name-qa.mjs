import {launch} from './vendor/machine/scripts/lib/browser.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'research/display-name-review');fs.mkdirSync(out,{recursive:true});
const {browser,page}=await launch({width:1440,height:1000});
const errors=[],external=[],checks=[],screenshots=[];
page.on('pageerror',e=>errors.push(String(e)));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
page.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url());});
await page.route(/^https?:/,r=>r.abort());
const old=/Mojave[\s_-]*Sphinx|MojaveSphinx|\bSphinx\b|斯芬克斯|莫哈韦|莫哈维/i;
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const assert=(v,m)=>{if(!v)throw new Error(m);};
const go=async relative=>{await page.goto(pathToFileURL(path.join(root,relative)).href,{waitUntil:'load'});};
const shot=async name=>{const p=path.join(out,name+'.png');await page.screenshot({path:p});screenshots.push({file:path.relative(root,p),sha256:sha(p)});};
const progress=()=>fs.writeFileSync(path.join(out,'qa-progress.json'),JSON.stringify({updated_at_utc:new Date().toISOString(),status:'running',checks,external,errors,screenshots},null,2)+'\n');
const check=async(name,fn)=>{const detail=await fn();checks.push({name,passed:true,detail});progress();console.log('PASS',name);};
const visibleNameCheck=async()=>{const title=await page.title(),text=await page.locator('body').innerText();assert(title.includes('启明火箭'),'Chinese browser title absent');assert(!old.test(text),'Old source project name leaked into rendered body');return {title,body_old_name_matches:0};};
const linkCheck=async()=>{const links=await page.locator('a[href]').evaluateAll(a=>a.map(x=>x.href));const local=links.filter(x=>x.startsWith('file:'));for(const u of local){const q=new URL(u);q.hash='';assert(fs.existsSync(fileURLToPath(q)),'Missing local link '+u);}return {local_links:local.length,all_local_targets_exist:true};};
const imageReady=async selector=>{await page.locator(selector).evaluateAll(async imgs=>{await Promise.all(imgs.map(async im=>{im.loading='eager';await Promise.race([im.decode(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Image decode timeout: '+im.src)),15000))]);}));});return await page.locator(selector).evaluateAll(imgs=>imgs.map(im=>({src:im.getAttribute('src'),width:im.naturalWidth,height:im.naturalHeight})));};
let report;
try{
await go('打开项目.html');
await check('rebuilt landing is actual Chinese HTML',async()=>{const n=await visibleNameCheck();const ims=await imageReady('img');assert(ims.length===2&&ims.every(x=>x.width>0),'Landing image missing');return {...n,images:ims,links:await linkCheck()};});
await shot('landing-desktop');
await page.setViewportSize({width:390,height:844});await page.reload({waitUntil:'load'});
await check('landing phone display',async()=>{const d=await visibleNameCheck();const w=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));assert(w.document<=w.viewport+1,'Landing horizontal overflow');return {...d,...w};});
await shot('landing-phone');
await page.setViewportSize({width:1440,height:1000});
await go('library/逐件原件预览.html');
await check('gallery displays all 170 aliases without altering source metadata',async()=>{const d=await visibleNameCheck();const e=await page.evaluate(()=>window.previewEvidence);assert(e.sourceRecords===170&&e.allImages===510,'Gallery count changed');const rows=await page.locator('.filename').allTextContents();assert(rows.length===170&&!rows.some(n=>old.test(n)),'Unfiltered filename');const identities=await page.evaluate(()=>({count:window.previewData.length,original_identity_retained:window.previewData.some(r=>/Mojave.*Sphinx/i.test(r.name))}));assert(identities.original_identity_retained,'Exact source metadata was removed');return {...d,evidence:e,identities,rendered_filename_aliases:rows.length};});
await imageReady('.picture img');await shot('gallery-desktop');
await check('all 510 gallery source-view images decode in isolated browser',async()=>{const results=await page.evaluate(async()=>{const urls=window.previewData.flatMap(r=>Object.values(r.views).map(v=>v.image));const rows=[];for(let start=0;start<urls.length;start+=8){rows.push(...await Promise.all(urls.slice(start,start+8).map(async src=>{const im=new Image();im.src=src;await im.decode();return {src,width:im.naturalWidth,height:im.naturalHeight};})));}return rows;});assert(results.length===510&&results.every(r=>r.width>0&&r.height>0),'Source-view image decode failure');return {decoded:results.length,unique_images:new Set(results.map(r=>r.src)).size,all_nonempty:true};});
await page.locator('#search').fill('启明火箭');
await check('Chinese display-name search finds original source records',async()=>{const n=await page.locator('.card').count();assert(n>0,'New name search empty');return {matching_cards:n};});
await page.locator('#search').fill('');
for(const id of ['P001','RAW01','A12','A15']){
 await page.locator(`[data-card="${id}"] .picture`).click();
 await check(`gallery modal ${id} uses Chinese filename alias and valid views`,async()=>{assert(await page.locator('dialog').isVisible(),'Modal did not open');const text=await page.locator('dialog').innerText();assert(!old.test(text),'Raw source name leaked into modal');const views=[];for(const view of ['front','side','oblique']){await page.locator(`.modal-views [data-view="${view}"]`).click();views.push({view,...(await imageReady('dialog img'))[0]});}return {display_filename:await page.locator('dialog code').innerText(),views};});
 if(id!=='RAW01')await shot('gallery-modal-'+id);
 await page.locator('#close').click();
}
await page.setViewportSize({width:430,height:900});await page.reload({waitUntil:'load'});
await check('gallery phone names and layout',async()=>{const n=await visibleNameCheck();const w=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));assert(w.document<=w.viewport+1,'Gallery horizontal overflow');return {...n,...w};});
await shot('gallery-phone');
await page.setViewportSize({width:1440,height:1000});await go('library/source-drawings/原图纸浏览.html');
await check('drawing gallery title and all thirteen image files',async()=>{const d=await visibleNameCheck(),images=await imageReady('.page-card img');assert(images.length===13&&images.every(im=>im.width===1600&&im.height===1131),'Drawing page image missing');return {...d,images,links:await linkCheck()};});
await page.locator('[data-page="0"]').click();
const pages=[];
for(let i=1;i<=13;i++){
 const image=(await imageReady('#large'))[0];const current=await page.evaluate(()=>window.sourceDrawingsReview.currentPage);const label=await page.locator('#page-title').innerText();assert(current===i&&label.includes(`第${i} / 13页`),'Drawing page mismatch');assert(image.width===1600&&image.height===1131,'Drawing image not decoded');pages.push({physical_page:i,label,image});
 if([1,7,13].includes(i))await shot('drawing-page-'+String(i).padStart(2,'0'));
 if(i<13)await page.keyboard.press('ArrowRight');
}
checks.push({name:'all thirteen renamed drawing display pages reachable and decoded in actual modal',passed:true,detail:pages});
await page.keyboard.press('Escape');await page.setViewportSize({width:390,height:844});await page.reload({waitUntil:'load'});await page.locator('[data-page="0"]').click();await imageReady('#large');
await check('drawing phone modal and Chinese display',async()=>{const n=await visibleNameCheck();const r=await page.locator('#large').boundingBox(),v=await page.evaluate(()=>({w:innerWidth,h:innerHeight}));assert(r.x>=0&&r.y>=0&&r.x+r.width<=v.w+1&&r.y+r.height<=v.h+1,'Drawing image not fitted to phone modal');return {...n,image_box:r,viewport:v};});
await shot('drawing-phone');
assert(!errors.length,'Browser JavaScript errors');assert(!external.length,'Unexpected network request');
report={tested_at_utc:new Date().toISOString(),browser:browser.version(),mode:'isolated headless Chrome, launched through existing Machine browser runtime; no existing user profile or foreground window',checks,passed:checks.every(c=>c.passed),external_requests:external,javascript_errors:errors,screenshots,source_counts_unchanged:{records:170,three_view_images:510,drawing_pages_separate:13},htmls:['打开项目.html','library/逐件原件预览.html','library/source-drawings/原图纸浏览.html'].map(p=>({path:p,sha256:sha(path.join(root,p))}))};
fs.writeFileSync(path.join(out,'qa.json'),JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(path.join(out,'qa-progress.json'),JSON.stringify({updated_at_utc:new Date().toISOString(),status:'complete',passed:true,checks:checks.length,final_report:'qa.json'},null,2)+'\n');
console.log(JSON.stringify({passed:report.passed,checks:checks.length,external:external.length,errors:errors.length,screenshots:screenshots.length}));
}catch(e){fs.writeFileSync(path.join(out,'qa-failure.json'),JSON.stringify({error:String(e),checks,external,errors,screenshots},null,2));throw e;}finally{await browser.close();}
