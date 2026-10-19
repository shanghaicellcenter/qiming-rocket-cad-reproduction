"""Read-only, saved-file QA for the source-only CAD visual-return animation.

This verifies representation/coordinates, not mechanical mates or safety.
The .blend is reopened, inspected and sampled without saving modifications.
"""
import bpy,json,hashlib
from pathlib import Path
import numpy as np

ROOT=Path('/Users/qianqiming/Documents/Codex/2026-10-19/new-chat')
WORK=ROOT/'work/virtual-assembly'
DELIVERY=ROOT/'outputs/virtual-assembly'
BLEND=DELIVERY/'virtual-assembly.blend'
if not BLEND.exists():BLEND=WORK/'virtual-assembly.blend'
plan=json.loads((WORK/'assembly-stages.json').read_text())
original_qc=json.loads((WORK/'alignment-qc.json').read_text())
baseline={r['source_usd_path']:r for r in original_qc['final_alignment']['objects']}
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
reference=bpy.data.scenes[plan['source_reference_scene']]
animation=bpy.data.scenes[plan['animation_scene']]
refs={o['source_usd_path']:o for o in reference.objects if o.get('source_usd_path')}
copies={o['source_usd_path']:o for o in animation.objects if o.get('source_usd_path')}
assert set(refs)==set(copies)==set(baseline)
assert len(refs)==1980
assert sum(o.type=='MESH' for o in refs.values())==688
assert all(copies[p].data is o.data for p,o in refs.items() if o.type=='MESH')
assert all(not(o.animation_data and o.animation_data.action) for o in copies.values())
assert sum(len(o.data.polygons) for o in refs.values() if o.type=='MESH')==2864600

by_stage={s['id']:s for s in plan['stages']}
pure_roots=[(r,s['id']) for s in plan['stages'] for r in s['maximal_pure_source_roots']]
object_stage={}
for p in refs:
    matches=[sid for r,sid in pure_roots if p==r or p.startswith(r+'/')]
    assert len(matches)<=1,(p,matches)
    object_stage[p]=matches[0] if matches else None
assert all(object_stage[p] is not None for p,o in refs.items() if o.type=='MESH')

def activate(frame,show_hidden=True):
    bpy.context.window.scene=animation
    animation['QC_SHOW_SOURCE_HIDDEN']=show_hidden
    animation.update_tag()
    animation.frame_set(frame)
    bpy.context.view_layer.update()

max_by_object={p:{'source_usd_path':p,'stage_id':object_stage[p],
    'source_type':o.type,'max_local_matrix_abs_error':0.,
    'max_basis_matrix_abs_error':0.,'max_parent_inverse_matrix_abs_error':0.,
    'max_expected_translated_world_matrix_abs_error':0.,
    'max_world_linear_part_abs_error':0.} for p,o in refs.items()}
