/*
 * A read-only view of the user-supplied CAD conversion, not a generated design.
 * The only model inputs are embedded GLBs. Source hierarchy and local transforms
 * remain in their original nodes. Presentation has a separate parent translation;
 * the Machine set applies one uniform display scale. CAD curves are tessellated,
 * so this is not a mathematically lossless CAD or mate/flight validation.
 * No geometry is invented, repaired, decimated, or replaced by this viewer.
 */
import {THREE,Lab,mat,setCaps,ease} from '../../vendor/machine/kit/lab-kit.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {ASSETS,SOURCE,SOURCE_NODES,SOURCE_PRIMS,PROVIDERS,LABELS,PATCH_LABELS,LIBRARY_ENTRIES,SOURCE_CATALOG} from './data.js';
import css from './styles.js';
import {PUBLIC_PROJECT_NAME} from './public-project.js';

const q=new URLSearchParams(location.search), reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const style=document.createElement('style');style.textContent=css;document.head.append(style);
document.documentElement.lang='zh-CN';
// The public name is a display alias. Source identities and API matching keep
// the original strings; HTML data-entry/option values use identityEsc below.
const publicName=s=>String(s??'')
  .replace(/mojave(?:[\s_-]*sphinx)?|sphinx/gi,PUBLIC_PROJECT_NAME)
  .replace(/(?:莫哈[韦維维][\s·・_-]*)?(?:斯[芬菲]克[斯思]|狮身人面像|獅身人面像)/g,PUBLIC_PROJECT_NAME)
  .replace(/莫哈[韦維维](?:火箭)?/g,PUBLIC_PROJECT_NAME);
const identityEsc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const esc=s=>identityEsc(publicName(s));
const setPublicText=(element,text)=>{element.textContent=publicName(text);};
const fmt=n=>Number(n||0).toLocaleString('en-US');
const loader=new GLTFLoader();
const sourceNodeByPath=new Map(SOURCE_NODES.map(x=>[x.prim_path,x]));
const sourcePrimByPath=new Map(SOURCE_PRIMS.map(x=>[x.path,x]));
const labelValues=new Set(Object.values(LABELS).map(x=>x.category));
const fullAssets=ASSETS.filter(a=>a.kind==='assembly'), libraryAssets=ASSETS.filter(a=>a.kind==='library');
let active=null, sourceRoot=null, presentation=null, meshes=[], entries=[], byId=new Map(), children=new Map(), topEntries=[];
let selected=null, isolated=false, showHidden=false, wire=false, showMeshes=false, pendingLoad=false, loadToken=0;
let modelSize=2.5, wholeBox=new THREE.Box3(), defaultView=null, frameCounter=0, frameAt=performance.now(), fps=0;
let expanded=new Set(), explodeTargets=[], lastExplode=-1, lastXray=-1, materialCache=new Map(), selectedMaterials=[];
let shadowDirty=true, modelStarted=false, sourceVisibilityCount=0, loadedSourceNodeCount=0;
let activeSupplement=null, lastAssemblyId=(fullAssets.find(a=>a.id==='browse')??fullAssets[0])?.id;
const labelFor=name=>LABELS[name]??PATCH_LABELS.find(x=>x.source_basename===name)??(name?.startsWith('BRKT-EGSE')?{label_zh:'地面设备安装支架',category:'连接件'}:name?.startsWith('CVR-ANT')?{label_zh:'地面设备接收天线罩',category:'辅助工具'}:undefined);
const libraryLabel=r=>labelFor(r.source_cad_filename??r.source_filename)?.label_zh??r.label_zh??r.source_filename;
const instanceLabel=(base,sourceDisplayName)=>{const match=sourceDisplayName?.match(/-(\d+)$/);return match?base+' · '+match[1]:base;};

setCaps('metal');
const lab=new Lab({prompt:PUBLIC_PROJECT_NAME+' · 从原始 CAD 装配进入每一个源节点',title:PUBLIC_PROJECT_NAME,sub:'源装配 · 中文检视',no:1,size:2.5,
  view:{az:28,el:12,dist:2.05,target:[0,1.1,0],frameX:0,fov:30},autoOrbit:false,
  cut:{a:[0,0,1],b:[0,0,1],center:[0,1.1,0],reach:.6},pills:['原CAD转换','原层级','完全离线']});
document.head.append(style); // Keep local layout rules after the kit's injected base stylesheet.
window.lab=lab;
lab.ao.enabled=false;lab.bloom.enabled=false;
lab.composer.renderTarget1.samples=0;lab.composer.renderTarget2.samples=0;
lab.renderer.setPixelRatio(lab.filmMode?Number(q.get('ss')||1):Math.min(devicePixelRatio,1.25));
lab.renderer.shadowMap.enabled=false;
lab.controlsOrbit.minDistance=.004;lab.controlsOrbit.maxDistance=35;lab.controlsOrbit.maxPolarAngle=Math.PI*.98;
lab.camera.far=100;lab.camera.updateProjectionMatrix();lab._resize();
lab.grade.uniforms.uGrain.value=.0025;
lab.sparks.update=()=>{};
const contactUpdate=lab._contact.update.bind(lab._contact);
lab._contact.update=function(){
  const separated=lab.state.explode>.004;
  this.plane.visible=!separated;
  if(shadowDirty&&!separated){contactUpdate();shadowDirty=false;}
};
lab._updateXray=()=>{};
setPublicText(lab.$('.lab-no'),'HALF CAT ROCKETRY / R01 · 源装配');
setPublicText(lab.$('.lab-how summary'),'来源、单位与检视范围');
lab.how('主装配的原始 SolidWorks 文件先转换为 USD，再导出 GLB。独立库亦含原 STL；单位未声明时会单独提示。本页直接读取这些文件的几何、层级和实例位置。曲面已三角化；精细级与浏览级来自同一来源的不同三角化级别。<br><br>源单位为 0.0254 米/单位；GLB 使用米。页面只整体居中并统一缩放显示；展示分开、透视和剖切均为检视状态。原生配合约束、制造适用性与飞行能力没有因此得到验证。',[
  '源节点、源文件、源网格、三角面与装配实例是不同计数。多材质源网格会拆为多个渲染网格。',
  '125/133 个源文件的名称对照，不等于部件完整率。',
  '原作隐藏件默认保持隐藏；目录可选中检视。'
]);

