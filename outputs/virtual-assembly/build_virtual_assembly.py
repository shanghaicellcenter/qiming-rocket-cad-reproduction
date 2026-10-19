"""Editable source-only CAD visual-return animation.

The sequence is an editorial presentation, not a physical manufacturing or
assembly procedure. No mates, fit, collision accessibility, operation, pressure,
ignition, strength or safety are solved. All original source mesh occurrences
remain present; no substitute geometry or parachute is constructed.
"""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
import numpy as np
ROOT=Path('/Users/qianqiming/Documents/Codex/2026-10-19/new-chat')
WORK=ROOT/'work/virtual-assembly';OUT=ROOT/'outputs/virtual-assembly';PREV=WORK/'review-frames'
for p in (WORK,OUT,PREV):p.mkdir(parents=True,exist_ok=True)
PLAN_PATH=WORK/'assembly-stages.json'
plan=json.loads(PLAN_PATH.read_text());stages=plan['stages'];FINAL=plan['frame_end']
sys.path.append('/Users/qianqiming/.codex/skills/scenario-blender-animation/scripts')
import bx_anim as A

def log(phase,**kw):print('VIRTUAL_ASSEMBLY='+json.dumps({'phase':phase,**kw},ensure_ascii=False),flush=True)
def ma(m):return np.asarray(m,dtype=np.float64)
def arr(m):return [[float(x) for x in row] for row in m]
def canonical(p):
    a=p.split('/');wrapper=a[1];a[1]='vehicle'
    if len(a)>2 and a[2]==wrapper:a[2]='vehicle'
    return '/'.join(a)
source_map=json.loads((ROOT/'work/native-cad/vehicle.name-source-map.json').read_text())
file_paths={p:f for f,ps in source_map['file_to_prim_paths'].items() for p in ps}
def source_file(p):
    p=canonical(p)
    while p and p!='/':
        if p in file_paths:return file_paths[p],p
        p=p.rsplit('/',1)[0]
    return None,None

bpy.ops.wm.open_mainfile(filepath=plan['source_blend'])
source_scene=bpy.context.scene;source_scene.name='00_Original_R01_Source_LOD1'
source_objects=[o for o in source_scene.objects if o.get('source_usd_path')]
assert len(source_objects)==1980
src_by_path={o['source_usd_path']:o for o in source_objects}
mesh_paths={o['source_usd_path'] for o in source_objects if o.type=='MESH'}
assert len(mesh_paths)==688
stage_for_mesh={p:s['id'] for s in stages for p in s['mesh_source_paths']}
assert set(stage_for_mesh)==mesh_paths

# Restore true USD visibility from the retained metadata. The USD importer used
# import_visible_only=False to retain all geometry and leaves hide flags false;
# the original R01 visibility is therefore restored explicitly in this NEW file.
for ob in source_objects:
    hidden=bool(ob.get('source_hidden',False))
    # Enable viewport evaluation for baseline matrix readback. Blender leaves
    # disabled viewport nodes unevaluated after load (identity world cache).
    # The intended source visibility is restored below after readback.
    ob.hide_render=hidden;ob.hide_viewport=False
    filename,matched_path=source_file(ob['source_usd_path'])
    if filename:
        ob['source_cad_filename']=filename;ob['source_cad_match_ancestor_path']=matched_path
source_scene['source_visibility_restored_from_usd_metadata']=True
source_scene['source_geometry_or_transforms_modified']=False
source_scene.frame_set(1);bpy.context.view_layer.update()
baseline={o['source_usd_path']:{'name':o.name,'type':o.type,'local':ma(o.matrix_local).copy(),
 'world':ma(o.matrix_world).copy(),'basis':ma(o.matrix_basis).copy(),
 'parent_inverse':ma(o.matrix_parent_inverse).copy(),
 'parent_path':o.parent.get('source_usd_path') if o.parent else None,
 'hidden':bool(o.get('source_hidden',False)),
 'hide_render':bool(o.get('source_hidden',False)),'hide_viewport':bool(o.get('source_hidden',False)),
 'data':o.data if o.type=='MESH' else None} for o in source_objects}
