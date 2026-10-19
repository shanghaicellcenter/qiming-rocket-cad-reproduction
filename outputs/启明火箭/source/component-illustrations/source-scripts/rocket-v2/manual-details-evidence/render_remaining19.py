"""Source-specific documentary cards. Keeps public data and frozen course source untouched."""
import bpy
import importlib.util
import json
import sys
from pathlib import Path

WORK=Path('/Users/qianqiming/Documents/Codex/2026-10-19/ni/work/rocket-v2/manual-details-evidence')
spec=importlib.util.spec_from_file_location('manual_card_tools',WORK/'render_first3.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def point_on_render(source,point):
    x0,y0,x1,y1=source['crop'];a,c,d,e=source['renderImageBounds']
    return [a+(point[0]-x0)*(d-a)/(x1-x0),c+(point[1]-y0)*(e-c)/(y1-y0)]

def build(row):
    b.base(row)
    b.rect(row['id']+'_source_area',[55,198,855,845],b.M['white'],0)
    source=row['sources'][0]
    p=b.image_plane(source,[78,218,750,607],row['id'])
    b.txt(row['label'],912,261,32,b.M['teal'],row['id']+'_label')
    b.leader(row['id']+'_leader',(912,291),p)
    b.txt('它做什么',912,427,27,b.M['muted'],row['id']+'_role_heading')
    b.txt(row['role'],912,478,30,b.M['ink'],row['id']+'_role')
    b.txt('看图时分清',912,635,27,b.M['muted'],row['id']+'_note_heading')
    b.txt(row['note'],912,681,25,b.M['ink'],row['id']+'_note')
    if row['id']=='C1-11':
        # An explicit annotation treatment: original source file remains packed untouched.
        # Fade its rendered CAD context, then trace the case contour; no replacement geometry.
        ob=next(o for o in bpy.data.objects if o.name==row['id']+'_original_photo')
        nt=ob.data.materials[0].node_tree
        tx=next(n for n in nt.nodes if n.type=='TEX_IMAGE');emit=next(n for n in nt.nodes if n.type=='EMISSION')
        mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[0].default_value=.78;mix.inputs[2].default_value=(1,1,1,1)
        nt.links.new(tx.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs[0],emit.inputs['Color'])
        outlines=[[(4,115),(20,91),(570,61),(750,78),(770,96),(769,414),(595,439),(3,420),(4,115)],[(270,87),(291,52),(316,10),(330,5),(430,0),(449,7),(474,60),(504,77),(478,82),(449,29),(442,20),(334,28),(310,78),(270,87)]]
        for i,ps in enumerate(outlines):b.line(row['id']+'_case_outline_'+str(i),[point_on_render(source,p) for p in ps],b.M['teal'],3,25)
        source['renderAnnotationTreatment']={'wholeImageFadeTowardWhite':.78,'caseOutlineTracedFromOriginal':True,'sourcePixelsRewritten':False}
        b.footer('上下文定位 · 只强调箱体轮廓，不是独立空箱CAD或商品认证',f'来源：物理页 {source["physicalPage"]} / 印刷页 {source["printedPage"]} · {source["file"]} · 原图内部设备淡化以区分箱体')
    elif row['id']=='C1-27':
        # Three labels total. The silver end fittings remain visibly outside the gold body.
        a=point_on_render(source,[246,151]);c=point_on_render(source,[716,164])
        b.txt('锁紧区',106,784,25,b.M['teal'],'lock_label');b.leader('lock_leader',(107,748),a)
        b.txt('外接件另列',614,784,25,b.M['teal'],'neighbor_label');b.leader('neighbor_leader',(616,748),c)
        b.footer('原手册装配局部 · 非独立单件CAD或商品认证',f'来源：物理页 {source["physicalPage"]} / 印刷页 {source["printedPage"]} · {source["file"]} · 两端银色接头不是中间金色穿壁体')
    else:
        photograph=row['kind'] in ('source_photo','source_photo_context')
        typ='原手册实照局部' if photograph else '原手册CAD安装局部'
        if row['id'] in ('B1-03','B1-04'):typ='原手册外观实例'
        b.footer(typ+' · 非独立单件CAD或商品认证',f'来源：物理页 {source["physicalPage"]} / 印刷页 {source["printedPage"]} · {source["file"]} · 仅作物项定位与角色解释')

def main():
    print('BLENDER_VERSION',bpy.app.version_string,flush=True)
    frozen=b.sha(b.FROZEN)
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    sc=bpy.context.scene;sc.render.engine='BLENDER_EEVEE_NEXT' if bpy.app.version<(5,0,0) else 'BLENDER_EEVEE';eevee=sc.render.engine
    sc.render.resolution_x=b.W;sc.render.resolution_y=b.H;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.film_transparent=False
    sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0;sc.view_settings.gamma=1;sc.world.color=(0,0,0)
    cd=bpy.data.cameras.new('ManualDetails_Ortho');cam=bpy.data.objects.new('ManualDetails_Ortho',cd);sc.collection.objects.link(cam);cam.location=(b.W/2,b.H/2,2000);cd.type='ORTHO';cd.ortho_scale=b.W;cd.clip_end=5000;sc.camera=cam
    b.font=bpy.data.fonts.load(b.FONT);b.M={k:b.mat('ManualCard_'+k,v) for k,v in dict(bg='#f2f5f3',ink='#18373d',muted='#52686c',teal='#087f8a',white='#ffffff',border='#ccd8d5',gold='#b39745',concept='#7e9996').items()}
    rows=json.loads((WORK/'remaining19-spec.json').read_text())['rows'];results=[]
    chosen=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if chosen:rows=[r for r in rows if r['id'] in chosen]
    for row in rows:
        old=set(bpy.data.objects);build(row);bpy.context.view_layer.update()
        sc.render.filepath=str(WORK/(row['id']+'.png'));bpy.ops.render.render(write_still=True)
        if row['id']=='C1-11':
            sc.render.engine='CYCLES';sc.cycles.samples=8;sc.cycles.use_denoising=False;sc.render.filepath=str(WORK/'C1-11-cycles-reference.png');bpy.ops.render.render(write_still=True);sc.render.engine=eevee
        bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();blend=b.BLENDS/(row['id']+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
        row.update(blend=str(blend),renderPNG=str(WORK/(row['id']+'.png')),imageSourceUnchanged=all(b.sha(b.SOURCE/s['file'])==s['sha256'] for s in row['sources']),visualReviewed=False)
        results.append(row)
        for ob in set(bpy.data.objects)-old:bpy.data.objects.remove(ob,do_unlink=True)
        print('RENDERED',row['id'],flush=True)
    after=b.sha(b.FROZEN);assert frozen==after
    if chosen:
        previous=json.loads((WORK/'render-evidence-remaining19.json').read_text())['items'];updates={r['id']:r for r in results};results=[updates.get(r['id'],r) for r in previous]
    report={'blenderVersion':bpy.app.version_string,'canvas':[b.W,b.H],'engine':eevee,'documentaryPhotoTreatment':'sRGB source texture -> emission -> Standard sRGB; UV crop only. C1-11 CAD context has declared shader fade and outline annotations.','sourcePhotosModified':False,'publicDataModified':False,'frozenBlendBefore':frozen,'frozenBlendAfter':after,'frozenBlendUnchanged':True,'items':results}
    (WORK/'render-evidence-remaining19.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('RESULT '+json.dumps({'count':len(results)}),flush=True)

if __name__=='__main__':main()
