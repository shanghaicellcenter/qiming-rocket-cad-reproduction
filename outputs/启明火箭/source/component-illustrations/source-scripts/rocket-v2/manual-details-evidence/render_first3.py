"""Editable, source-preserving manual cards; never opens the frozen course blend."""
import bpy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path('/Users/qianqiming/Documents/Codex/2026-10-19/ni')
WORK = ROOT/'work/rocket-v2/manual-details-evidence'
SOURCE = Path('/Users/qianqiming/Desktop/火箭设计 中文版/中文文档/images')
BLENDS = ROOT/'outputs/rocket/manual-detail-sources'
FROZEN = ROOT/'outputs/rocket/animation/causal-course.blend'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
W, H = 1600, 1000

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def rgb(c):
    v=[int(c[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in v)

def mat(name,c):
    m=bpy.data.materials.new(name)
    if m.node_tree is None: m.use_nodes=True
    nt=m.node_tree;nt.nodes.clear()
    e=nt.nodes.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*rgb(c),1);e.inputs['Strength'].default_value=1
    o=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(e.outputs[0],o.inputs['Surface'])
    return m

def mesh(name,coords,faces,m):
    me=bpy.data.meshes.new(name);me.from_pydata([(x,H-y,z) for x,y,z in coords],[],faces);me.validate()
    ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob);me.materials.append(m);ob['manual_details_owned']=True
    return ob

def rect(name,b,m,z=0):
    x0,y0,x1,y1=b
    return mesh(name,[(x0,y1,z),(x1,y1,z),(x1,y0,z),(x0,y0,z)],[(0,1,2,3)],m)

def txt(s,x,y,size,m,name):
    cu=bpy.data.curves.new(name,'FONT');cu.body=s;cu.font=font;cu.size=size;cu.space_character=1.02;cu.space_line=1.18;cu.align_y='TOP_BASELINE'
    ob=bpy.data.objects.new(name,cu);bpy.context.scene.collection.objects.link(ob);ob.location=(x,H-y,12);cu.materials.append(m);ob['manual_details_owned']=True
    return ob

def line(name,pts,m,width=3,z=14):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=width/2;cu.bevel_resolution=2
    sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,(x,y) in zip(sp.points,pts):p.co=(x,H-y,z,1)
    ob=bpy.data.objects.new(name,cu);bpy.context.scene.collection.objects.link(ob);cu.materials.append(m);ob['manual_details_owned']=True
    return ob

def ring(name,p,r=10):
    pts=[(p[0]+r*math.cos(a*math.tau/48),p[1]+r*math.sin(a*math.tau/48)) for a in range(49)]
    line(name+'_white',pts,M['white'],7,17);line(name,pts,M['teal'],3,25)

def leader(name,start,end):
    pts=[start,(start[0]+(end[0]-start[0])*.52,start[1]),end]
    line(name+'_halo',pts,M['white'],8,14);line(name,pts,M['teal'],3,22);ring(name+'_target',end)
    return pts

def image_plane(spec,bounds,name):
    path=SOURCE/spec['file'];assert sha(path)==spec['sha256'],str(path)
    img=bpy.data.images.load(str(path),check_existing=True);img.colorspace_settings.name='sRGB'
    sw,sh=img.size;x0,y0,x1,y1=spec['crop'];bx,by,bw,bh=bounds
    assert 0<=x0<x1<=sw and 0<=y0<y1<=sh
    scale=min(bw/(x1-x0),bh/(y1-y0));pw=(x1-x0)*scale;ph=(y1-y0)*scale
    px=bx+(bw-pw)/2;py=by+(bh-ph)/2
    m=mat(name+'_texture','#ffffff');nt=m.node_tree
    tx=nt.nodes.new('ShaderNodeTexImage');tx.image=img;tx.interpolation='Linear';tx.extension='CLIP'
    uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='SourceCropUV';nt.links.new(uv.outputs['UV'],tx.inputs['Vector'])
    e=next(n for n in nt.nodes if n.type=='EMISSION');nt.links.new(tx.outputs['Color'],e.inputs['Color'])
    ob=rect(name+'_original_photo',[px,py,px+pw,py+ph],m,2);uvs=ob.data.uv_layers.new(name='SourceCropUV')
    vals=[(x0/sw,1-y1/sh),(x1/sw,1-y1/sh),(x1/sw,1-y0/sh),(x0/sw,1-y0/sh)]
    for loop,p in zip(uvs.data,vals):loop.uv=p
    anchor=[px+(spec['anchor'][0]-x0)*scale,py+(spec['anchor'][1]-y0)*scale]
    spec.update(sourcePath=str(path),sourceSize=[sw,sh],renderImageBounds=[px,py,px+pw,py+ph],renderAnchor=anchor,sourcePixelsUnchanged=True)
    ob['source_file']=str(path);ob['source_sha256']=spec['sha256'];ob['crop_pixels']=spec['crop'];img.pack()
    return anchor