children={o:[] for o in source_objects}
for ob in source_objects:
    if ob.parent in children:children[ob.parent].append(ob)
desc={}
def descendants_stages(ob):
    if ob in desc:return desc[ob]
    result={stage_for_mesh[ob['source_usd_path']]} if ob.type=='MESH' else set()
    for c in children[ob]:result|=descendants_stages(c)
    desc[ob]=result;return result
for ob in source_objects:descendants_stages(ob)
pure_roots=[]
for ob in source_objects:
    if len(desc[ob])!=1:continue
    if ob.parent in desc and desc[ob.parent]==desc[ob]:continue
    pure_roots.append(ob)
assert all(len(desc[o])==1 for o in pure_roots)

anim=bpy.data.scenes.new('01_Visual_CAD_Return_Animation')
anim.unit_settings.system=source_scene.unit_settings.system
anim.unit_settings.scale_length=source_scene.unit_settings.scale_length
anim.render.fps=24;anim.frame_start=1;anim.frame_end=FINAL
anim['QC_SHOW_SOURCE_HIDDEN']=False
anim['scope_zh']=plan['scope_zh']
anim['presentation_only']=True;anim['source_mesh_occurrences']=688
anim['source_original_scene']=source_scene.name
anim['source_usd_sha256']=plan['source_usd_sha256']
anim.id_properties_ui('QC_SHOW_SOURCE_HIDDEN').update(description='检查模式：仅临时显示动画副本中的原隐藏网格，不改变源显隐记录。')
model_col=bpy.data.collections.new('ANIMATION_SOURCE_OBJECTS_SHARED_MESH_DATA')
control_col=bpy.data.collections.new('PRESENTATION_CONTROLLERS_NOT_SOURCE_PARTS')
anim.collection.children.link(model_col);anim.collection.children.link(control_col)
clones={}
for ob in source_objects:
    cp=ob.copy();cp.name='ANIM_'+ob.name
    model_col.objects.link(cp);clones[ob]=cp
    cp['source_original_object_name']=ob.name
    cp['source_original_parent_path']=baseline[ob['source_usd_path']]['parent_path'] or ''
    cp['animation_transform_keys_on_source_object']=False
for ob,cp in clones.items():cp.parent=clones.get(ob.parent)
bpy.context.window.scene=anim
anim.frame_set(1);bpy.context.view_layer.update()
# Gate the raw clone before inserting presentation-only identity carriers.
clone_preflight=[]
for ob,cp in clones.items():
    expected=baseline[ob['source_usd_path']]
    e=float(max(np.abs(ma(cp.matrix_local)-expected['local']).max(),np.abs(ma(cp.matrix_world)-expected['world']).max()))
    if e:clone_preflight.append({'path':ob['source_usd_path'],'max_error':e})
assert not clone_preflight,clone_preflight[:3]

global_lo=np.array([np.inf]*3);global_hi=-global_lo
mesh_world_corners={}
for ob in source_objects:
    if ob.type!='MESH':continue
    points=np.array([tuple(ob.matrix_world@Vector(c)) for c in ob.bound_box],dtype=np.float64)
    mesh_world_corners[ob['source_usd_path']]=points
    global_lo=np.minimum(global_lo,points.min(axis=0));global_hi=np.maximum(global_hi,points.max(axis=0))
