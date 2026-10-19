"""Read existing WAVs with the already cached independent CPU Paraformer; no TTS."""
from pathlib import Path
import os,json,time,hashlib
for key,value in {'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','MODELSCOPE_OFFLINE':'1','MS_HUB_OFFLINE':'1'}.items():os.environ[key]=value
BASE=Path(__file__).resolve().parent
MODEL=Path('/home/qianqiming/s2s/models/modelscope/hub/models/iic--speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch/snapshots/master')
IDS=['intro','stage05','stage08','stage09','stage10','stage12']
assert(MODEL/'model.pt').is_file()
def write(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x))+'\n');tmp.replace(path)
write(BASE/'results/paraformer-process.json',{'pid':os.getpid(),'status':'loading_cached_cpu_model','tts_requests':0,'shared_writer_lock_acquired':False})
print('PARAFORMER_CPU_STARTED',os.getpid(),flush=True)
import torch
torch.set_num_threads(4)
from funasr import AutoModel
model=AutoModel(model=str(MODEL),device='cpu',disable_update=True,disable_pbar=True,ncpu=4,trust_remote_code=False)
status=json.loads((BASE/'results/status.json').read_text());records={r['id']:r for r in status['clips']};output=[]
for ident in IDS:
    clip=records[ident];path=BASE/clip['wav_file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==clip['wav_sha256']
    started=time.monotonic();raw=model.generate(input=str(path),disable_pbar=True)
    row={'id':ident,'input_wav_sha256':clip['wav_sha256'],'engine':'FunASR offline Paraformer','device':'cpu','expected_text_supplied':False,'hotword_supplied':False,'raw_result':raw,'transcript':' '.join(x.get('text','') for x in raw),'elapsed_seconds':time.monotonic()-started}
    output.append(row);write(BASE/'results/paraformer-crosscheck.json',output)
    print('PARAFORMER_REVIEW',ident,row['transcript'],flush=True)
write(BASE/'results/paraformer-process.json',{'pid':os.getpid(),'status':'complete6','tts_requests':0,'shared_writer_lock_acquired':False})