const dock=document.createElement('aside');dock.className='dock';dock.setAttribute('aria-label','源装配层级目录');
dock.innerHTML=`<div class="dock-head"><b>源装配目录</b><span id="directory-total"></span><button id="close-tree" aria-label="收起目录">−</button></div><div class="dock-tools"><input id="search" type="search" placeholder="搜索中文、显示名或源路径" aria-label="搜索源节点"><div class="filter-row"><select id="category" aria-label="筛选类别"><option value="">所有类别</option>${[...labelValues].map(x=>`<option value="${identityEsc(x)}">${esc(x)}</option>`).join('')}</select><select id="library" aria-label="选择源装配或独立原件"><option value="">原整箭装配</option>${LIBRARY_ENTRIES.map(r=>`<option value="${identityEsc(r.asset_id+':'+r.supplement_id)}">${esc(r.supplement_id+' · '+libraryLabel(r))}</option>`).join('')}</select></div><div class="dock-checks"><label><input type="checkbox" id="source-hidden">显示源隐藏件</label><label><input type="checkbox" id="show-meshes">显示网格节点</label></div></div><div class="tree-status" aria-live="polite">正在读取实际层级…</div><div class="tree" role="tree" aria-label="原CAD节点与网格"></div>`;
document.body.append(dock);
const panelTab=document.createElement('button');panelTab.className='panel-tab';setPublicText(panelTab,'打开源目录');panelTab.hidden=true;document.body.append(panelTab);
function setDock(open){dock.hidden=!open;panelTab.hidden=open;document.body.dataset.treeOpen=String(open);}
dock.querySelector('#close-tree').onclick=()=>setDock(false);panelTab.onclick=()=>setDock(true);
if(innerWidth<=820)setDock(false);

const tools=document.createElement('nav');tools.className='tools';tools.setAttribute('aria-label','检视工具');
tools.innerHTML=`<button id="whole">整箭</button><button id="focus">放大选中</button><button id="solo">隔离查看</button><select id="quality" aria-label="选择三角化级别">${fullAssets.map(a=>`<option value="${esc(a.id)}">${esc(a.label)}</option>`).join('')}</select>`;document.body.append(tools);
const help=document.createElement('div');help.className='help-line';setPublicText(help,'拖动旋转 · 滚轮缩放 · 单击选中 · 双击隔离 · Esc 返回整箭');document.body.append(help);
const scope=document.createElement('div');scope.className='scope-note';document.body.append(scope);
const inspector=document.createElement('section');inspector.className='inspector on';inspector.setAttribute('aria-label','选中节点来源');lab.$('.lab-side').append(inspector);
const modeNote=document.createElement('div');modeNote.className='mode-note';lab.$('.lab-side').append(modeNote);
const sourceButton=document.createElement('button');sourceButton.className='source-button';setPublicText(sourceButton,'查看来源与文件覆盖');lab.$('.lab-side').append(sourceButton);
const cutControl=document.createElement('div');cutControl.className='cut-control';cutControl.innerHTML='展示剖切位置<input id="cut-position" aria-label="展示剖切位置" type="range" min="0" max="100" value="50">';lab.$('.lab-side').append(cutControl);
const spread=lab.slider({id:'spread',label:'展示分开',min:0,max:100,value:0,unit:'%',ends:['原始相对位置','仅展示偏移'],onInput:v=>{lab.target.explode=v/100;}});
const dialog=document.createElement('dialog');dialog.setAttribute('aria-label','来源与覆盖说明');dialog.innerHTML=`<div class="dialog-head"><h2>从原文件，到当前检视。</h2><button aria-label="关闭来源说明">×</button></div><div class="dialog-body"></div>`;document.body.append(dialog);dialog.querySelector('button').onclick=()=>dialog.close();sourceButton.onclick=()=>{fillSourceDialog();dialog.showModal();};

const names={cut:'展示剖切',xray:'外壳透视',explode:'展示分开',wire:'网格',reset:'复位'};
lab._modes=function(){const host=this.$('.lab-modes');host.innerHTML=[['cut','C'],['xray','X'],['explode','E'],['wire','W'],['reset','0']].map(([k,key])=>`<button data-k="${k}">${names[k]}<kbd>${key}</kbd></button>`).join('');host.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;activateMode(b.dataset.k);});};
lab._syncButtons=function(){for(const b of this.$('.lab-modes').querySelectorAll('button')){const on=b.dataset.k==='wire'?wire:b.dataset.k==='reset'?false:this.target[b.dataset.k]>.5;b.classList.toggle('act',on);b.setAttribute('aria-pressed',String(on));b.disabled=(active?.kind==='library'&&b.dataset.k==='explode')||(b.dataset.k==='xray'&&!meshes.some(m=>m.userData.isPresentationShell));}};
function activateMode(key){if(key==='reset'){reset();return;}if(key==='wire'){wire=!wire;updateMaterials();lab._syncButtons();return;}lab.toggle(key);cutControl.classList.toggle('on',lab.target.cut>.5);shadowDirty=true;}

