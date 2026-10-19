"""Source-preserving Blender annotation cards. Never opens or writes the frozen course scene."""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from project_inputs import ROOT, SOURCE_PREVIEWS
WORK = ROOT / 'work/rocket-v2/source-details-evidence'
OUT = ROOT / 'outputs/rocket/assets/source-details'
SOURCE_OUT = ROOT / 'outputs/rocket/source-detail-sources'
MANUAL = Path('/Users/qianqiming/Desktop/火箭设计 中文版/中文文档/images/p254_i3.jpeg')
FROZEN = ROOT / 'outputs/rocket/animation/causal-course.blend'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
W, H = 1200, 800
BG = '#f3f5f2'
INK = '#15343a'
MUTED = '#52676b'
TEAL = '#087e8b'

ROWS = [
    dict(id='A7-01', name='回收控制高度计', code='EGTMR-QRK', native='P087', crop=[35, 180, 733, 600],
         source=SOURCE_PREVIEWS/'P087-oblique.png', expected='3de7c847d82456804e11e5f5329fcde9fe4c0fff68e64d6a42b414c510b6c9e6',
         nativeName='EggTimer Quark.SLDPRT',
         lines=['原设计中的 Quark', '电路板简化外形。', '', '未展示完整真实电路，', '不能替代实物性能核验。']),
    dict(id='A7-16', name='回收电子电池', code='9V-BATT', native='P072', crop=[185, 55, 584, 733],
         source=SOURCE_PREVIEWS/'P072-oblique.png', expected='dc93d203038dda84055dbd83172087944dd6f8cde7df0771f9188e70b3d1c65c',
         nativeName='9V Battery.SLDPRT',
         lines=['原设计中的通用', '9V 电池外形。', '', '电池与电池座是两件。', '无品牌或性能含义。']),
    dict(id='C1-19', name='地面扩口接口转接件', code='50675K162', crop=[590, 110, 835, 420], anchor=[704, 309], originalArrow=[704, 278],
         source=MANUAL, expected='8c043c4975f986df11a7abf78bc2a2d007dea66167cf91e856404ee3b12cabf9',
         lines=['指向最右端转接件。', '原图货号与箭头保留。', '', '显示装配中的局部，', '不代表独立三维模型。']),
    dict(id='C1-21', name='地面穿壁连接件', code='50785K273', crop=[440, 110, 675, 410], anchor=[513, 281], originalArrow=[517, 255],
         source=MANUAL, expected='8c043c4975f986df11a7abf78bc2a2d007dea66167cf91e856404ee3b12cabf9',
         lines=['指向金色穿壁接头。', '黑色螺母另列一项。', '', '原页正文有货号冲突，', '本图依原图箭头对应。']),
    dict(id='C1-22', name='穿壁接口间隔螺母', code='97149A370', crop=[480, 240, 750, 497], anchor=[566, 327], originalArrow=[575, 385],
         source=MANUAL, expected='8c043c4975f986df11a7abf78bc2a2d007dea66167cf91e856404ee3b12cabf9',
         lines=['指向黑色六角螺母。', '与金色接头分开识别。', '', '相邻零件有遮挡，', '不是完整独立外形。']),
    dict(id='C1-23', name='压力测量分支接头', code='50785K222', crop=[280, 245, 560, 497], anchor=[413, 319], originalArrow=[409, 358],
         source=MANUAL, expected='8c043c4975f986df11a7abf78bc2a2d007dea66167cf91e856404ee3b12cabf9',
         lines=['指向中央三通体。', '正面可见支路接口。', '', '仅说明位置与拓扑，', '不说明密封或压力。']),
    dict(id='C1-24', name='测量区域直通接头', code='5485K22', crop=[240, 110, 500, 410], anchor=[318, 314], originalArrow=[311, 278],
         source=MANUAL, expected='8c043c4975f986df11a7abf78bc2a2d007dea66167cf91e856404ee3b12cabf9',
         lines=['指向阀与三通之间', '可见的小型六角短接。', '', '本体部分被邻件遮挡，', '不替换成相近货号。']),
    dict(id='C1-25', name='控制区域快插接口', code='9396T32', crop=[0, 260, 180, 497], anchor=[50, 319], originalArrow=[50, 353],
         source=MANUAL, expected='8c043c4975f986df11a7abf78bc2a2d007dea66167cf91e856404ee3b12cabf9',
         lines=['指向最左端快插头。', '原图货号与箭头保留。', '', '该件为 9396T32，', '未套用 T31 的外形。']),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgb(hex_value):
    v=[int(hex_value[i:i+2], 16)/255 for i in (1, 3, 5)]
    return tuple(c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4 for c in v)


def emission(name, color):
    mat=bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes=True  # Required on this installed Blender 4.4.3.
    nt=mat.node_tree
    nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial')
    emit=nt.nodes.new('ShaderNodeEmission')
    emit.inputs['Color'].default_value=(*rgb(color), 1)
    emit.inputs['Strength'].default_value=1
    nt.links.new(emit.outputs[0], out.inputs['Surface'])
    return mat


def mesh(name, coords, faces, mat):
    me=bpy.data.meshes.new(name)
    me.from_pydata([(x, H-y, z) for x,y,z in coords], [], faces)
    me.validate()
    ob=bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob['source_details_owned']=True
    me.materials.append(mat)
    return ob


def rect(name, bounds, mat, z=0):
    x0,y0,x1,y1=bounds
    return mesh(name, [(x0,y1,z),(x1,y1,z),(x1,y0,z),(x0,y0,z)], [(0,1,2,3)], mat)


def text(body, x, baseline, size, mat, font, name):
    cu=bpy.data.curves.new(name, 'FONT')
    cu.body=body
    cu.font=font
    cu.size=size
    cu.space_character=1.04
    cu.align_y='BOTTOM_BASELINE'
    ob=bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location=(x,H-baseline,4)
    cu.materials.append(mat)
    ob['source_details_owned']=True
    return ob


def line(name, pts, material, width=2, z=6):
    cu=bpy.data.curves.new(name, 'CURVE')
    cu.dimensions='3D'
    cu.bevel_depth=width/2
    cu.bevel_resolution=2
    sp=cu.splines.new('POLY')
    sp.points.add(len(pts)-1)
    for p,(x,y) in zip(sp.points,pts):
        p.co=(x,H-y,z,1)
    ob=bpy.data.objects.new(name,cu)
    bpy.context.scene.collection.objects.link(ob)
    cu.materials.append(material)
    ob['source_details_owned']=True
    return ob


def photo(row):
    img=bpy.data.images.load(str(row['source']), check_existing=True)
    img.colorspace_settings.name='sRGB'
    sw,sh=img.size
    x0,y0,x1,y1=row['crop']
    scale=min(770/(x1-x0), 468/(y1-y0))
    pw,ph=(x1-x0)*scale,(y1-y0)*scale
    px,py=50+(790-pw)/2,188+(474-ph)/2
    mat=emission(row['id']+'_source_sRGB', '#ffffff')
    nt=mat.node_tree
    tx=nt.nodes.new('ShaderNodeTexImage'); tx.image=img; tx.interpolation='Linear'
    uv=nt.nodes.new('ShaderNodeUVMap'); uv.uv_map='SourceCropUV'
    nt.links.new(uv.outputs['UV'],tx.inputs['Vector'])
    mix=nt.nodes.new('ShaderNodeMixRGB'); mix.blend_type='MIX'
    mix.inputs[1].default_value=(*rgb('#ffffff'),1)
    nt.links.new(tx.outputs['Alpha'],mix.inputs[0]); nt.links.new(tx.outputs['Color'],mix.inputs[2])
    emit=next(n for n in nt.nodes if n.type=='EMISSION')
    nt.links.new(mix.outputs[0],emit.inputs['Color'])
    ob=rect(row['id']+'_source_plane', [px,py,px+pw,py+ph], mat, 1)
    uvs=ob.data.uv_layers.new(name='SourceCropUV')
    vals=[(x0/sw,1-y1/sh),(x1/sw,1-y1/sh),(x1/sw,1-y0/sh),(x0/sw,1-y0/sh)]
    for loop,coord in zip(uvs.data,vals): loop.uv=coord
    row['sourceSize']=[sw,sh]
    row['renderCropBounds']=[px,py,px+pw,py+ph]
    row['pixelsPerSourcePixel']=scale
    if 'anchor' in row:
        row['renderAnchor']=[px+(row['anchor'][0]-x0)*scale,py+(row['anchor'][1]-y0)*scale]
    return row


def build(row, mats, font):
    before=set(bpy.data.objects)
    rect(row['id']+'_background', [0,0,W,H], mats['bg'],-2)
    rect(row['id']+'_rule', [38,137,1162,139], mats['border'],0)
    rect(row['id']+'_photo_frame', [36,172,856,678],mats['white'],0)
    rect(row['id']+'_sidebar', [879,172,1164,678],mats['white'],0)
    text('启明火箭 · 原件外形',39,42,21,mats['muted'],font,row['id']+'_series')
    text(row['id'],1034,42,23,mats['teal'],font,row['id']+'_id')
    text(row['name'],38,108,44,mats['ink'],font,row['id']+'_title')
    photo(row)
    text('原件对应',900,213,19,mats['muted'],font,row['id']+'_label')
    text(row['code'],900,258,29,mats['teal'],font,row['id']+'_code')
    body=row['lines']
    if 'native' in row:
        text('源库 '+row['native'],900,296,20,mats['muted'],font,row['id']+'_native_id')
        for i,value in enumerate(body):
            text(value,900,352+i*33,21,mats['ink'],font,row['id']+'_body_'+str(i))
        text('原 CAD 简化外形',38,725,27,mats['ink'],font,row['id']+'_status')
        text('原单件图：'+row['nativeName']+' · 仅作外形识别',38,765,19,mats['muted'],font,row['id']+'_source')
    else:
        for i,value in enumerate(body):
            text(value,900,316+i*32,20,mats['ink'],font,row['id']+'_body_'+str(i))
        text('青色引线：本物项',900,535,20,mats['teal'],font,row['id']+'_pointer_label')
        tx,ty=row['renderAnchor']
        pts=[(899,565),(845,565),(tx+38,ty+43),(tx,ty)]
        line(row['id']+'_leader_underlay',pts,mats['white'],7,6)
        line(row['id']+'_leader',pts,mats['teal'],3,11)
        vx,vy=pts[-2][0]-tx,pts[-2][1]-ty
        n=math.hypot(vx,vy);ux,uy=vx/n,vy/n
        mesh(row['id']+'_arrow',[(tx,ty,16),(tx+ux*15-uy*6,ty+uy*15+ux*6,16),(tx+ux*15+uy*6,ty+uy*15-ux*6,16)],[(0,1,2)],mats['teal'])
        ring=[(tx+10*math.cos(a*math.tau/40),ty+10*math.sin(a*math.tau/40)) for a in range(41)]
        line(row['id']+'_target_ring_underlay',ring,mats['white'],5,10)
        line(row['id']+'_target_ring',ring,mats['teal'],2,14)
        row['renderLeader']=pts
        text('原手册局部，非单件CAD',38,725,27,mats['ink'],font,row['id']+'_status')
        text('原图物理页 254 / 印刷页 245 · p254_i3 · 保留原货号及原箭头',38,765,19,mats['muted'],font,row['id']+'_source')
    bpy.context.view_layer.update()
    return list(set(bpy.data.objects)-before)


def main():
    print('BLENDER_VERSION',bpy.app.version_string,flush=True)
    WORK.mkdir(exist_ok=True,parents=True);OUT.mkdir(exist_ok=True,parents=True);SOURCE_OUT.mkdir(exist_ok=True,parents=True)
    frozen_before=sha(FROZEN)
    for ob in list(bpy.data.objects): bpy.data.objects.remove(ob,do_unlink=True)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT' if bpy.app.version < (5,0,0) else 'BLENDER_EEVEE'
    eevee_engine=scene.render.engine
    scene.render.resolution_x=W;scene.render.resolution_y=H;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
    scene.world.color=(0,0,0)
    camera_data=bpy.data.cameras.new('SourceDetails_Ortho')
    camera=bpy.data.objects.new('SourceDetails_Ortho',camera_data)
    scene.collection.objects.link(camera);camera.location=(W/2,H/2,2000)
    camera_data.type='ORTHO';camera_data.ortho_scale=W;camera_data.clip_end=5000;scene.camera=camera
    mats={k:emission('SourceDetails_'+k,c) for k,c in dict(bg=BG,ink=INK,muted=MUTED,teal=TEAL,white='#ffffff',border='#cbd7d4').items()}
    font=bpy.data.fonts.load(FONT)
    manifest=[]
    for row in ROWS:
        assert sha(row['source']) == row['expected'], 'Source hash mismatch '+row['id']
        objs=build(row,mats,font)
        scene.render.filepath=str(WORK/(row['id']+'.png'))
        bpy.ops.render.render(write_still=True)
        if row['id']=='C1-22':
            scene.render.engine='CYCLES';scene.cycles.samples=16
            scene.cycles.use_denoising=False
            scene.render.filepath=str(WORK/'C1-22-cycles-reference.png')
            bpy.ops.render.render(write_still=True)
            scene.render.engine=eevee_engine
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.file.pack_all()
        blend=SOURCE_OUT/(row['id']+'.blend')
        bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
        item={k:str(v) if isinstance(v,Path) else v for k,v in row.items()}
        item.update(sourceSha256=sha(row['source']),sourceUnchanged=sha(row['source'])==row['expected'],png=str(WORK/(row['id']+'.png')),targetImage='assets/source-details/'+row['id']+'.webp',editableSource=str(blend.relative_to(ROOT/'outputs/rocket')),editableSourceSha256=sha(blend),
                    evidenceType='source_cad_simplified' if 'native' in row else 'source_labelled_context',
                    sourcePhysicalPage=None if 'native' in row else 254,sourcePrintedPage=None if 'native' in row else 245,
                    visualReviewed=False,displayTransform='Source sRGB -> emission strength 1 -> Standard sRGB; orthographic; UV crop only; no redraw',
                    annotation='Native source-card text only' if 'native' in row else 'Original labels retained; extra cyan leader ends on the same physical item as the original part-number arrow')
        manifest.append(item)
        for ob in objs: bpy.data.objects.remove(ob,do_unlink=True)
        print('RENDERED',row['id'],flush=True)
    frozen_after=sha(FROZEN)
    assert frozen_before==frozen_after
    report=dict(blenderVersion=bpy.app.version_string,canvas=[W,H],engine=eevee_engine,lights='None: documentary sRGB image planes use emission to preserve source values',font=FONT,
                frozenScene=str(FROZEN),frozenSceneSha256Before=frozen_before,frozenSceneSha256After=frozen_after,frozenSceneUnchanged=True,
                sourcePackageModified=False,publicDataModified=False,items=manifest)
    (WORK/'render-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('RESULT '+json.dumps(dict(count=len(manifest),evidence=str(WORK/'render-evidence.json')),ensure_ascii=False),flush=True)


if __name__=='__main__': main()
