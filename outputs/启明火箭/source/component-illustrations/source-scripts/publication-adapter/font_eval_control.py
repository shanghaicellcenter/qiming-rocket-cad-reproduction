import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import font_safe_blender as F
import bpy
job=json.loads((Path(__file__).parent/'font-job.json').read_text());item=job['items'][0];r=Path(job['component_root'])/'review'
F.open_file(item['source_file']);before=F.snapshot_nonfont();again=F.snapshot_nonfont();F.render(r/'control-render-only.png');after=F.snapshot_nonfont();after2=F.snapshot_nonfont()
F.write(r/'render-only-control.json',{'before':before,'again':again,'after_render':after,'after_again':after2,'before_repeat_exact':before==again,'render_changed':before!=after,'after_repeat_exact':after==after2})
print('RESULT',json.dumps({'before_repeat_exact':before==again,'render_changed':before!=after,'after_repeat_exact':after==after2}))