function canonicalPath(raw){if(active?.kind!=='assembly'||!raw)return raw;const at=raw.indexOf('/Default');if(at>=0)return '/vehicle/vehicle'+raw.slice(at);if(raw.startsWith('/tn__vehiclebrowse_')){const parts=raw.split('/').filter(Boolean);return parts.length>=2?'/vehicle/vehicle'+(parts.length>2?'/'+parts.slice(2).join('/'):''):'/vehicle';}return raw;}
function rawSourcePath(object){for(let o=object;o;o=o.parent){if(o.userData?.source_usd_path)return o.userData.source_usd_path;}return '';}
function sourcePath(object){for(let o=object;o;o=o.parent){if(o.userData?.source_usd_canonical_path)return o.userData.source_usd_canonical_path;if(o.userData?.source_usd_path)return canonicalPath(o.userData.source_usd_path);}return '';}
function sourceHidden(object){for(let o=object;o;o=o.parent){const p=o.userData?.source_usd_canonical_path??canonicalPath(o.userData?.source_usd_path);const v=o.userData?.source_usd_visibility??sourcePrimByPath.get(p)?.visible;if(v==='invisible'||o.userData?.source_hidden===true)return true;}return false;}
function nativeFilename(object){for(let o=object;o;o=o.parent){if(o.userData?.source_cad_filename||o.userData?.source_filename)return o.userData.source_cad_filename??o.userData.source_filename;const info=sourceNodeByPath.get(o.userData?.source_usd_canonical_path??canonicalPath(o.userData?.source_usd_path));if(info?.source_filename_candidates?.length===1)return info.source_filename_candidates[0];}return null;}
function meshProviders(mesh){return mesh.userData.point_attribute_provider_path?[{property_path:mesh.userData.point_attribute_provider_path}]:(PROVIDERS[mesh.userData.sourcePath]?.point_attribute_providers??[]);}
function createMaterial(original,isShell){const key=original.uuid+':'+(isShell?'shell':'inner');if(materialCache.has(key))return materialCache.get(key);const m=mat({color:original.color?.toArray()??[.62,.63,.61],metalness:original.metalness??0,roughness:original.roughness??.5,transparent:original.transparent,opacity:original.opacity,side:original.side,alphaTest:original.alphaTest,vertexColors:original.vertexColors,map:original.map??null,normalMap:original.normalMap??null,roughnessMap:original.roughnessMap??null,metalnessMap:original.metalnessMap??null,emissive:original.emissive?.toArray()??[0,0,0],emissiveIntensity:original.emissiveIntensity??1,finish:null});m.userData.sourceOpacity=original.opacity??1;m.userData.sourceTransparent=!!original.transparent;m.userData.shell=isShell;materialCache.set(key,m);return m;}
function disposeModel(){for(const m of selectedMaterials)m.dispose();selectedMaterials=[];if(sourceRoot){const geos=new Set();sourceRoot.traverse(o=>{if(o.isMesh)geos.add(o.geometry);});for(const g of geos)g.dispose();}for(const m of materialCache.values())m.dispose();materialCache=new Map();if(presentation)lab.machine.remove(presentation);sourceRoot=presentation=null;meshes=[];entries=[];byId.clear();children.clear();topEntries=[];explodeTargets=[];selected=null;}

function decodeAsset(asset){const text=document.getElementById(asset.asset_id)?.textContent?.trim();if(!text)throw new Error('模型资源没有包含在当前文件：'+asset.id);const raw=atob(text);const buffer=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)buffer[i]=raw.charCodeAt(i);return buffer.buffer;}
function loading(message,detail=''){let el=document.getElementById('loading');if(!el){el=document.createElement('div');el.id='loading';el.className='load-state';document.body.append(el);}el.innerHTML='<div>'+esc(message)+'<small>'+esc(detail)+'</small></div>';return el;}

async function loadAsset(id,{preserveSelection=true,supplementId=null}={}){
  const asset=ASSETS.find(a=>a.id===id);if(!asset)throw new Error('真实模型输入不存在：'+id);
  const token=++loadToken,previousId=preserveSelection?selected?.id:null,previousSolo=preserveSelection&&isolated;
  pendingLoad=true;document.body.dataset.ready='false';loading('正在读取'+asset.label+'…','来自源 CAD 转换，完整几何直接包含在此 HTML 中。');
  await new Promise(r=>setTimeout(r,20));disposeModel();active=asset;
  const gltf=q.has('dev')?await loader.loadAsync(asset.development_uri):await loader.parseAsync(decodeAsset(asset),'');if(token!==loadToken)return;
  sourceRoot=gltf.scene;sourceRoot.name='source_glb_scene';
  lab.root.scale.setScalar(1);
  presentation=new THREE.Group();presentation.name='presentation_centering_only';presentation.userData.presentationOnly=true;presentation.add(sourceRoot);lab.machine.add(presentation);
  sourceRoot.updateWorldMatrix(true,true);const checked=new Set();
  sourceRoot.traverse(o=>{if(!o.isMesh)return;const source=sourcePath(o),filename=nativeFilename(o),category=labelFor(filename)?.category;const shell=category==='箭体'||category==='头锥';o.userData.originalSourceHidden=sourceHidden(o);o.userData.sourcePath=source;o.userData.sourcePathRaw=rawSourcePath(o);o.userData.sourceFilename=filename;o.userData.isPresentationShell=shell;o.castShadow=false;o.receiveShadow=false;o.frustumCulled=true;if(!checked.has(o.geometry)){o.geometry.computeBoundingBox();o.geometry.computeBoundingSphere();checked.add(o.geometry);}const converted=(Array.isArray(o.material)?o.material:[o.material]).map(m=>createMaterial(m,shell));o.material=Array.isArray(o.material)?converted:converted[0];o.userData.baseMaterial=o.material;o.userData.triangles=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;meshes.push(o);});
  if(!meshes.length)throw new Error('GLB 中没有可显示网格；没有生成替代模型。');
  let box=boxForMeshes(meshes.filter(m=>!m.userData.originalSourceHidden));if(box.isEmpty())box=boxForMeshes(meshes);
  const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());modelSize=Math.max(size.x,size.y,size.z);lab.size=modelSize;lab.k=2.4/modelSize;lab.root.scale.setScalar(lab.k);
  presentation.position.set(-center.x,-box.min.y+.012*modelSize,-center.z);presentation.updateWorldMatrix(true,true);
  wholeBox=boxForMeshes(meshes.filter(m=>!m.userData.originalSourceHidden));
  buildEntries();sourceVisibilityCount=meshes.filter(m=>!m.userData.originalSourceHidden).length;
  loadedSourceNodeCount=entries.filter(e=>e.kind!=='mesh'&&(e.objects.length||e.meshes.length)).length;
  prepareExplosion();lastExplode=-1;lastXray=-1;lab.target.explode=lab.state.explode=0;spread.set(0);
  lab.target.cut=lab.state.cut=0;lab.target.xray=lab.state.xray=0;cutControl.classList.remove('on');
  if(asset.kind==='assembly'){lastAssemblyId=asset.id;activeSupplement=null;}
  tools.querySelector('#quality').value=asset.kind==='assembly'?asset.id:lastAssemblyId;tools.querySelector('#quality').disabled=asset.kind==='library';dock.querySelector('#library').value='';
  lab.hero({label:asset.kind==='assembly'?'已读取组件/组节点':'已读取独立源节点',unit:'个',max:Math.max(1,loadedSourceNodeCount)});
  defaultView=viewForBox(wholeBox,{whole:true});lab.setView(defaultView);
  lab.camera.near=Math.max(.00001,defaultView.dist*2.4/250);lab.camera.updateProjectionMatrix();
  if(previousId&&byId.has(previousId)){selected=byId.get(previousId);isolated=previousSolo;}else{selected=null;isolated=false;}
  if(asset.kind==='library'){selectSupplement(supplementId??LIBRARY_ENTRIES.find(r=>r.asset_id===asset.id)?.supplement_id);}
  refreshVisibility();setSelectionHighlight();renderTree();updateInspector();updateEvidence();updateHero();updateScope();setupFilm();
  if(!modelStarted){lab.start();modelStarted=true;}lab._assembly=0;lab._building=false;lab._pc=null;
  pendingLoad=false;shadowDirty=true;lab._syncButtons();document.body.dataset.ready='true';document.getElementById('loading')?.remove();
  if(lab.filmMode){lab._initFilm();window.__film.ready=true;}
}