length=float(max(global_hi-global_lo))
for ob in source_objects:ob.hide_viewport=bool(ob.get('source_hidden',False))
masters={};carriers={s['id']:[] for s in stages}
for s in stages:
    ctrl=bpy.data.objects.new('RETURN_STAGE_'+s['id']+'_CONTROL',None);control_col.objects.link(ctrl)
    ctrl.empty_display_type='PLAIN_AXES';ctrl.empty_display_size=length*.015
    ctrl['presentation_only']=True;ctrl['stage_id']=s['id'];ctrl['title_zh']=s['title_zh']
    offset=np.array(s['presentation_offset_world_fraction_of_source_length'],dtype=float)*length
    s['presentation_offset_world_source_units']=offset.tolist()
    s['presentation_offset_world_metres']=(offset*plan['source_meters_per_world_unit']).tolist()
    s['controller_name']=ctrl.name;masters[s['id']]=ctrl
    A.key_pose(ctrl,{'location':tuple(offset)},1,keytype='EXTREME',interpolation='CONSTANT',handle='AUTO_CLAMPED')
    A.key_pose(ctrl,{'location':tuple(offset)},s['move_start_frame'],keytype='EXTREME',interpolation='BEZIER',handle='AUTO_CLAMPED')
    A.key_pose(ctrl,{'location':(0,0,0)},s['move_end_frame'],keytype='EXTREME',interpolation='CONSTANT',handle='AUTO_CLAMPED')
    A.key_pose(ctrl,{'location':(0,0,0)},FINAL,keytype='MOVING_HOLD',interpolation='CONSTANT',handle='AUTO_CLAMPED')
for ob in pure_roots:
    cp=clones[ob];sid=next(iter(desc[ob]));old_parent=cp.parent
    carrier=bpy.data.objects.new('PRESENTATION_CARRIER_'+sid+'_'+str(len(carriers[sid])+1).zfill(3),None)
    control_col.objects.link(carrier);carrier.parent=old_parent
    carrier['presentation_only']=True;carrier['stage_id']=sid
    carrier['source_root_path']=ob['source_usd_path']
    # The identity carrier does not alter the source object's own local matrix.
    cp.parent=carrier
    pw=baseline[ob['source_usd_path']]['world']
    if ob.parent:
        parent_world=Matrix(baseline[ob.parent['source_usd_path']]['world'].tolist())
    else:parent_world=Matrix.Identity(4)
    inv=parent_world.to_3x3().inverted()
    for axis in range(3):
        fc=carrier.driver_add('location',axis);driver=fc.driver;driver.type='SCRIPTED'
        for j,label in enumerate(('x','y','z')):
            var=driver.variables.new();var.name=label;var.type='SINGLE_PROP'
            var.targets[0].id=masters[sid];var.targets[0].data_path=f'location[{j}]'
        driver.expression='+'.join(f'({float(inv[axis][j]):.17g})*{var}' for j,var in enumerate(('x','y','z')))
    carriers[sid].append((ob,carrier))

# Inspection switch affects only animated copies; source geometry/visibility
# records and the original R01 scene are not altered by this switch.
for ob,cp in clones.items():
    if not ob.get('source_hidden',False):continue
    for prop in ('hide_render','hide_viewport'):
        fc=cp.driver_add(prop);drv=fc.driver;drv.type='SCRIPTED'
        var=drv.variables.new();var.name='show_hidden';var.type='SINGLE_PROP'
        var.targets[0].id_type='SCENE';var.targets[0].id=anim
        var.targets[0].data_path='["QC_SHOW_SOURCE_HIDDEN"]'
        drv.expression='not show_hidden'

def activate_frame(frame,show_hidden=None):
    bpy.context.window.scene=anim
    if show_hidden is not None:
        anim['QC_SHOW_SOURCE_HIDDEN']=show_hidden
        anim.update_tag()
    anim.frame_set(frame);bpy.context.view_layer.update()
