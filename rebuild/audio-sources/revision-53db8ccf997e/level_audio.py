"""Pilot-matched2:1 compression and per-paragraph static gain, preserving sample count."""
from pathlib import Path
import hashlib,json,math,re,subprocess,wave
import numpy as np

BASE=Path(__file__).resolve().parent
RAW=BASE/'raw-archive'
FFMPEG='/opt/homebrew/bin/ffmpeg'
CONTRACT=json.loads((BASE/'pilot-leveling-contract.json').read_text())
FILTER=CONTRACT['processing']['filter']
TARGET=CONTRACT['pilot_after']['voicedWindowRmsMedianDbfs']
CEILING=-2.1

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def read_wav(path):
    with wave.open(str(path),'rb') as f:
        assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(24000,1,2)
        n=f.getnframes();b=f.readframes(n);assert len(b)==n*2
    return np.frombuffer(b,dtype='<i2').copy(),n
def merged(words):
    result=[]
    for w in words:
        a,b=w['start'],w['end'];assert a is not None and b is not None and b>=a
        if result and a<=result[-1][1]:result[-1][1]=max(b,result[-1][1])
        else:result.append([a,b])
    return result
def stats(samples,intervals):
    spans=[];all_windows=[]
    for start in range(0,len(samples)-4800+1,2400):
        a,b=start/24000,(start+4800)/24000
        coverage=sum(max(0,min(b,y)-max(a,x)) for x,y in intervals)/.2
        rms=20*math.log10(max(float(np.sqrt(np.mean(samples[start:start+4800]**2))),1e-12))
        if coverage>=.7:spans.append(rms)
        all_windows.append({'start':a,'end':b,'asr_speech_fraction':coverage,'voiced':coverage>=.7,'rms_dbfs':rms})
    assert spans
    p10,median,p95=np.percentile(spans,[10,50,95]).tolist()
    return {'peak_dbfs':20*math.log10(max(float(np.max(np.abs(samples))),1e-12)),'full_track_rms_dbfs':20*math.log10(max(float(np.sqrt(np.mean(samples**2))),1e-12)),'voiced_window_rms_p10_dbfs':p10,'voiced_window_rms_median_dbfs':median,'voiced_window_rms_p95_dbfs':p95,'voiced_p95_minus_p10_db':p95-p10,'voiced_windows':len(spans),'window_curve':all_windows}
def measure(path=None,floats=None):
    args=[FFMPEG,'-nostdin','-hide_banner','-loglevel','info']
    if path:args+=['-i',str(path)];data=None
    else:args+=['-f','f64le','-ar','24000','-ac','1','-i','pipe:0'];data=np.asarray(floats,dtype='<f8').tobytes()
    args+=['-af','ebur128=peak=true:framelog=verbose','-f','null','-']
    p=subprocess.run(args,input=data,capture_output=True,check=True)
    text=p.stderr.decode();tail=text[text.rfind('Summary:'):]
    loud=float(re.search(r'Integrated loudness:\s+I:\s+(-?[\d.]+)',tail)[1]);tp=float(re.search(r'True peak:\s+Peak:\s+(-?[\d.]+)',tail)[1])
    return {'integrated_lufs':loud,'true_peak_dbtp':tp},text