function boxForMeshes(list){const box=new THREE.Box3();for(const m of list){m.updateWorldMatrix(true,false);box.union(m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld));}return box;}
function entryBox(e){return boxForMeshes((e?.meshes??meshes).filter(m=>m.visible));}
function viewForBox(box,{whole=false,az=28,el=12}={}){if(box.isEmpty())box=wholeBox;const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());const fov=30;const fraction=innerWidth<=820?.68:.78;const radius=size.length()/2;const d=Math.max(radius/Math.sin(THREE.MathUtils.degToRad(fov/2))/fraction,.012);return{az,el,dist:d/2.4,target:center.clone().divideScalar(lab.k).toArray(),frameX:innerWidth<=820?(whole?-.08:-.03):.015,fov};}
function focus(e=selected){const box=entryBox(e);if(box.isEmpty())return;const size=box.getSize(new THREE.Vector3()),span=Math.max(size.x,size.y,size.z);let az=lab.view.az,el=Math.max(8,lab.view.el);if(span>0){if(size.y<span*1e-5)el=45;else if(size.z<span*1e-5){az=0;el=18;}else if(size.x<span*1e-5){az=90;el=18;}}const view=viewForBox(box,{whole:!e,az,el});lab.setView(view);lab.camera.near=Math.max(.000002,view.dist*2.4/250);lab.camera.updateProjectionMatrix();}

function buildEntries(){
  const objectByPath=new Map();sourceRoot.traverse(o=>{const p=o.userData?.source_usd_canonical_path??canonicalPath(o.userData?.source_usd_path);if(p){if(!objectByPath.has(p))objectByPath.set(p,[]);objectByPath.get(p).push(o);}});
  const data=active.kind==='assembly'?SOURCE_NODES:[];
  for(const n of data){const filename=n.source_filename_candidates?.length===1?n.source_filename_candidates[0]:null;const label=labelFor(filename);const objects=objectByPath.get(n.prim_path)||[];const related=meshes.filter(m=>m.userData.sourcePath===n.prim_path||m.userData.sourcePath.startsWith(n.prim_path+'/'));const e={id:'node:'+n.prim_path,path:n.prim_path,rawPath:objects[0]?.userData?.source_usd_path??n.prim_path,kind:n.kind??'group',label:label?.label_zh?instanceLabel(label.label_zh,n.display_name):(n.display_name??n.prim_path.split('/').pop()),sourceDisplayName:n.display_name,filename,category:label?.category??'',objects,meshes:related,parent:null,children:[],originalHidden:related.length>0&&related.every(m=>m.userData.originalSourceHidden)};entries.push(e);byId.set(e.id,e);}
  if(active.kind==='library'){for(const root of sourceRoot.children){const id=root.userData?.supplement_id;if(!id)continue;const filename=nativeFilename(root),l=labelFor(filename),related=meshes.filter(m=>m.userData.supplement_id===id);const e={id:'supplement:'+id,path:root.userData.source_usd_path??root.userData.source_filename,rawPath:root.userData.source_usd_path??root.userData.source_filename,kind:'component',label:l?.label_zh??root.userData.label_zh??root.name,filename,category:l?.category??'',objects:[root],meshes:related,children:[],parent:null,originalHidden:related.length>0&&related.every(m=>m.userData.originalSourceHidden),supplementId:id,identity:root.userData};entries.push(e);byId.set(e.id,e);}}
  const sourceEntries=[...entries];
  for(const e of sourceEntries){if(e.supplementId)continue;let p=e.path.slice(0,e.path.lastIndexOf('/'));while(p&&!byId.has('node:'+p))p=p.slice(0,p.lastIndexOf('/'));e.parent=byId.get('node:'+p)||null;}
  for(let i=0;i<meshes.length;i++){const m=meshes[i],p=m.userData.sourcePath;let owner=active.kind==='library'?byId.get('supplement:'+m.userData.supplement_id):null;for(let o=m;o&&!owner;o=o.parent){const path=o.userData?.source_usd_canonical_path??canonicalPath(o.userData?.source_usd_path);owner=byId.get('node:'+path)||null;}if(!owner){let path=p;while(path&&!owner){owner=byId.get('node:'+path)||null;path=path.slice(0,path.lastIndexOf('/'));}}const filename=m.userData.sourceFilename??owner?.filename??active.source_filename;const label=labelFor(filename);const e={id:'mesh:'+(m.userData.presentation_id??p)+':'+i,path:p,rawPath:m.userData.sourcePathRaw,kind:'mesh',label:'网格 · '+(label?.label_zh??m.userData.source_usd_name??m.name),filename,category:label?.category??owner?.category??'',objects:[m],meshes:[m],parent:owner,children:[],originalHidden:m.userData.originalSourceHidden,meshIndex:i};entries.push(e);byId.set(e.id,e);m.userData.navigationOwner=owner?.id??e.id;m.userData.meshNavigationId=e.id;}
  for(const e of entries){if(e.parent)e.parent.children.push(e);else topEntries.push(e);}
  const getDepth=(e,seen=new Set())=>{if(!e.parent||seen.has(e.id))return 0;seen.add(e.id);return 1+getDepth(e.parent,seen);};for(const e of entries)e.depth=getDepth(e);
  expanded=new Set(entries.filter(e=>e.kind!=='mesh'&&e.depth<3).map(e=>e.id));
  setPublicText(dock.querySelector('#directory-total'),fmt(entries.filter(e=>e.kind!=='mesh').length)+' 源节点');
}