def matrix_report(paths):
    rows=[]
    for p in sorted(paths):
        src=src_by_path[p];cp=clones[src];b=baseline[p]
        local=ma(cp.matrix_local);world=ma(cp.matrix_world)
        le=float(np.abs(local-b['local']).max());we=float(np.abs(world-b['world']).max())
        rows.append({'source_usd_path':p,'source_usd_canonical_path':canonical(p),'source_type':src.type,
          'source_object_name':b['name'],'animated_object_name':cp.name,
          'source_parent_path':b['parent_path'],
          'local_matrix_source':b['local'].tolist(),'local_matrix_returned':local.tolist(),
          'world_matrix_source':b['world'].tolist(),'world_matrix_returned':world.tolist(),
          'max_local_matrix_abs_error':le,'max_world_matrix_abs_error_source_units':we,
          'local_matrix_numerically_exact':bool(np.array_equal(local,b['local'])),
          'world_matrix_numerically_exact':bool(np.array_equal(world,b['world']))})
    return rows

stage_qc=[]
for s in stages:
    activate_frame(s['end_frame'],show_hidden=True)
    roots=[o for o,_ in carriers[s['id']]]
    covered=set()
    for root in roots:
        for ob in source_objects:
            p=ob['source_usd_path'];rp=root['source_usd_path']
            if p==rp or p.startswith(rp+'/'):covered.add(p)
        par=root.parent
        while par:
            if par.get('source_usd_path'):covered.add(par['source_usd_path'])
            par=par.parent
    rows=matrix_report(covered)
    q={'stage_id':s['id'],'frame':s['end_frame'],'checked_source_objects':len(rows),
      'checked_source_nonmesh_objects':sum(r['source_type']!='MESH' for r in rows),
      'checked_source_mesh_objects':sum(r['source_type']=='MESH' for r in rows),
      'max_local_matrix_abs_error':max(r['max_local_matrix_abs_error'] for r in rows),
      'max_world_matrix_abs_error_source_units':max(r['max_world_matrix_abs_error_source_units'] for r in rows),
      'all_local_matrices_numerically_exact':all(r['local_matrix_numerically_exact'] for r in rows),
      'all_world_matrices_numerically_exact':all(r['world_matrix_numerically_exact'] for r in rows),
      'objects':rows}
    stage_qc.append(q)
    s['maximal_pure_source_roots']=[o['source_usd_path'] for o,_ in carriers[s['id']]]
    s['presentation_carrier_names']=[c.name for _,c in carriers[s['id']]]
    s['geometric_qc_result']={k:v for k,v in q.items() if k!='objects'}
    pts=np.concatenate([mesh_world_corners[p] for p in s['mesh_source_paths']],axis=0)
    s['source_world_bbox_native']={'min':pts.min(axis=0).tolist(),'max':pts.max(axis=0).tolist()}
    s['mesh_source_records']=[]
    for p in s['mesh_source_paths']:
        f,fp=source_file(p);ob=src_by_path[p]
        s['mesh_source_records'].append({'source_usd_path':p,'canonical_path':canonical(p),
          'source_cad_filename':f,'source_cad_match_ancestor_path':fp,
          'source_hidden':bool(ob.get('source_hidden',False)),
          'source_triangle_count':int(ob.get('source_triangle_count',len(ob.data.polygons)))})

activate_frame(FINAL,show_hidden=True)
final_rows=matrix_report(src_by_path)
global_qc={'frame':FINAL,'source_objects_checked':1980,'source_mesh_occurrences':688,
 'source_mesh_occurrences_in_animation':sum(o.type=='MESH' for o in clones.values()),
 'all_source_mesh_data_shared_with_reference_scene':all(clones[o].data is o.data for o in source_objects if o.type=='MESH'),
 'all_source_meshes_preserved':set(stage_for_mesh)==mesh_paths,
 'partition_disjoint':len(stage_for_mesh)==sum(s['mesh_count'] for s in stages),
 'partition_complete':set(stage_for_mesh)==mesh_paths,
 'source_hidden_meshes':sum(o.type=='MESH' and o.get('source_hidden',False) for o in source_objects),
 'source_transform_action_keys_created':sum(bool(cp.animation_data and cp.animation_data.action) for cp in clones.values()),
 'max_local_matrix_abs_error':max(r['max_local_matrix_abs_error'] for r in final_rows),
 'max_world_matrix_abs_error_source_units':max(r['max_world_matrix_abs_error_source_units'] for r in final_rows),
 'all_local_matrices_numerically_exact':all(r['local_matrix_numerically_exact'] for r in final_rows),
 'all_world_matrices_numerically_exact':all(r['world_matrix_numerically_exact'] for r in final_rows),
 'world_matrix_error_note':'Maximum error among the 16 world-matrix coefficients in USD-to-Blender source coordinates; not a manufacturing tolerance.',
 'constraints_or_collision_solver_executed':False,'source_mesh_data_modified':False,
 'objects':final_rows}