def main():
    bundle=json.loads((BASE/'clips.json').read_text());status=json.loads((RAW/'results/status.json').read_text())
    assert status['engine']=='Breeze2' and status['source_narration_sha256']==bundle['source_narration_sha256']
    original={x['id']:x for x in status['clips']};outdir=BASE/'leveled'/bundle['source_narration_sha256'][:12];outdir.mkdir(parents=True,exist_ok=True)
    report={'engine':'Breeze2','source_narration_sha256':bundle['source_narration_sha256'],'reference_sha256':bundle['reference_sha256'],'compressor_filter':FILTER,'target_voiced_window_median_dbfs':TARGET,'target_basis':'Actual accepted pilot200ms windows/100ms hop, Whisper speech coverage>=70%; natural pauses are not boosted to compensate whole-file RMS','true_peak_ceiling_dbtp':CEILING,'no_pitch_shift':True,'no_time_stretch':True,'no_resampling':True,'no_sentence_concatenation':True,'no_second_loudnorm':True,'eligible_for_final_movie':False,'tracks':[],'waiting_for_asr':[]}
    for clip in bundle['clips']:
        if clip['id'] not in original:continue
        row=original[clip['id']];path=RAW/row['wav_file'];assert sha(path)==row['wav_sha256']
        asrpath=path.with_suffix('.asr.json');alignpath=path.with_suffix('.sentence-alignment.json')
        if not asrpath.exists():report['waiting_for_asr'].append(clip['id']);continue
        asr=json.loads(asrpath.read_text());assert asr['input_wav_sha256']==row['wav_sha256']
        audio,n=read_wav(path);source=audio.astype(np.float64)/32768;intervals=merged(asr['words'])
        rawstats=stats(source,intervals)
        cmd=[FFMPEG,'-nostdin','-hide_banner','-loglevel','error','-i',str(path),'-af',FILTER,'-f','f64le','pipe:1']
        completed=subprocess.run(cmd,capture_output=True,check=True);compressed=np.frombuffer(completed.stdout,dtype='<f8').copy();assert len(compressed)==n
        compstats=stats(compressed,intervals);compmeasure,complog=measure(floats=compressed)
        requested=TARGET-compstats['voiced_window_rms_median_dbfs'];gain=min(requested,CEILING-compmeasure['true_peak_dbtp'])
        processed=compressed*10**(gain/20);scaled=np.rint(processed*32768);assert np.max(scaled)<32767 and np.min(scaled)>-32768
        samples=scaled.astype('<i2');output=outdir/(clip['id']+'.wav')
        with wave.open(str(output),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(samples.tobytes())
        verified,n2=read_wav(output);assert n2==n and np.array_equal(verified,samples)
        assert np.all(samples[audio==0]==0), 'Original exact digital zeros must remain zero'
        finalstats=stats(samples.astype(np.float64)/32768,intervals);finalmeasure,finallog=measure(path=output)
        (outdir/(clip['id']+'.ebur128.log')).write_text(finallog)
        align=json.loads(alignpath.read_text());assert align['text_sha256']==clip['text_sha256']
        record={'id':clip['id'],'text':clip['text'],'text_sha256':clip['text_sha256'],'engine':'Breeze2','raw_wav_path':str(path),'raw_wav_sha256':row['wav_sha256'],'wav_path':str(output),'wav_sha256':sha(output),'pcm_sha256':hashlib.sha256(samples.tobytes()).hexdigest(),'duration_seconds':n/24000,'sample_rate':24000,'channels':1,'sample_width':2,'frames':n,'raw_frames':n,'frame_count_unchanged':True,'source_digital_zeros_remain_zero':True,'full_scale_samples':int(np.count_nonzero((samples==-32768)|(samples==32767))),'requested_constant_gain_db':requested,'applied_constant_gain_db':gain,'gain_limited_by_true_peak':gain<requested-1e-8,'target_voiced_median_dbfs':TARGET,'before':rawstats,'after_compressor':compstats,'after':finalstats,'final_loudness':finalmeasure,'asr_json_path':str(asrpath),'asr_json_sha256':sha(asrpath),'asr_device':asr['device'],'asr_dtype':asr.get('dtype','torch.float32 configured in original CPU runner'),'asr_words':asr['words'],'subtitle_sentences':[{'start':x['start'],'end':x['end'],'target_text':x['target_text'],'timing_basis':x['timing_basis']} for x in align['sentences']],'eligible_for_final_movie':False,'content_review_status':'pending independent fulltext/homophone and pronunciation ambiguity review'}
        report['tracks'].append(record);write(BASE/'leveling-audit.json',report)
        print(json.dumps({'id':clip['id'],'gain_db':round(gain,3),'voiced_median_dbfs':round(finalstats['voiced_window_rms_median_dbfs'],3),**finalmeasure,'frames_unchanged':n==n2}),flush=True)
    report['all_requested_processed']=len(report['tracks'])==len(original);write(BASE/'leveling-audit.json',report)

if __name__=='__main__':main()