function selectSupplement(id){
  const entry=byId.get('supplement:'+id);if(!entry)return false;
  activeSupplement=entry.identity;selected=entry;isolated=true;
  lab.root.scale.setScalar(1);presentation.position.set(0,0,0);sourceRoot.updateWorldMatrix(true,true);
  const box=boxForMeshes(entry.meshes),c=box.getCenter(new THREE.Vector3()),s=box.getSize(new THREE.Vector3());
  modelSize=Math.max(s.x,s.y,s.z);lab.size=modelSize;lab.k=2.4/modelSize;
  presentation.position.set(-c.x,-box.min.y+.012*modelSize,-c.z);lab.root.scale.setScalar(lab.k);presentation.updateWorldMatrix(true,true);
  wholeBox=boxForMeshes(entry.meshes);defaultView=viewForBox(wholeBox,{whole:true});lab.setView(defaultView);
  lab.camera.near=Math.max(.00001,defaultView.dist*2.4/250);lab.camera.updateProjectionMatrix();
  dock.querySelector('#library').value=active.id+':'+id;
  refreshVisibility();setSelectionHighlight();updateInspector();renderTree();updateScope();updateEvidence();updateHero();shadowDirty=true;return true;
}

function prepareExplosion(){
  if(active.kind==='library'){explodeTargets=[];return;}
  const center=wholeBox.getCenter(new THREE.Vector3());
  const candidates=entries.filter(e=>e.kind==='component'&&e.objects.length&&!e.filename?.endsWith('.SLDASM')&&e.meshes.length);
  const visited=new Set();explodeTargets=[];
  for(const [index,e] of candidates.entries()){const object=e.objects.find(o=>!o.isMesh)??e.objects[0];if(visited.has(object))continue;let parent=object.parent,hasTargetParent=false;while(parent){if(visited.has(parent)){hasTargetParent=true;break;}parent=parent.parent;}if(hasTargetParent)continue;visited.add(object);const c=boxForMeshes(e.meshes).getCenter(new THREE.Vector3());const dir=new THREE.Vector3(c.x-center.x,0,c.z-center.z);if(dir.length()<modelSize*lab.k*.004){const angle=index*2.399963;dir.set(Math.cos(angle),0,Math.sin(angle));}dir.normalize().multiplyScalar(modelSize*.1*lab.k);dir.y=(c.y-center.y)*.12;const inverse=new THREE.Matrix3().setFromMatrix4(object.parent.matrixWorld.clone().invert());const local=dir.applyMatrix3(inverse);explodeTargets.push({object,base:object.position.clone(),offset:local});}
}

function renderTree(){
  const term=dock.querySelector('#search').value.trim().toLowerCase(),category=dock.querySelector('#category').value;
  const visible=[];const match=e=>{const raw=e.label+' '+(e.filename??'')+' '+e.path;return(!category||e.category===category)&&(!term||(raw+' '+publicName(raw)).toLowerCase().includes(term));};
  if(term||category){for(const e of entries)if((showMeshes||e.kind!=='mesh'||term)&&match(e))visible.push(e);}else{const walk=e=>{if(e.kind==='mesh'&&!showMeshes)return;visible.push(e);if(expanded.has(e.id))for(const c of e.children)walk(c);};for(const e of topEntries)walk(e);}
  dock.querySelector('.tree').innerHTML=visible.length?visible.map(e=>{const expandable=e.children.some(c=>showMeshes||c.kind!=='mesh');const depth=term||category?0:Math.min(e.depth,9);return`<div class="tree-row kind-${esc(e.kind)}${selected?.id===e.id?' selected':''}${e.originalHidden?' source-hidden':''}" role="treeitem" aria-selected="${selected?.id===e.id}" aria-level="${e.depth+1}"${expandable?' aria-expanded="'+expanded.has(e.id)+'"':''} style="padding-left:${depth*11}px" data-entry="${identityEsc(e.id)}"><button class="tree-toggle" tabindex="${expandable?'0':'-1'}" aria-label="${expanded.has(e.id)?'折叠':'展开'}${esc(e.label)}">${expandable?(expanded.has(e.id)?'⌄':'›'):''}</button><i class="tree-mark"></i><button class="tree-label" title="${esc(e.filename??e.path)}">${esc(e.label)}${term?'<small>'+esc(e.filename??e.path)+'</small>':''}</button>${e.originalHidden?'<span class="tree-count">隐藏</span>':''}<span class="tree-count" title="包含的网格数">${e.kind==='mesh'?'M':fmt(e.meshes.length)}</span></div>`;}).join(''):'<div class="tree-empty">没有符合条件的源记录。</div>';
  setPublicText(dock.querySelector('.tree-status'),(term||category?'匹配 '+visible.length+' 条；':'')+'组件/组按源层级排列，数字为所含网格数。');
}
dock.querySelector('.tree').addEventListener('click',ev=>{const row=ev.target.closest('[data-entry]');if(!row)return;const e=byId.get(row.dataset.entry);if(ev.target.closest('.tree-toggle')){expanded.has(e.id)?expanded.delete(e.id):expanded.add(e.id);renderTree();return;}selectEntry(e.id,{isolate:false,camera:false});});
dock.querySelector('.tree').addEventListener('dblclick',ev=>{const row=ev.target.closest('[data-entry]');if(row&&!ev.target.closest('.tree-toggle'))selectEntry(row.dataset.entry,{isolate:true,camera:true});});
for(const id of ['search','category'])dock.querySelector('#'+id).addEventListener('input',renderTree);
dock.querySelector('#show-meshes').onchange=e=>{showMeshes=e.target.checked;renderTree();};
dock.querySelector('#source-hidden').onchange=e=>{showHidden=e.target.checked;refreshVisibility();updateInspector();updateScope();shadowDirty=true;updateEvidence();};
dock.querySelector('#library').onchange=e=>{const value=e.target.value;if(!value){loadAsset(lastAssemblyId,{preserveSelection:false}).catch(showError);return;}const [assetId,supplementId]=value.split(':');if(active?.id===assetId)selectSupplement(supplementId);else loadAsset(assetId,{preserveSelection:false,supplementId}).catch(showError);};
tools.querySelector('#quality').onchange=e=>loadAsset(e.target.value).catch(showError);
tools.querySelector('#whole').onclick=()=>restoreWhole();tools.querySelector('#focus').onclick=()=>focus();tools.querySelector('#solo').onclick=()=>{if(selected)selectEntry(selected.id,{isolate:!isolated,camera:true});};