frames=sorted(set([1,plan['frame_end']]+
    [(s['move_start_frame']+s['move_end_frame'])//2 for s in plan['stages']]))
samples=[]
for frame in frames:
    activate(frame)
    offsets={sid:np.asarray(animation.objects[s['controller_name']].location,dtype=float)
        for sid,s in by_stage.items()}
    max_local=max_world=max_linear=max_basis=max_parent_inverse=0.
    exact_local=True
    for p,cp in copies.items():
        b=baseline[p]
        local=np.asarray(cp.matrix_local,dtype=float)
        world=np.asarray(cp.matrix_world,dtype=float)
        original_local=np.asarray(b['local_matrix_source'],dtype=float)
        expected=np.asarray(b['world_matrix_source'],dtype=float)
        sid=object_stage[p]
        if sid:expected[:3,3]+=offsets[sid]
        le=float(np.max(np.abs(local-original_local)))
        be=float(np.max(np.abs(np.asarray(cp.matrix_basis,dtype=float)-np.asarray(refs[p].matrix_basis,dtype=float))))
        pe=float(np.max(np.abs(np.asarray(cp.matrix_parent_inverse,dtype=float)-np.asarray(refs[p].matrix_parent_inverse,dtype=float))))
        we=float(np.max(np.abs(world-expected)))
        ne=float(np.max(np.abs(world[:3,:3]-expected[:3,:3])))
        exact_local &= bool(np.array_equal(local,original_local))
        max_local=max(max_local,le);max_world=max(max_world,we);max_linear=max(max_linear,ne)
        max_basis=max(max_basis,be);max_parent_inverse=max(max_parent_inverse,pe)
        row=max_by_object[p]
        row['max_local_matrix_abs_error']=max(row['max_local_matrix_abs_error'],le)
        row['max_basis_matrix_abs_error']=max(row['max_basis_matrix_abs_error'],be)
        row['max_parent_inverse_matrix_abs_error']=max(row['max_parent_inverse_matrix_abs_error'],pe)
        row['max_expected_translated_world_matrix_abs_error']=max(row['max_expected_translated_world_matrix_abs_error'],we)
        row['max_world_linear_part_abs_error']=max(row['max_world_linear_part_abs_error'],ne)
    samples.append({'frame':frame,'all_1980_local_matrices_numerically_exact':exact_local,
        'max_local_matrix_abs_error':max_local,
        'max_basis_matrix_abs_error':max_basis,'max_parent_inverse_matrix_abs_error':max_parent_inverse,
        'max_expected_translated_world_matrix_abs_error':max_world,
        'max_world_linear_part_abs_error':max_linear,
        'stage_controller_offsets':{sid:v.tolist() for sid,v in offsets.items()}})

(WORK/'motion-qc-debug.json').write_text(json.dumps({'samples':samples,
    'nonzero_objects':[v for v in max_by_object.values() if v['max_local_matrix_abs_error'] or v['max_world_linear_part_abs_error']]},indent=2))
assert all(s['max_basis_matrix_abs_error']==0 and s['max_parent_inverse_matrix_abs_error']==0 for s in samples)
assert samples[-1]['all_1980_local_matrices_numerically_exact']
assert all(s['max_world_linear_part_abs_error']==0 for s in samples)
assert samples[-1]['max_expected_translated_world_matrix_abs_error']==0
float_bound=64*np.finfo(np.float32).eps*107.258751
assert max(s['max_expected_translated_world_matrix_abs_error'] for s in samples)<float_bound

activate(plan['frame_end'],show_hidden=False)
source_visibility_ok=all(bool(o.hide_render)==bool(o.get('source_hidden',False)) for o in refs.values())
animation_visibility_ok=all(bool(o.hide_render)==bool(o.get('source_hidden',False)) for o in copies.values())
assert source_visibility_ok and animation_visibility_ok
assert sum(o.type=='MESH' and o.hide_render for o in refs.values())==3
assert sum(o.type=='MESH' and o.hide_render for o in copies.values())==3

reopen_dir=WORK/'reopened-animation-review'
reopen_dir.mkdir(exist_ok=True)
review_samples=[('01_start_separated',1),
    ('02_stage_01_moving',(by_stage['01']['move_start_frame']+by_stage['01']['move_end_frame'])//2),
    ('03_stage_02_moving',(by_stage['02']['move_start_frame']+by_stage['02']['move_end_frame'])//2),
    ('04_stage_06_moving',(by_stage['06']['move_start_frame']+by_stage['06']['move_end_frame'])//2),
    ('05_stage_10_moving',(by_stage['10']['move_start_frame']+by_stage['10']['move_end_frame'])//2),
    ('06_stage_14_moving',(by_stage['14']['move_start_frame']+by_stage['14']['move_end_frame'])//2),
    ('07_final_original_positions',plan['frame_end'])]
rendered=[]
for name,frame in review_samples:
    activate(frame,show_hidden=False)
    path=reopen_dir/(name+'.png')
    animation.render.filepath=str(path)
    bpy.ops.render.render(write_still=True,scene=animation.name)
    rendered.append({'name':name,'frame':frame,'path':str(path),
        'all_source_objects_present':True,'default_source_visibility':True})

summary={'saved_blend':str(BLEND),'saved_blend_sha256':hashlib.sha256(BLEND.read_bytes()).hexdigest(),
    'blender_version':bpy.app.version_string,'read_only_reopen_no_save':True,
    'source_objects_per_scene':1980,'source_mesh_occurrences_per_scene':688,
    'source_triangles_per_scene':2864600,'shared_mesh_datablocks':688,
    'stage_count':15,'frames':plan['frame_end'],'fps':24,
    'sampled_motion_frames':len(samples),
    'source_reference_visibility_matches_usd':source_visibility_ok,
    'animated_default_visibility_matches_usd':animation_visibility_ok,
    'hidden_mesh_occurrences_per_scene':3,
    'source_basis_and_parent_inverse_matrices_exact_at_all_sampled_frames':True,
    'final_local_matrices_numerically_exact':True,
    'max_intermediate_computed_local_matrix_abs_error':max(s['max_local_matrix_abs_error'] for s in samples),
    'intermediate_local_matrix_note':'Blender recomputes Object.matrix_local against moved presentation parents. Intermediate floating-point differences are in heterogeneous source local coordinate frames, not a manufacturing tolerance; source basis/parent-inverse matrices remain exact and final local/world matrices are exact.',
    'world_linear_parts_exact_at_all_sampled_frames':True,
    'max_expected_translated_world_matrix_abs_error':max(s['max_expected_translated_world_matrix_abs_error'] for s in samples),
    'final_local_world_matrix_error':0.,
    'floating_point_numerical_acceptance_bound':float(float_bound),
    'bound_is_manufacturing_tolerance':False,
    'scope':'Source geometry presentation only; no mates, contact, accessibility, load, pressure, ignition, operation or safety solver.',
    'samples':samples,'objects':list(max_by_object.values()),'rendered_samples':rendered}
(WORK/'saved-file-motion-qc.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print('SAVED_FILE_QC='+json.dumps({k:v for k,v in summary.items() if k not in ('samples','objects','rendered_samples')},ensure_ascii=False),flush=True)
