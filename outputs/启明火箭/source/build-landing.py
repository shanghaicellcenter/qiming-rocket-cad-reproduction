"""Build the offline Chinese project entrance using only the Python stdlib.

The images are existing renders of the supplied source CAD. Optional film links
appear only when their target exists. No model, document or video is rewritten.
"""
from pathlib import Path
import json,html,hashlib,datetime

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def esc(text):return html.escape(str(text),quote=True)
def existing(relative):
    path=(ROOT/relative).resolve()
    if not path.is_file():raise FileNotFoundError(f'Missing linked deliverable: {relative}')
    return relative
def anchor(relative,label,cls=''):
    return f'<a class="{esc(cls)}" href="{esc(existing(relative))}">{esc(label)}<span aria-hidden="true">↗</span></a>'

index=read(ROOT/'library/preview-index.json')
primary_record_count=index['source_record_count'];primary_image_count=index['image_count']
exchange_summary=ROOT/'native-cad/exchange-source/actual-read-summary.json'
exchange=read(exchange_summary) if exchange_summary.is_file() else None
record_count=primary_record_count+(exchange['step']['source_files'] if exchange else 0)
image_count=primary_image_count+(exchange['step']['png_views'] if exchange else 0)
mesh_count=read(ROOT/'native-cad/vehicle.validation.json')['mesh_count']
hero=existing('library/assembly-previews/A12-oblique.png')
electronics=existing('library/assembly-previews/A04-oblique.png')
whole=anchor('整箭原件检视.html','打开整箭检视','button primary')
parts=anchor('library/逐件原件预览.html','逐件看图','button secondary')
exchange_button=anchor('library/exchange-source/交换格式来源图册.html','STEP与二维来源图册','button secondary') if exchange else ''
animated=anchor('../virtual-assembly/virtual-assembly.blend','打开虚拟归位模型','text-link')
model_links=''.join([
    anchor('assembly/vehicle-original.blend','完整精细模型 · Blender','resource'),
    anchor('assembly/vehicle-browse.blend','流畅浏览模型 · Blender','resource'),
    anchor('../virtual-assembly/virtual-assembly.blend','15段虚拟归位 · Blender','resource')])
evidence_links=''.join([
    anchor('library/source-drawings/原图纸浏览.html','原图纸 · 13页','resource'),
    anchor('../virtual-assembly/逐环节质量核对说明.md','15环节原理与质量核对','resource'),
    anchor('复现验收.md','复现验收','resource'),
    anchor('research/coverage.json','来源覆盖清单','resource'),
    anchor('research/simulation/simulation-review-report.md','已有仿真核对','resource'),
    anchor('research/flight-evidence/证据审查.md','实测与飞行证据','resource')])
extra_resources=HERE/'landing-resources.json'
if extra_resources.is_file():
    evidence_links+=''.join(anchor(x['path'],x['label'],'resource') for x in read(extra_resources).get('links',[]))

# Root may add accepted final media here or in landing-media.json. Candidates
# are never linked before the file is present; the old early-stage clip is not
# included automatically.
optional=[
    {'path':'逐步虚拟归位.html','label':'打开逐步讲解'},
    {'path':'media/逐步虚拟归位.mp4','label':'播放逐步讲解视频'}]
registry=HERE/'landing-media.json'
if registry.is_file():optional=read(registry).get('links',optional)
available=[]
for item in optional:
    if (ROOT/item['path']).resolve().is_file():available.append(item)
if available:
    film='<section class="media" aria-labelledby="film-title"><div><span class="eyebrow">继续看</span><h2 id="film-title">跟着原件，逐步归位。</h2></div><div class="media-links">'+''.join(anchor(x['path'],x['label'],'button secondary') for x in available)+'</div></section>'
else:
    film='<p class="film-status">逐步讲解短片正在完成。现在可以先查看15段虚拟归位的可编辑模型。</p>'

count_note=f'{mesh_count}记录整箭中的网格实例，同一原件可以多次出现。{record_count}是三维源文件记录，每条3个角度，共{image_count}图。'
if exchange:count_note+=f'主图册{primary_record_count}条/{primary_image_count}图；独立STEP图册35条/105图。13页原图纸及3份DXF的4个二维视图另列。多格式和版本分别保留，不把源文件数当实体零件数。'

