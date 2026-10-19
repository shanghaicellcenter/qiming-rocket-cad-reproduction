"""Re-render the final offline Machine page with its actual speech timeline.
Uses delivered geometry/audio; does not contact a TTS service or change voice speed.
"""
from pathlib import Path
import argparse,os,subprocess,json,hashlib,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'media/逐步虚拟归位讲解-rebuilt.mp4')
args=parser.parse_args()
for module in [HERE/'node_modules/playwright/index.mjs',HERE.parent/'node_modules/playwright/index.mjs']:
 if module.is_file():
  os.environ.setdefault('MACHINE_PLAYWRIGHT_MODULE',module.as_uri());break
NODE=os.environ.get('MACHINE_NODE') or shutil.which('node')
assert NODE,'Node.js18+ required; set MACHINE_NODE if it is not on PATH.'
PAGE=ROOT/'逐步虚拟归位.html';WAV=ROOT/'media/逐步虚拟归位旁白.wav';ASS=HERE/'captions.ass'
RECORDER=HERE.parent/'vendor/machine/scripts/record.mjs'
TIMELINE=json.loads((HERE/'final-timeline.json').read_text());FPS=TIMELINE['fps']
for file in [PAGE,WAV,ASS,RECORDER]:assert file.is_file(),file
CACHE=HERE/'render-work';CACHE.mkdir(exist_ok=True)
sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
runtime_sources=[RECORDER,*sorted((RECORDER.parent/'lib').rglob('*.mjs')),*sorted((RECORDER.parent.parent/'kit').rglob('*.js'))]
identity={str(p.relative_to(ROOT)):sha(p) for p in [PAGE,WAV,ASS,HERE/'final-timeline.json',*runtime_sources]}
state_file=CACHE/'state.json';previous=json.loads(state_file.read_text()) if state_file.exists() else {}
reuse=previous.get('inputs')==identity
previous_clips={row['id']:row for row in previous.get('clips',[])}
rows=[]
def run(command):
 result=subprocess.run(command,cwd=ROOT);assert result.returncode==0,command

def video_ok(file,frames):
 if not file.is_file():return False
 result=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,width,height','-of','json',str(file)],capture_output=True,text=True)
 if result.returncode:return False
 try:
  stream=json.loads(result.stdout)['streams'][0]
  return int(stream['nb_read_frames'])==frames and stream['width']==1280 and stream['height']==720
 except (KeyError,IndexError,ValueError):return False

for clip in TIMELINE['clips']:
 destination=CACHE/(clip['id']+'.mp4');frames=clip['frames'];first=round(clip['start']*FPS)
 old=previous_clips.get(clip['id'])
 cache_ok=reuse and old is not None and destination.is_file() and sha(destination)==old.get('sha256') and video_ok(destination,frames)
 if not cache_ok:
  run([NODE,str(RECORDER),str(PAGE),str(destination),'--w','1280','--h','720','--ss','1','--fps',str(FPS),'--from',str(first/FPS),'--to',str((first+frames)/FPS)])
 assert video_ok(destination,frames),('Captured frame count mismatch',clip['id'])
 rows.append({'id':clip['id'],'path':str(destination),'frames':frames,'sha256':sha(destination)})
 state_file.write_text(json.dumps({'inputs':identity,'clips':rows},ensure_ascii=False,indent=2)+'\n')
listing=CACHE/'concat.txt';listing.write_text(''.join("file '"+r['path']+"'\n" for r in rows))
output=args.output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-i',str(WAV),'-map','0:v:0','-map','1:a:0','-vf','ass='+str(ASS),'-r',str(FPS),'-fps_mode','cfr','-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p','-video_track_timescale','15360','-c:a','aac','-b:a','192k','-t',str(TIMELINE['duration']),'-movflags','+faststart',str(output)])
assert video_ok(output,TIMELINE['frames'])
run(['ffmpeg','-v','error','-xerror','-err_detect','explode','-i',str(output),'-f','null','-'])
print(json.dumps({'movie':str(output),'sha256':sha(output),'frames':TIMELINE['frames'],'audio_speed_changed':False},ensure_ascii=False))