function refreshVisibility(){if(!sourceRoot)return;sourceRoot.traverse(o=>{o.visible=true;});const set=selected&&isolated?new Set(selected.meshes):null;for(const m of meshes)m.visible=(!set||set.has(m))&&(showHidden||!m.userData.originalSourceHidden||(!!set&&selected.originalHidden));tools.querySelector('#solo').classList.toggle('active',isolated);}
function clearHighlight(){for(const m of meshes)if(m.userData.baseMaterial)m.material=m.userData.baseMaterial;for(const m of selectedMaterials)m.dispose();selectedMaterials=[];}
function setSelectionHighlight(){clearHighlight();if(!selected)return;for(const mesh of selected.meshes){const clone=m=>{const c=m.clone();c.onBeforeCompile=m.onBeforeCompile;c.customProgramCacheKey=m.customProgramCacheKey;c.clippingPlanes=m.clippingPlanes;c.userData={...m.userData};c.emissive=new THREE.Color(.19,.115,.035);c.emissiveIntensity=.32;if(mesh.userData.originalSourceHidden){c.color.setRGB(.15,.25,.14);c.roughness=Math.max(c.roughness,.72);c.emissive.setRGB(.015,.04,.02);c.emissiveIntensity=.2;}selectedMaterials.push(c);return c;};mesh.material=Array.isArray(mesh.userData.baseMaterial)?mesh.userData.baseMaterial.map(clone):clone(mesh.userData.baseMaterial);}updateMaterials();}
function selectEntry(id,{isolate=false,camera=false}={}){const e=byId.get(id);if(!e)return false;if(active.kind==='library'&&e.supplementId)return selectSupplement(e.supplementId);selected=e;isolated=active.kind==='library'||isolate;if(e.originalHidden&&!isolated)isolated=true;refreshVisibility();setSelectionHighlight();updateInspector();renderTree();if(camera)focus(e);document.body.dataset.selection=e.id;document.body.dataset.isolated=String(isolated);shadowDirty=true;updateEvidence();return true;}
function restoreWhole(){if(active?.kind==='library'){loadAsset(lastAssemblyId,{preserveSelection:false}).catch(showError);return;}selected=null;isolated=false;clearHighlight();refreshVisibility();updateInspector();renderTree();lab.setView(defaultView);document.body.dataset.selection='whole';document.body.dataset.isolated='false';shadowDirty=true;updateEvidence();}
function reset(){lab.target.explode=lab.state.explode=0;for(const t of explodeTargets)t.object.position.copy(t.base);presentation?.updateWorldMatrix(true,true);lab.target.cut=lab.state.cut=0;lab.target.xray=lab.state.xray=0;wire=false;showHidden=false;dock.querySelector('#source-hidden').checked=false;spread.set(0);cutControl.classList.remove('on');lastExplode=-1;lastXray=-1;updateMaterials();restoreWhole();lab._syncButtons();}

