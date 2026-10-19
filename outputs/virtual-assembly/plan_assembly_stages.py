"""Partition the supplied R01 source tree for CAD visualization only.
This is not a physical assembly order, working procedure, or safety validation.
"""
from pathlib import Path
import json,hashlib
ROOT=Path('/Users/qianqiming/Documents/Codex/2026-10-19/new-chat')
WORK=ROOT/'work/virtual-assembly';WORK.mkdir(parents=True,exist_ok=True)
AUDIT=ROOT/'work/native-cad/vehicle-blender/vehicle-browse.audit.json'
data=json.loads(AUDIT.read_text());objects=data['blender_objects']
meshes={o['source_usd_path']:o for o in objects if o['type']=='MESH'}
by_path={o['source_usd_path']:o for o in objects}
name_map=json.loads((ROOT/'work/native-cad/vehicle.name-source-map.json').read_text())
sourcefiles={p:f for f,ps in name_map['file_to_prim_paths'].items() for p in ps}
def canonical(p):
    seg=p.split('/');wrapper=seg[1];seg[1]='vehicle'
    if len(seg)>2 and seg[2]==wrapper:seg[2]='vehicle'
    return '/'.join(seg)
def select(text):return sorted(o['source_usd_path'] for o in objects if o['type']=='EMPTY' and text in o.get('source_usd_display_name',''))
def one(text):
    a=select(text);assert len(a)==1,(text,a);return a[0]
def under(p,r):return p==r or p.startswith(r+'/')
def members(roots,excludes=()):return {p for p in meshes if any(under(p,r) for r in roots) and not any(under(p,r) for r in excludes)}
tank=one('Mojave Sphinx Tank Assembly-');thrust=one('Mojave Sphinx Thrust Chamber Assembly-')
valves=select('SABV-04FF Servo Actuated Ball Valve Assembly,');assert len(valves)==2
fins=select('Mojave Sphinx Fin Bracket Assembly-');assert len(fins)==4
prop=one('Mojave Sphinx Propulsion Assembly-');avbay=one('AVBY-ASSM Avbay Assembly,')
nose=one('NSCN-ASSM Nose Cone Assembly,');lower=one('20545T38-AF-LWR Airframe Tube, Lower,')
upper=one('20545T38-AF-UPR Airframe Tube, Upper,');recovery=select('Mass Volume,')
assert len(recovery)==6
specs=[
 ('01','源 Tank 子装配（独立阀实例另列）',[tank],valves,
  '按原CAD树保留该源子装配中其余既有几何的相对位置。',[-.33,0,-.02]),
 ('02','源 Thrust Chamber 子装配',[thrust],[],
  '以源项目已有子装配为一个视觉单元，展示其几何组成与原位关系。',[.24,-.16,-.28]),
 ('03','源 SABV 子装配实例 A',[valves[0]],[],
  '展示原树第一个SABV实例的既有形体和原坐标位置。',[-.40,-.10,.12]),
 ('04','源 SABV 子装配实例 B',[valves[1]],[],
  '展示原树第二个SABV实例；保持与实例A不同的原源身份。',[.40,-.10,.16]),
 ('05','源下部树其余既有节点',[prop],[tank,thrust,*fins],
  '保留该源树中未被前述独立展示单元包含的已有几何。',[0,.35,-.20]),
]
for i,p in enumerate(fins):
    offsets=[(-.30,-.24,-.16),(.30,-.24,-.16),(-.30,.24,-.16),(.30,.24,-.16)]
    specs.append((f'{i+6:02d}',f'源尾翼支架子装配 {i+1}',[p],[],
      '展示该原实例中尾翼与支架既有几何的空间关系。',list(offsets[i])))