def base(row):
    rect(row['id']+'_background',[0,0,W,H],M['bg'],-2)
    txt('启明火箭  /  看清每一件',55,48,24,M['muted'],'series')
    txt(row['id'],1405,48,26,M['teal'],'id')
    txt(row['title'],55,128,52,M['ink'],'title')
    bw=270 if row['id']=='C1-33' else 200
    rect('evidence_badge',[W-bw-55,85,W-55,137],M['teal'],0)
    txt(row['badge'],W-bw-38,122,27,M['white'],'badge_text')
    rect('header_rule',[55,163,1545,165],M['border'],0)

def footer(line1,line2):
    rect('footer_rule',[55,875,1545,877],M['border'],0)
    txt(line1,55,916,25,M['ink'],'footer_scope')
    txt(line2,55,960,21,M['muted'],'footer_source')

def build_cloth(row):
    rect('photo_area',[55,198,810,845],M['white'],0)
    p=image_plane(row['sources'][0],[80,218,690,607],row['id'])
    txt('防热护布',880,260,36,M['teal'],'target_label')
    leader('cloth_pointer',(878,287),p)
    txt('先看清它是什么',880,420,27,M['muted'],'role_heading')
    txt(row['role'],880,470,31,M['ink'],'role')
    txt('原照片的织物局部',880,627,29,M['ink'],'context')
    txt('可见编织纹理与缝边。\n不由外观判断材质、尺寸或性能。',880,674,25,M['muted'],'limits')
    footer('原手册实照局部 · 不是独立单件图或商品认证','来源：物理页 304 / 印刷页 295 · p304_i3 · 仅裁切取景，原照片内容未改写')

def build_radio(row):
    rect('tx_panel',[55,198,780,815],M['white'],0);rect('rx_panel',[810,198,1545,815],M['white'],0)
    txt('发射机 · 原照局部',83,246,34,M['ink'],'tx_label')
    txt('接收机 · 安装局部',840,246,34,M['ink'],'rx_label')
    p=image_plane(row['sources'][0],[80,280,675,430],row['id']+'_tx')
    q=image_plane(row['sources'][1],[838,280,680,430],row['id']+'_rx')
    leader('tx_pointer',(104,731),p);leader('rx_pointer',(866,731),q)
    txt('发送遥控指令',102,783,29,M['teal'],'tx_role');txt('接收并交给地面系统',866,783,29,M['teal'],'rx_role')
    txt('两件物品分开识别；实照与安装图的证据性质不同。',55,852,29,M['muted'],'two_parts')
    footer('原手册局部 · 非独立CAD或商品认证图，不据外观认证型号或性能','来源：p286_i2 发射机实照；p273_i2 接收机安装图 · 接收机身份参照 p272 原标签')