function updateMaterials(){const x=lab.state.xray;for(const mesh of meshes){const list=Array.isArray(mesh.material)?mesh.material:[mesh.material];for(const m of list){const opacity=m.userData.sourceOpacity??1,transparent=m.userData.sourceTransparent||(m.userData.shell&&x>.005);if(m.transparent!==transparent){m.transparent=transparent;m.needsUpdate=true;}m.opacity=opacity*(m.userData.shell?1-.9*x:1);m.depthWrite=!transparent;m.wireframe=wire;}}}
function updateInspector(){if(!selected){inspector.innerHTML='<strong>原始相对位置</strong><div class="source-kind">源装配整体 · 原显隐保留</div><div class="detail-line">在目录或画面中选择节点，查看所属来源和三角化网格。</div><div class="actions"><button id="inspect-source">来源与覆盖</button></div>';inspector.querySelector('button').onclick=()=>{fillSourceDialog();dialog.showModal();};return;}const visible=selected.meshes.filter(m=>m.visible),triangles=selected.meshes.reduce((n,m)=>n+m.userData.triangles,0),providers=new Set(selected.meshes.flatMap(m=>meshProviders(m).map(p=>p.property_path)));const kind=selected.kind==='mesh'?'网格节点':selected.kind==='component'?'源组件节点':'源组/子装配节点';inspector.innerHTML=`<strong>${esc(selected.label)}</strong><div class="source-kind">${kind}${selected.category?' · '+esc(selected.category):''}</div>${selected.originalHidden?'<span class="flag">原作隐藏 · 当前为临时高亮检视</span>':''}<div class="detail-line"><b>${fmt(selected.meshes.length)}</b> 个网格 · ${fmt(triangles)} 个当前三角面<br>${fmt(visible.length)} 个网格正在显示${providers.size?'<br>'+fmt(providers.size)+' 个源几何提供者身份':''}</div><div class="actions"><button id="inspect-solo">${isolated?'恢复整箭':'隔离查看'}</button><button id="inspect-fit">放大选中</button><button id="inspect-origin">来源详情</button></div><code title="原文件与USD路径（显示名）">${esc(selected.filename??'源组名：'+selected.label)}<br>${esc(selected.rawPath??selected.path)}</code>`;inspector.querySelector('#inspect-solo').onclick=()=>isolated?restoreWhole():selectEntry(selected.id,{isolate:true,camera:true});inspector.querySelector('#inspect-fit').onclick=()=>focus();inspector.querySelector('#inspect-origin').onclick=()=>{fillSourceDialog(selected);dialog.showModal();};}
function updateHero(){if(!active)return;lab.setHero(loadedSourceNodeCount,{state:active.kind==='assembly'?'源整箭装配':'独立原件',sub:`${fmt(new Set(meshes.map(m=>active?.kind==='library'?(m.userData.presentation_id??m.userData.sourcePath):m.userData.sourcePath)).size)} 个源网格 · ${fmt(meshes.length)} 个渲染网格<br>${fmt(meshes.reduce((n,m)=>n+m.userData.triangles,0))} 个当前三角面`});setPublicText(modeNote,active.kind==='assembly'?active.label+' · 同源层级与位置；曲面三角化密度不同。':(activeSupplement?.unit_is_physical===false?'源STL未声明单位 · 不与整箭比较尺度。':'独立源原件 · 不在此处补造装配位置。'));spread.wrap.style.display=active.kind==='library'?'none':'';}
function updateScope(){scope.innerHTML=active?.kind==='library'?'<b>独立源原件检视。</b> 统一居中用于观看，不推定其在原整箭中的位置。':`<b>源装配转换检视。</b> 已保留全部载入网格及源显隐；${showHidden?'当前临时显示源隐藏件。':'默认隐藏 '+fmt(meshes.filter(m=>m.userData.originalSourceHidden).length)+' 个源网格。'} 展示偏移不代表拆装流程。`;}
function fillSourceDialog(entry=null){const standalone=active?.kind==='library',unitUnknown=standalone&&activeSupplement?.unit_is_physical===false;const sourceArchiveSha=standalone?(activeSupplement?.source_archive_sha256??'源库未附归档哈希'):SOURCE.archive_sha256;const providers=entry?entry.meshes.flatMap(m=>meshProviders(m).map(p=>p.property_path)):[];dialog.querySelector('.dialog-body').innerHTML=`${entry?`<p><b>${esc(entry.label)}</b><br>${esc(entry.filename??entry.label)}<br><code>${esc(entry.rawPath??entry.path)}</code></p>${providers.length?'<p>源几何提供者身份：<br>'+[...new Set(providers)].map(p=>'<code>'+esc(p)+'</code>').join('<br>')+'</p>':''}`:''}<p>${unitUnknown?'当前原件直接来自源STL，保留原始顶点；原STL未声明单位。':standalone?'当前原件来自相应源CAD的独立转换；独立修订件保留其各自归档身份。':'主模型来自原 SolidWorks 装配的真实转换；浏览级与精细级采用同源的不同三角化级别。'} CAD曲面转换后已三角化。页面保持本次转换的对象层级和相对位置，未生成替代部件，也没有由静态外观推断配合约束已求解。</p><div class="source-grid"><div><small>原始入口（显示名）</small>${esc(standalone?(activeSupplement?.source_filename??activeSupplement?.source_cad_filename):SOURCE.entry)}</div><div><small>来源归档（显示名）</small>${esc(standalone?(activeSupplement?.source_archive??SOURCE.archive):SOURCE.archive)}</div><div><small>当前页面载入</small>${fmt(loadedSourceNodeCount)} 个源组件/组节点 / ${fmt(new Set(meshes.map(m=>active?.kind==='library'?(m.userData.presentation_id??m.userData.sourcePath):m.userData.sourcePath)).size)} 个源网格 / ${fmt(meshes.length)} 个渲染网格</div><div><small>名称对照</small>${SOURCE.matched_source_files}/${SOURCE.source_file_count} 个源文件 · 不是完整率</div><div><small>源单位 → GLB</small>${unitUnknown?'原STL未声明单位，保留原数值；不与整箭比较尺度。':SOURCE.source_unit_metres+' 米/源单位 → GLB米'}</div><div><small>展示坐标</small>单独父组统一居中；Machine场景再统一缩放</div><div><small>原生配合/制造/飞行验证</small>未由此页面执行或证明</div><div><small>当前GLB身份</small><code>${esc(active?.sha256??'')}</code></div></div><p><small>原归档SHA256</small><br><code>${sourceArchiveSha}</code>${standalone?'<br><small>当前原件SHA256</small><br><code>'+esc(activeSupplement?.source_sha256??'')+'</code>':'<br><small>精细USD SHA256</small><br><code>'+SOURCE.source_usd_sha256+'</code>'}</p><p>本页将项目显示名统一为“启明火箭”；内部源标识、文件名匹配及哈希保持原样。</p><p>源文件、源组件/组节点、源网格和装配实例是不同计数。多材质源网格会被渲染器拆为多个渲染网格；不会增加源部件。源名未匹配可能涉及未用变体、工具、配置或名称差异，不能直接认定缺失几何。源作隐藏对象已保留，默认不强制显示。</p><p>以下源名尚未通过整箭节点名称匹配；独立库如已提供，可单独查看：</p><ul class="source-list">${SOURCE.unmatched_source_files.map(f=>'<li>'+esc(f)+'</li>').join('')}</ul><p>全部主R01源CAD身份目录（${SOURCE_CATALOG.length}条）：</p><table class="source-file-table"><thead><tr><th>源文件显示名</th><th>中文身份</th><th>格式</th></tr></thead><tbody>${SOURCE_CATALOG.map(r=>`<tr><td>${esc(r.filename)}</td><td>${esc(LABELS[r.filename]?.label_zh??r.filename)}</td><td>${r.format}</td></tr>`).join('')}</tbody></table>`;}

function updateEvidence(){window.assemblyEvidence={activeAsset:active?.id,assetKind:active?.kind,sourceNodesLoaded:loadedSourceNodeCount,sourceGLTFNodes:active?.glb_nodes,meshObjectsLoaded:meshes.length,sourceMeshObjectsExpected:active?.kind==='assembly'?SOURCE.source_full_mesh_count:null,sourceMeshIdentitiesLoaded:new Set(meshes.map(m=>active?.kind==='library'?(m.userData.presentation_id??m.userData.sourcePath):m.userData.sourcePath)).size,renderMeshObjectsLoaded:meshes.length,trianglesLoaded:meshes.reduce((n,m)=>n+m.userData.triangles,0),sourceFullTriangles:SOURCE.source_full_triangles,visibleMeshes:meshes.filter(m=>m.visible).length,sourceHiddenMeshObjects:meshes.filter(m=>m.userData.originalSourceHidden).length,sourceMatchedFiles:SOURCE.matched_source_files,sourceCatalogFiles:SOURCE.source_file_count,selected:selected?.id??null,isolated,originalCADTessellated:true,nativeMatesSolved:false,manufacturingValidated:false,flightValidated:false,showHidden,wireframe:wire,displayTranslation:presentation?.position.toArray(),displayUniformScale:lab.k,glbUnit:active?.kind==='library'&&activeSupplement?.unit_is_physical===false?'source STL unit undeclared':'metre',sourceUnitMetres:active?.kind==='library'&&activeSupplement?.unit_is_physical===false?null:SOURCE.source_unit_metres,glbSha256:active?.sha256,measuredFPS:fps};}