log('Transform QC',**{k:v for k,v in global_qc.items() if k!='objects'})
assert global_qc['all_source_mesh_data_shared_with_reference_scene']
assert global_qc['all_local_matrices_numerically_exact'] and global_qc['all_world_matrices_numerically_exact']
assert all(q['all_local_matrices_numerically_exact'] and q['all_world_matrices_numerically_exact'] for q in stage_qc)
activate_frame(FINAL,show_hidden=False)
global_qc['source_visibility_records_preserved']=all(clones[o].get('source_hidden')==o.get('source_hidden') for o in source_objects)
global_qc['default_hidden_visibility_matches_usd']=all(bool(clones[o].hide_render)==bool(o.get('source_hidden',False)) for o in source_objects)
if not global_qc['default_hidden_visibility_matches_usd']:
    log('Visibility mismatch',objects=[{'name':clones[o].name,'hidden':bool(o.get('source_hidden',False)),
        'hide_render':bool(clones[o].hide_render),'hide_viewport':bool(clones[o].hide_viewport)}
        for o in source_objects if bool(clones[o].hide_render)!=bool(o.get('source_hidden',False))])
assert global_qc['default_hidden_visibility_matches_usd']

# Planned review camera: fixed informational three-quarter view and explicit
# stage-end cameras. Only cameras/controllers are presentation helpers.
anim.render.engine='BLENDER_WORKBENCH';anim.render.resolution_x=1440;anim.render.resolution_y=900
anim.render.resolution_percentage=100;anim.render.image_settings.file_format='PNG'
anim.render.film_transparent=False;anim.view_settings.view_transform='Standard'
world=bpy.data.worlds.new('VISUAL_RETURN_REVIEW_WORLD');world.color=(.055,.065,.08);anim.world=world
sh=anim.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL'
sh.show_shadows=False;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_backface_culling=False
sh.background_type='WORLD'
camera_data=bpy.data.cameras.new('VISUAL_RETURN_CAMERA');camera=bpy.data.objects.new('VISUAL_RETURN_CAMERA',camera_data)
control_col.objects.link(camera);camera['presentation_only']=True
camera_data.type='ORTHO';camera_data.clip_start=.001;camera_data.clip_end=10000
camera_data.lens=80;camera_data.passepartout_alpha=.95;anim.camera=camera
stage_directions={}
for s in stages:
    fin_paths=[r['source_usd_path'] for r in s['mesh_source_records']
        if (r['source_cad_filename'] or '').startswith('FIN-STD-')]
    if fin_paths:
        fin=src_by_path[fin_paths[0]]
        points=np.asarray([tuple(fin.matrix_world@v.co) for v in fin.data.vertices],dtype=float)
        eigenvalues,eigenvectors=np.linalg.eigh(np.cov(points.T))
        normal=Vector(eigenvectors[:,int(np.argmin(eigenvalues))])
        if normal.dot(Vector((1.4,-2.7,1.0)))<0:normal=-normal
        stage_directions[s['id']]=(normal*2.8+Vector((0,0,1))).normalized()