def build_cord(row):
    rect('material_photo_area',[55,198,750,845],M['white'],0)
    p=image_plane(row['sources'][0],[80,219,640,607],row['id'])
    txt('原照中的细伞绳',805,249,33,M['teal'],'cord_label');leader('cord_pointer',(806,280),p)
    txt('地面系留 · 功能示意',805,420,32,M['ink'],'concept_heading')
    rect('concept_panel',[800,450,1545,696],M['white'],0)
    # New abstract relation drawing: two unbranded silhouettes and a flexible line.
    rect('retained_small_item',[1290,516,1380,590],M['concept'],3)
    rect('anchor_surface',[847,520,893,612],M['border'],3)
    ring('fixed_anchor',(916,563),16)
    line('anchor_to_surface',[(891,563),(901,563)],M['teal'],4,24)
    pts=[(932,563),(973,596),(1022,618),(1074,606),(1121,565),(1173,540),(1223,544),(1291,556)]
    line('concept_tether',pts,M['gold'],8,5)
    txt('柔性连接留住小部件',832,661,28,M['teal'],'concept_role')
    txt('左图只参照细绳形态。\n右图不是地面系留原实照。',805,758,29,M['ink'],'evidence_boundary')
    footer('同类材料参照 · 不是独立CAD或商品认证；不核验 EK5580 或强度','来源：物理页 303 / 印刷页 294 · p303_i3 主伞细绳局部 · 不将宽尼龙带当作细绳')

def main():
    global font,M
    print('BLENDER_VERSION',bpy.app.version_string,flush=True)
    before=sha(FROZEN);WORK.mkdir(exist_ok=True,parents=True);BLENDS.mkdir(exist_ok=True,parents=True)
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    sc=bpy.context.scene;sc.render.engine='BLENDER_EEVEE_NEXT' if bpy.app.version<(5,0,0) else 'BLENDER_EEVEE'
    eevee=sc.render.engine;sc.render.resolution_x=W;sc.render.resolution_y=H;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.film_transparent=False
    sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0;sc.view_settings.gamma=1
    sc.world.color=(0,0,0);camd=bpy.data.cameras.new('ManualDetails_Ortho');cam=bpy.data.objects.new('ManualDetails_Ortho',camd);sc.collection.objects.link(cam)
    cam.location=(W/2,H/2,2000);camd.type='ORTHO';camd.ortho_scale=W;camd.clip_end=5000;sc.camera=cam
    M={k:mat('ManualCard_'+k,v) for k,v in dict(bg='#f2f5f3',ink='#18373d',muted='#52686c',teal='#087f8a',white='#ffffff',border='#ccd8d5',gold='#b39745',concept='#7e9996').items()}
    font=bpy.data.fonts.load(FONT);rows=json.loads((WORK/'first3-spec.json').read_text())['rows']
    results=[]
    for row in rows:
        old=set(bpy.data.objects);base(row)
        {'A7-06':build_cloth,'C1-01':build_radio,'C1-33':build_cord}[row['id']](row)
        bpy.context.view_layer.update();sc.render.filepath=str(WORK/(row['id']+'.png'));bpy.ops.render.render(write_still=True)
        if row['id']=='C1-33':
            sc.render.engine='CYCLES';sc.cycles.samples=8;sc.cycles.use_denoising=False;sc.render.filepath=str(WORK/(row['id']+'-cycles-reference.png'));bpy.ops.render.render(write_still=True);sc.render.engine=eevee
        bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all()
        blend=BLENDS/(row['id']+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
        row.update(blend=str(blend),renderPNG=str(WORK/(row['id']+'.png')),annotationLabelCount={'A7-06':1,'C1-01':2,'C1-33':2}[row['id']],imageSourceUnchanged=all(sha(SOURCE/s['file'])==s['sha256'] for s in row['sources']),visualReviewed=False)
        results.append(row)
        for ob in set(bpy.data.objects)-old:bpy.data.objects.remove(ob,do_unlink=True)
        print('RENDERED',row['id'],flush=True)
    after=sha(FROZEN);assert before==after
    report={'blenderVersion':bpy.app.version_string,'canvas':[W,H],'engine':eevee,'documentaryPhotoTreatment':'sRGB source image texture -> emission strength 1 -> Standard sRGB; UV crop only, no AI redrawing, no relighting','sourcePhotosModified':False,'publicDataModified':False,'frozenBlendBefore':before,'frozenBlendAfter':after,'frozenBlendUnchanged':True,'items':results}
    (WORK/'render-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('RESULT '+json.dumps({'count':len(results),'report':str(WORK/'render-evidence.json')}),flush=True)

if __name__=='__main__':main()