function updateCutCenter(){const box=selected&&isolated?entryBox(selected):wholeBox;if(box.isEmpty())return;const center=box.getCenter(new THREE.Vector3()).divideScalar(lab.k);const fraction=Number(cutControl.querySelector('input').value)/100-.5;const extent=box.getSize(new THREE.Vector3()).z/lab.k;center.z+=fraction*extent;lab.o.cut.center=center.toArray();}
cutControl.querySelector('input').oninput=()=>{updateCutCenter();shadowDirty=true;};
lab.onTick(()=>{
  if(pendingLoad||!active)return;
  if(reduced&&!lab.filmMode)for(const k of ['explode','cut','xray'])lab.state[k]=lab.target[k];
  const e=lab.state.explode;if(Math.abs(e-lastExplode)>.00001){const k=ease.io(e);for(const t of explodeTargets)t.object.position.copy(t.base).addScaledVector(t.offset,k);lastExplode=e;presentation.updateWorldMatrix(true,true);if(Math.abs(e-lab.target.explode)<.001)shadowDirty=true;}
  const x=lab.state.xray;if(Math.abs(x-lastXray)>.0001){updateMaterials();lastXray=x;}
  if(Math.abs(spread.value-e*100)>.7)spread.set(lab.target.explode*100);
  updateCutCenter();frameCounter++;const now=performance.now();if(now-frameAt>1000&&!lab.filmMode){fps=frameCounter*1000/(now-frameAt);frameCounter=0;frameAt=now;updateEvidence();}
});

let down=null;
lab.renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];});
function pick(e,isolate=false){if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5||pendingLoad)return;const ray=new THREE.Raycaster(),pointer=new THREE.Vector2(e.clientX/innerWidth*2-1,1-e.clientY/innerHeight*2);ray.setFromCamera(pointer,lab.camera);const hits=ray.intersectObjects(meshes.filter(m=>m.visible),false);for(const hit of hits){const mats=Array.isArray(hit.object.material)?hit.object.material:[hit.object.material];const planes=mats[0].clippingPlanes;const clipped=lab.state.cut>.005&&planes?.length&&planes.every(p=>p.distanceToPoint(hit.point)<0);if(clipped)continue;selectEntry(hit.object.userData.navigationOwner,{isolate,camera:isolate});return;}}
lab.renderer.domElement.addEventListener('pointerup',e=>pick(e));lab.renderer.domElement.addEventListener('dblclick',e=>pick(e,true));
addEventListener('keydown',e=>{if(e.target.matches('input,select,textarea')||dialog.open)return;if(e.key==='Escape'){restoreWhole();return;}const key={c:'cut',x:'xray',e:'explode',w:'wire','0':'reset'}[e.key.toLowerCase()];if(key){e.preventDefault();activateMode(key);}});
addEventListener('resize',()=>{if(!pendingLoad&&defaultView&&!selected){defaultView=viewForBox(wholeBox,{whole:true});lab.setView(defaultView);}});

function setupFilm(){if(!active||active.kind!=='assembly')return;const inspect=entries.find(e=>e.filename?.startsWith('AVBY-ASSM')&&e.meshes.length)??entries.find(e=>e.category==='电子舱'&&e.meshes.length)??entries.find(e=>e.kind==='component'&&e.meshes.length);const box=inspect?boxForMeshes(inspect.meshes):wholeBox;const near=viewForBox(box,{az:38,el:18});const first={...defaultView,frameX:-.08,az:22},last={...first};lab.film('main',{len:24,shots:[{t:0,...first},{t:4,...first,az:34},{t:8,...defaultView,az:44,frameX:-.08},{t:12,...near,frameX:-.11},{t:16,...near,az:65,frameX:-.11},{t:20,...defaultView,az:40,dist:defaultView.dist*1.1,frameX:-.08},{t:24,...last}],events:[{t:0,beat:['01','从源装配开始。','原始层级与相对位置，来自实际CAD转换。'],do:()=>restoreWhole()},{t:4.2,beat:['02','打开一个展示剖面。','剖切只改变检视，不补造源几何。'],set:{cut:1}},{t:9.2,beat:['03','每个源节点，都能追溯。','选中电子舱子树，保留原层级。'],set:{cut:1},do:()=>{if(inspect)selectEntry(inspect.id,{isolate:true,camera:false});}},{t:15,beat:['04','局部细节，仍可追溯。','展示剖面中保留原来的内部组件。']},{t:18,beat:['05','仅为展示分开。','偏移不是拆装顺序，也不改变来源身份。'],do:()=>restoreWhole(),set:{explode:1,cut:0}},{t:22,set:{explode:0,cut:0,xray:0}}]});}

function showError(error){console.error(error);pendingLoad=false;const el=loading('模型未能完成读取',String(error.message??error));el.querySelector('div').classList.add('error-state');document.body.dataset.ready='error';window.assemblyError=String(error.stack??error);}
window.assemblyReview={select:(id,options)=>selectEntry(id,options),selectByFilename:(name,options)=>{const e=entries.find(x=>x.filename===name&&x.kind!=='mesh');return e?selectEntry(e.id,options):false;},restore:restoreWhole,reset,focus,loadMode:id=>loadAsset(id),setHidden:on=>{showHidden=!!on;dock.querySelector('#source-hidden').checked=showHidden;refreshVisibility();updateEvidence();updateScope();},setMeshNodes:on=>{showMeshes=!!on;dock.querySelector('#show-meshes').checked=showMeshes;renderTree();},getEntries:()=>entries.map(e=>({id:e.id,label:e.label,kind:e.kind,filename:e.filename,sourceDisplayName:e.sourceDisplayName,path:e.path,meshCount:e.meshes.length,originalHidden:e.originalHidden,parent:e.parent?.id??null})),getMeshes:()=>meshes.map(m=>({id:m.userData.meshNavigationId,path:m.userData.sourcePath,filename:m.userData.sourceFilename,triangles:m.userData.triangles,sourceHidden:m.userData.originalSourceHidden,visible:m.visible})),toggle:activateMode,source:SOURCE};
loadAsset(q.get('quality')&&fullAssets.some(a=>a.id===q.get('quality'))?q.get('quality'):(fullAssets.find(a=>a.id==='browse')??fullAssets[0])?.id,{preserveSelection:false}).then(async()=>{
  const requested=q.get('part');
  if(requested){
    let entry=entries.find(e=>e.filename===requested&&e.kind!=='mesh');
    if(!entry){const independent=LIBRARY_ENTRIES.find(e=>e.source_filename===requested);if(independent){await loadAsset(independent.asset_id,{preserveSelection:false,supplementId:independent.supplement_id});entry=entries.find(e=>e.filename===requested&&e.kind!=='mesh');}}
    if(entry)selectEntry(entry.id,{isolate:true,camera:true});
    window.assemblyInitialSelection={requestedSourceFilename:requested,matched:!!entry,sourcePath:entry?.path??null,sourceLibraryNotAssembly:active.kind==='library'};
  }
}).catch(showError);