css='''
:root{--paper:#f0efe8;--ink:#282b25;--muted:#757970;--line:#d8d9cf;--accent:#6d342e}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(ellipse at 66% 26%,#faf9f2 0,transparent 57%),var(--paper);color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",sans-serif}a{color:inherit;text-decoration:none}a:focus-visible{outline:2px solid var(--accent);outline-offset:5px}button,a{-webkit-tap-highlight-color:transparent}header,main,footer{max-width:1360px;margin:auto;padding-left:56px;padding-right:56px}header{height:96px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}.brand{font:13px/1.4 Georgia,serif;letter-spacing:.13em}.brand small{display:block;font:10px/1.6 -apple-system,sans-serif;letter-spacing:.12em;color:var(--muted)}nav{display:flex;gap:27px;font-size:12px;color:var(--muted)}nav a:hover{color:var(--ink)}.hero{min-height:620px;display:grid;grid-template-columns:1.05fr 1fr;position:relative;align-items:center;gap:18px}.eyebrow{color:var(--muted);letter-spacing:.15em;font-size:10px;text-transform:uppercase}.hero-copy{position:relative;z-index:1;padding:58px 0 38px}.hero h1{font:76px/.96 Georgia,"Times New Roman",serif;font-weight:400;letter-spacing:-.055em;margin:21px 0 26px}.hero h1 em{font-style:italic}.hero h2{font-size:28px;font-weight:450;line-height:1.45;letter-spacing:-.025em;margin:0 0 20px}.hero p{max-width:445px;color:var(--muted);line-height:1.95;margin:0 0 27px;font-size:14px}.actions{display:flex;gap:12px;flex-wrap:wrap}.button{display:inline-flex;align-items:center;justify-content:space-between;gap:27px;min-height:48px;padding:11px 20px;border:1px solid var(--ink);border-radius:3px;font-size:12px;transition:transform .15s,background .15s}.button:hover{transform:translateY(-2px)}.primary{background:var(--ink);color:#f9f8ef}.secondary{border-color:#c8cbbf;background:#f7f6f0}.hero-figure{margin:0;min-width:0;align-self:stretch;position:relative;display:grid;place-items:center;overflow:hidden}.hero-figure img{width:100%;height:570px;object-fit:contain;transform:rotate(23deg) scale(1.06);filter:drop-shadow(12px 18px 12px #7a7b6a16)}.hero-figure figcaption{position:absolute;bottom:34px;left:36px;color:var(--muted);font-size:10px;letter-spacing:.04em}.metrics{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:25px 0 22px}.metric{padding:0 29px;border-right:1px solid var(--line)}.metric:first-child{padding-left:0}.metric:last-child{border:0}.metric strong{font:47px/1 Georgia,serif;letter-spacing:-.04em;font-weight:400}.metric span{display:block;font-size:11px;color:var(--muted);margin-top:8px}.count-note{font-size:11px;color:var(--muted);max-width:820px;margin:14px 0 50px}.paths{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;margin:0 0 51px}.path{border-top:1px solid var(--ink);padding-top:16px}.number{font:italic 12px Georgia,serif;color:var(--muted)}.path h3{font-size:20px;font-weight:450;margin:11px 0 12px}.path p{font-size:12px;color:var(--muted);line-height:1.9;max-width:325px;margin:0 0 18px}.text-link{font-size:11px;border-bottom:1px solid #bfc1b5;padding-bottom:4px;display:inline-flex;gap:16px;align-items:center}.detail{display:grid;grid-template-columns:.85fr 1.15fr;gap:48px;border-top:1px solid var(--line);padding-top:38px;align-items:center}.detail-figure{margin:0;display:grid;place-items:center;min-height:350px;background:linear-gradient(140deg,#e8e9df,#f3f2eb);border-radius:3px}.detail-figure img{width:100%;height:330px;object-fit:contain}.detail-figure figcaption{font-size:10px;color:var(--muted);padding:0 15px 18px}.detail h2,.media h2{font:32px/1.35 Georgia,"Songti SC",serif;font-weight:400;letter-spacing:-.03em;margin:7px 0 12px}.detail .intro{font-size:12px;color:var(--muted);margin:0 0 20px}.resources{display:grid;grid-template-columns:1fr 1fr;gap:28px}.resources h3{font-size:11px;font-weight:500;color:var(--muted);margin:0 0 9px}.resource{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid var(--line);font-size:11px}.resource:hover{color:var(--accent)}.film-status{font-size:11px;color:var(--muted);padding:18px 0 33px}.media{display:flex;justify-content:space-between;gap:25px;align-items:center;padding:30px 0}.media-links{display:flex;gap:10px;flex-wrap:wrap}footer{border-top:1px solid var(--line);margin-top:24px;padding-top:22px;padding-bottom:29px;display:flex;justify-content:space-between;gap:32px;font-size:10px;color:var(--muted)}footer p{margin:0;max-width:720px}.credit{white-space:nowrap}.mobile-note{display:none}
@media(min-width:1450px){.hero{min-height:660px}.hero-figure img{height:620px}.hero h1{font-size:84px}}
@media(max-width:900px){header,main,footer{padding-left:28px;padding-right:28px}.hero{grid-template-columns:1.1fr .9fr;min-height:550px}.hero h1{font-size:58px}.hero h2{font-size:24px}.hero-figure img{height:510px;transform:rotate(15deg) scale(1.15)}.hero-figure figcaption{left:0;bottom:23px;font-size:9px}.paths{gap:20px}.detail{gap:28px;grid-template-columns:.75fr 1.25fr}.resources{gap:16px}}
@media(max-width:620px){header,main,footer{padding-left:22px;padding-right:22px}header{height:78px}.brand{font-size:11px}nav{gap:15px;font-size:10px}nav .desktop{display:none}.hero{display:flex;flex-direction:column;gap:0;min-height:0;align-items:stretch}.hero-copy{padding:38px 0 0}.hero h1{font-size:62px;margin:18px 0 19px}.hero h2{font-size:24px;margin-bottom:15px}.hero p{font-size:12px;line-height:1.85;margin-bottom:21px}.button{font-size:11px;padding:10px 15px;min-height:45px;gap:19px}.hero-figure{height:330px;align-self:auto}.hero-figure img{height:360px;width:100%;transform:rotate(28deg) scale(1.14)}.hero-figure figcaption{bottom:11px;left:0}.metrics{padding:19px 0}.metric{padding:0 17px}.metric strong{font-size:36px}.metric span{font-size:9px}.count-note{font-size:10px;margin:12px 0 33px}.paths{grid-template-columns:1fr;gap:25px;margin-bottom:34px}.path h3{margin:8px 0;font-size:19px}.path p{max-width:none;margin-bottom:12px}.detail{grid-template-columns:1fr;gap:24px;padding-top:28px}.detail-figure{min-height:270px}.detail-figure img{height:265px}.detail h2{font-size:28px}.resources{gap:22px}.resource{font-size:10px}.media{align-items:flex-start;flex-direction:column}footer{flex-direction:column;gap:12px;margin-top:0}.credit{white-space:normal}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.button{transition:none}}
'''
page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>启明火箭 · 打开项目</title><meta name="description" content="从原CAD整箭、逐件多角度图到可编辑虚拟归位与来源证据的项目总入口。"><style>{css}</style></head><body>
<header><div class="brand">HALF CAT ROCKETRY<small>启明火箭 / R01</small></div><nav aria-label="项目导航"><a href="整箭原件检视.html">整箭</a><a href="library/逐件原件预览.html">逐件</a><a href="#models" class="desktop">模型与证据</a></nav></header>
<main><section class="hero" aria-labelledby="title"><div class="hero-copy"><span class="eyebrow">从原文件开始 · 项目入口</span><h1 id="title">启明<br><em>火箭</em></h1><h2>从整箭，到每个原件。</h2><p>来自 Half Cat Rocketry R01 的原CAD与公开资料。先看整体关系，再逐件对照；需要检查原始相对位置时，打开虚拟归位模型。</p><div class="actions">{whole}{parts}{exchange_button}</div></div><figure class="hero-figure"><img src="{esc(hero)}" alt="启明火箭原整箭CAD的真实几何渲染" width="1280" height="960"><figcaption>A12 · 原整箭CAD渲染</figcaption></figure></section>
<section class="metrics" aria-label="来源规模"><div class="metric"><strong>{mesh_count:,}</strong><span>整箭源网格实例</span></div><div class="metric"><strong>{record_count:,}</strong><span>三维源文件记录</span></div><div class="metric"><strong>{image_count:,}</strong><span>原几何多角度图</span></div></section><p class="count-note">{count_note}</p>
<section class="paths" aria-label="从哪里开始"><article class="path"><span class="number">01 / 整体</span><h3>看它们怎样放在一起。</h3><p>旋转整箭，选中原层级里的部件，隔离放大，或切换到剖切与展示分开。</p>{anchor('整箭原件检视.html','进入整箭','text-link')}</article><article class="path"><span class="number">02 / 逐件</span><h3>把细节逐一看清。</h3><p>按中文名称和来源寻找原件。正面、侧面与斜视图对应同一条源记录。</p>{anchor('library/逐件原件预览.html','打开原件图册','text-link')}</article><article class="path"><span class="number">03 / 归位</span><h3>回到原CAD的位置。</h3><p>15段可编辑展示覆盖全部688个源网格实例。最终位置逐节点对照原CAD坐标。</p>{animated}</article></section>
<section class="detail" id="models" aria-labelledby="resources-title"><figure class="detail-figure"><img src="{esc(electronics)}" alt="原电子舱托板、线路板和紧固件的CAD渲染" width="1280" height="960" loading="lazy"><figcaption>A04 · 原电子舱托板装配</figcaption></figure><div><span class="eyebrow">留得下，也查得到</span><h2 id="resources-title">模型与证据，放在一起。</h2><p class="intro">继续编辑原几何，或回到资料核对这次复现的覆盖与边界。</p><div class="resources"><section><h3>可编辑模型</h3>{model_links}</section><section id="evidence"><h3>来源与核对</h3>{evidence_links}</section></div>{film}</div></section></main>
<footer><p>图像均来自已有源几何。CAD曲面经三角化显示；视觉归位与坐标一致，不等于实物配合、工作或飞行能力已经得到验证。</p><p class="credit">原设计归属 Half Cat Rocketry · 许可随项目保留</p></footer></body></html>'''
output=ROOT/'打开项目.html';output.write_text(page,encoding='utf-8')
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'output':str(output),
    'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
    'source_mesh_instances':mesh_count,'source_records':record_count,'source_images':image_count,
    'primary_source_records':primary_record_count,'primary_source_images':primary_image_count,
    'exchange_source_included':bool(exchange),
    'actual_source_images':[hero,electronics],
    'optional_existing_media_links':available,'optional_nonexistent_links_omitted':len(optional)-len(available),
    'network_resources':False,'standard_library_only':True}
(HERE/'landing-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