def set_camera(target,lo,hi,roll=35,direction=None):
    target=Vector(target);direction=Vector(direction if direction is not None else (1.4,-2.7,1.0)).normalized()
    camera.location=target+direction*length*3
    q=(target-camera.location).to_track_quat('-Z','Y')
    camera.rotation_euler=(q@Quaternion(Vector((0,0,1)),math.radians(roll))).to_euler()
    right=camera.rotation_euler.to_matrix()@Vector((1,0,0));up=camera.rotation_euler.to_matrix()@Vector((0,1,0))
    corners=[Vector((x,y,z))-target for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
    w=max(abs(v.dot(right)) for v in corners)*2;h=max(abs(v.dot(up)) for v in corners)*2
    camera_data.ortho_scale=max(w,h*1440/900)*1.13
def current_bounds(paths):
    arrays=[]
    for p in paths:
        cp=clones[src_by_path[p]]
        arrays.append(np.array([tuple(cp.matrix_world@Vector(c)) for c in cp.bound_box],dtype=float))
    pts=np.concatenate(arrays,axis=0);return pts.min(axis=0),pts.max(axis=0)
activate_frame(1,show_hidden=False)
ilo,ihi=current_bounds(mesh_paths);set_camera((ilo+ihi)/2,ilo,ihi,28)
camera.keyframe_insert(data_path='location',frame=1);camera.keyframe_insert(data_path='rotation_euler',frame=1)
camera_data.keyframe_insert(data_path='ortho_scale',frame=1)
for s in stages:
    # Camera holds the union of the stage's source and display-offset positions;
    # the source geometry itself is not reframed or resized.
    pts=np.concatenate([mesh_world_corners[p] for p in s['mesh_source_paths']],axis=0)
    delta=np.array(s['presentation_offset_world_source_units'])
    both=np.concatenate([pts,pts+delta],axis=0)
    lo=both.min(axis=0);hi=both.max(axis=0);target=(lo+hi)/2
    set_camera(target,lo,hi,25,stage_directions.get(s['id']))
    for frame in (s['start_frame'],s['end_frame']):
        camera.keyframe_insert(data_path='location',frame=frame)
        camera.keyframe_insert(data_path='rotation_euler',frame=frame)
        camera_data.keyframe_insert(data_path='ortho_scale',frame=frame)
    marker=anim.timeline_markers.new('STAGE_'+s['id']+' '+s['title_zh'],frame=s['start_frame'])
set_camera((global_lo+global_hi)/2,global_lo,global_hi,48)
for frame in (stages[-1]['end_frame']+1,FINAL):
    camera.keyframe_insert(data_path='location',frame=frame);camera.keyframe_insert(data_path='rotation_euler',frame=frame)
    camera_data.keyframe_insert(data_path='ortho_scale',frame=frame)
for idb in (camera,camera_data):
    for fc in A.fcurves(idb):
        for k in fc.keyframe_points:k.interpolation='CONSTANT'

plan['animation_scene']=anim.name;plan['source_reference_scene']=source_scene.name
plan['pure_subtree_carrier_count']=len(pure_roots)
plan['source_geometry_shared_between_scenes']=True
plan['final_alignment_summary']={k:v for k,v in global_qc.items() if k!='objects'}
PLAN_PATH.write_text(json.dumps(plan,ensure_ascii=False,indent=2))
(WORK/'alignment-qc.json').write_text(json.dumps({'scope_zh':plan['scope_zh'],
 'final_alignment':global_qc,'stage_alignment':stage_qc},ensure_ascii=False,indent=2))

# Lightweight key-frame review only; no thousands-of-frames Cycles render.
# A separate unkeyed camera avoids the animated camera's action re-evaluating
# over the tighter review framing when Blender starts a still render.
keyed_camera=camera;keyed_camera_data=camera_data
camera_data=keyed_camera_data.copy();camera_data.name='TEMP_UNKEYED_STAGE_REVIEW_CAMERA_DATA'
camera_data.animation_data_clear()
camera=bpy.data.objects.new('TEMP_UNKEYED_STAGE_REVIEW_CAMERA',camera_data)
control_col.objects.link(camera);anim.camera=camera
review=[]
for s in stages:
    frame=s['end_frame'];activate_frame(frame,show_hidden=False)
    # For readable individual stage evidence, render only the incoming source
    # group temporarily. All objects remain in the scene and are restored.
    saved={cp:cp.hide_render for cp in clones.values()}
    group=set(s['mesh_source_paths'])
    for ob,cp in clones.items():
        if ob.type=='MESH' and ob['source_usd_path'] not in group:cp.hide_render=True
    # Fit the source group after return, with unchanged object transforms.
    bblo,bbhi=current_bounds(group);set_camera((bblo+bbhi)/2,bblo,bbhi,20,stage_directions.get(s['id']))
    anim.camera=camera
    path=PREV/(s['id']+'_stage_'+s['id']+'_returned.png')
    anim.render.filepath=str(path);bpy.ops.render.render(write_still=True,scene=anim.name)
    review.append({'stage_id':s['id'],'frame':frame,'path':str(path),
      'temporary_group_isolation_for_review':True,'source_default_visibility_respected':True,
      'camera':anim.camera.name,'ortho_scale':float(camera_data.ortho_scale)})
    for cp,v in saved.items():
        # Hidden source copies have drivers; their default remains source hidden.
        if not cp.get('source_hidden',False):cp.hide_render=v
    log('Review frame',stage=s['id'],path=str(path))

# Restore the animated camera's keyed state and every default visibility flag.
anim.camera=keyed_camera
bpy.data.objects.remove(camera,do_unlink=True)
bpy.data.cameras.remove(camera_data)
camera=keyed_camera;camera_data=keyed_camera_data
activate_frame(1,show_hidden=False)
anim.render.filepath=''
for ob,cp in clones.items():
    if not cp.get('source_hidden',False):cp.hide_render=False
source_scene['presentation_only_animation_in_other_scene']=anim.name
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
readme='''R01 原CAD视觉归位动画 / CAD VISUAL RETURN ONLY

00_Original_R01_Source_LOD1：源R01对象、原局部/世界位置和源USD显隐。
01_Visual_CAD_Return_Animation：相同1980个源对象的展示副本，688个网格与原样场景共享数据。
15段互斥分区完整覆盖688个网格，原3个隐藏网格仍默认隐藏。
Scene属性 QC_SHOW_SOURCE_HIDDEN 只临时显示动画副本中的原隐藏件。

动画仅对展示控制器和摄影机打关键帧，源对象自身局部transform不打动画。
展示控制器归零后，全部1980个源对象的local/world矩阵逐项数值一致；见alignment-qc.json。
MassVolume保留五种源定义、六实例的原占位几何，没有新造伞、绳、接口或功能件。
本文件使用完整原层级LOD1镶嵌；LOD3全细节版本另存。未把不在R01 Vehicle中的其他变体、夹具或补丁装入。

顺序是为读图安排的CAD视觉归位顺序，不是实物制造或装配操作。
未执行mates/接触/碰撞可达性/工程载荷/工作过程求解；坐标一致不能作为配合、运行或安全认证。
Workbench阶段图为清楚读图临时隔离当前源组，图后恢复全部源几何与默认显隐。
'''
txt=bpy.data.texts.new('README_视觉归位范围与证据');txt.write(readme)
for name,path in [('build_virtual_assembly.py',Path(__file__)),('assembly-stages.json',PLAN_PATH)]:
    t=bpy.data.texts.new(name);t.write(path.read_text())
bpy.context.preferences.filepaths.save_version=0
blendpath=OUT/'virtual-assembly.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blendpath),compress=True)
(WORK/'review-frames.json').write_text(json.dumps(review,ensure_ascii=False,indent=2))
(WORK/'阅读说明.md').write_text(readme)
log('Complete',blend=str(blendpath),bytes=blendpath.stat().st_size,
 stages=15,source_meshes=688,source_objects=1980,source_meshes_shared=True,
 max_local_error=global_qc['max_local_matrix_abs_error'],max_world_error=global_qc['max_world_matrix_abs_error_source_units'])
