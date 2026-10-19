import sys,json,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent));import font_safe_blender as F
import bpy
b=Path(__file__).parent;job=json.loads((b/'font-job.json').read_text());F.open_file(job['items'][0]['source_file']);review=Path(job['component_root'])/'review'
def get():
 graph=bpy.context.evaluated_depsgraph_get();ob=bpy.data.objects['Solid unmachined bar'];ev=ob.evaluated_get(graph);m=ev.to_mesh(preserve_all_data_layers=True,depsgraph=graph)
 try:
  uv=m.uv_layers[0];legacy=np.full(len(uv.data)*2,np.nan,dtype='<f4');uv.data.foreach_get('uv',legacy);modern=np.full(len(uv.uv)*2,np.nan,dtype='<f4');uv.uv.foreach_get('vector',modern)
  return legacy.copy(),modern.copy()
 finally:ev.to_mesh_clear()
a,am=get();a2,am2=get();F.render(review/'control-uv.png');c,cm=get();d,dm=get()
def summary(x,y):
 return {'a_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'b_sha256':hashlib.sha256(y.tobytes()).hexdigest(),'exact':np.array_equal(x,y,equal_nan=True),'max_abs_difference':float(np.nanmax(np.abs(x.astype(float)-y.astype(float)))),'changed_values':int(np.count_nonzero(x!=y)),'a_nonfinite':int(np.count_nonzero(~np.isfinite(x))),'b_nonfinite':int(np.count_nonzero(~np.isfinite(y))),'a_min':float(np.nanmin(x)),'a_max':float(np.nanmax(x)),'b_min':float(np.nanmin(y)),'b_max':float(np.nanmax(y))}
result={'legacy_repeat':summary(a,a2),'modern_repeat':summary(am,am2),'legacy_across_render':summary(a,c),'modern_across_render':summary(am,cm),'legacy_modern_before':summary(a,am),'legacy_modern_after':summary(c,cm),'modern_after_repeat':summary(cm,dm)};F.write(review/'uv-api-control.json',result);print('RESULT',json.dumps(result))
