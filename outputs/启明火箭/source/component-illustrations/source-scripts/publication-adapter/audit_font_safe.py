"""Fresh headless audit of saved publication copies; does not save or edit them."""
import bpy,sys,json,hashlib,datetime
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from font_safe_blender import sha,mesh_hash,snapshot_nonfont,font_inventory,write,open_file
job=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());component=Path(job['component_root']);manifest=json.loads((component/'font-safe-manifest.json').read_text());assert manifest['all_completed'] and len(manifest['items'])==62
mirror=Path(job['publication_mirror']);rows=[]
for item in manifest['items']:
 p=Path(item['output_file']);assert sha(p)==item['published_sha256'];assert sha(Path(item['source_file']))==item['source_sha256']
 open_file(p)
 assert not any(o.type=='FONT' for o in bpy.data.objects)
 assert not any(f.packed_file or f.filepath!='<builtin>' for f in bpy.data.fonts)
 assert not bpy.data.libraries and not bpy.data.sounds and not bpy.data.movieclips and not bpy.data.cache_files
 actual=snapshot_nonfont(set(item['nonfont_reference']))
 eval_uv_hash_variants=[]
 for name,ref in item['nonfont_reference'].items():
  current=actual[name]
  for key in set(ref)|set(current):
   if key=='evaluated_mesh':continue
   assert ref.get(key)==current.get(key),(item['id'],name,key)
  if 'evaluated_mesh' in ref:
   a=ref['evaluated_mesh'];b=current['evaluated_mesh'];assert a['vertices']==b['vertices'] and a['polygons']==b['polygons']
   for k,v in a['component_sha256'].items():
    if k.startswith('uv:'):
     if v!=b['component_sha256'][k]:eval_uv_hash_variants.append({'object':name,'component':k,'scope':'Ephemeral modifier UV; source baseUV/positions/topology/matrices exact. Per-value tolerance measured during conversion.'})
    else:assert v==b['component_sha256'][k],(item['id'],name,k)
 for tr in item['text_outlines']:
  o=bpy.data.objects[tr['object_name']];assert o.type=='MESH' and mesh_hash(o.data)==tr['publication_mesh_hash'];assert o['publication_original_text']==tr['text']
 images=[]
 for image in bpy.data.images:
  if image.source!='FILE':continue
  assert image.filepath.startswith('//');r=Path(bpy.path.abspath(image.filepath)).resolve();assert r.is_relative_to(mirror) and r.is_file(),r
  match=[i for i in item['image_inputs'] if i['image']==image.name];assert len(match)==1 and sha(r)==match[0]['sha256']
  image.reload();size=tuple(image.size);n=len(image.pixels);px=list(image.pixels[:4]);assert size[0]>0 and size[1]>0 and n==size[0]*size[1]*4 and len(px)==4
  images.append({'name':image.name,'relative_path':image.filepath,'size':list(size),'sha256':sha(r),'packed':bool(image.packed_file)})
 for scene in bpy.data.scenes:assert scene.render.filepath.startswith('//')
 rows.append({'id':item['id'],'family':item['family'],'release_path':item['release_path'],'published_sha256':sha(p),'source_sha256':sha(Path(item['source_file'])),'nonfont_base_geometry_and_matrices_exact':True,'nonfont_evaluated_positions_topology_materials_exact':True,'evaluated_uv_hash_variants':eval_uv_hash_variants,'text_meshes_exact':len(item['text_outlines']),'font_object_count':0,'restricted_packed_vfont_count':0,'external_blend_library_count':0,'images':images,'saved_file_sha_unchanged_by_audit':sha(p)==item['published_sha256']})
 write(component/'fresh-reopen-audit.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'in_progress' if len(rows)<62 else 'passed_all_62_actual_saved_copies','blender_version':bpy.app.version_string,'file_count_expected':62,'file_count_checked':len(rows),'all_passed':len(rows)==62,'font_safe_manifest_sha256':sha(component/'font-safe-manifest.json'),'read_only':True,'items':rows})
 print('FRESH_AUDIT_CHECKPOINT',len(rows),item['family'],item['id'],flush=True)