specs.extend([
 ('10','源电子舱子装配',[avbay],[],
  '展示原电子舱内承载件与既有设备几何的空间排列。',[.42,0,.14]),
 ('11','源回收 MassVolume 占位组',recovery,[],
  '保留原项目用于空间排布的简化体积占位；五种定义共六个实例。',[-.30,0,.38]),
 ('12','源下段箭体',[lower],[],
  '展示原下段机身外壳的外形及其原位覆盖关系。',[.37,.12,-.02]),
 ('13','源上段箭体',[upper],[],
  '展示原上段机身外壳的外形及其原位覆盖关系。',[-.38,-.12,.12]),
 ('14','源鼻锥子装配',[nose],[],
  '展示源鼻锥多段形体与既有连接几何在原位的关系。',[0,0,.40]),
])
assigned=set();stages=[]
for sid,title,roots,excludes,principle,offset in specs:
    group=members(roots,excludes)
    assert group and not assigned.intersection(group),(sid,'overlapping or empty stage')
    assigned|=group
    stages.append({'id':sid,'title_zh':title,'source_subtree_paths':roots,
      'excluded_source_subtrees':excludes,'high_level_role_zh':principle,
      'presentation_offset_world_fraction_of_source_length':offset,'mesh_source_paths':sorted(group)})
remaining=set(meshes)-assigned
stages.append({'id':'15','title_zh':'源外部树其余既有节点','source_subtree_paths':[],
 'excluded_source_subtrees':[],'high_level_role_zh':'保留R01源装配中其余既有节点，完成全部网格的视觉归位。',
 'presentation_offset_world_fraction_of_source_length':[.18,-.36,.10],
 'mesh_source_paths':sorted(remaining),'selection_policy':'Exact set complement in the original R01 688 mesh occurrences'})
allpaths=[p for s in stages for p in s['mesh_source_paths']]
assert len(allpaths)==len(set(allpaths))==688 and set(allpaths)==set(meshes)
for i,s in enumerate(stages):
    s['mesh_count']=len(s['mesh_source_paths'])
    s['visible_mesh_count']=sum(not meshes[p]['source_hidden'] for p in s['mesh_source_paths'])
    s['source_hidden_mesh_count']=sum(meshes[p]['source_hidden'] for p in s['mesh_source_paths'])
    s['mesh_canonical_source_paths']=[canonical(p) for p in s['mesh_source_paths']]
    s['source_subtree_cad_files']={p:sourcefiles.get(canonical(p)) for p in s['source_subtree_paths']}
    s['source_display_names']={p:by_path[p].get('source_usd_display_name','') for p in s['source_subtree_paths']}
    s['start_frame']=49+i*144;s['move_start_frame']=s['start_frame']+24
    s['move_end_frame']=s['start_frame']+96;s['end_frame']=s['start_frame']+143
    s['start_seconds']=(s['start_frame']-1)/24;s['end_seconds']=s['end_frame']/24
    s['geometric_qc_zh']=['源网格实例路径不重不漏。','归位后逐项比较源局部矩阵和世界矩阵。',
      '保持源几何、原显隐记录与同源网格数据。']
    s['mass_volume_source_placeholder']=s['id']=='11'
result={'schema_version':1,'title_zh':'R01原CAD子装配视觉归位','scope_zh':'这是CAD视觉归位顺序；不表示实物制造、装配操作、配合约束已求解或物理可靠性。',
 'source_blend':str(ROOT/'work/native-cad/vehicle-blender/vehicle-browse.blend'),
 'source_usd':str(ROOT/'work/native-cad/vehicle-browse.usdc'),
 'source_usd_sha256':data['source_usd_sha256'],'source_meters_per_world_unit':data['usd_meters_per_unit'],
 'lod':'Upstream native CAD tessellation LOD1; complete source hierarchy and all occurrences',
 'source_mesh_count':688,'source_object_count':1980,'source_triangle_count':2864600,
 'stage_count':15,'fps':24,'frame_start':1,'frame_end':48+len(stages)*144+48,
 'partition_disjoint':True,'partition_complete':True,'source_hidden_mesh_count':3,
 'recovery_unique_definitions':5,'recovery_occurrences':6,
 'source_unreferenced_jigs_variants_or_patch_added':False,'real_mating_constraints_or_physics_solver':False,
 'presentation_path_note_zh':'展示偏移与插值只用于读图，不作为实际装配可达性或无碰撞路径的证明。',
 'stages':stages}
(WORK/'assembly-stages.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'stage_count':15,'mesh_counts':[s['mesh_count'] for s in stages],
 'sum':sum(s['mesh_count'] for s in stages),'source_hidden':[s['source_hidden_mesh_count'] for s in stages],
 'timeline_seconds':result['frame_end']/24},ensure_ascii=False))
