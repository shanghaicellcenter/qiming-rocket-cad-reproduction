"""Locally combine independent visual/audio packages for noncommercial research. No TTS/network/deletion."""
from pathlib import Path
import argparse, base64, hashlib, json, re, subprocess

PATTERN=re.compile(rb'(<script id="narration-audio"[^>]*>)(.*?)(</script>)',re.S)
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(4*1024*1024):h.update(b)
    return h.hexdigest()
def run(command):
    p=subprocess.run(command,capture_output=True,text=True);assert p.returncode==0,p.stderr[-2500:];return p.stdout
def stream_hash(path,kind):return run(['ffmpeg','-nostdin','-v','error','-i',str(path),'-map',f'0:{kind}:0','-c','copy','-f','hash','-hash','sha256','-']).strip().split('=')[-1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--noncommercial-research',action='store_true');a=p.parse_args()
    assert a.noncommercial_research,'Breeze self-hosted audio/output is research/noncommercial only; this does not restrict GPL visual assets.'
    root=a.root.resolve();dest=a.destination.resolve();assert not dest.exists(),'Use a new destination to retain the verified downloaded packages untouched.'
    base=root/'outputs/启明火箭';ref=json.loads((root/'release-metadata/restoration-reference.json').read_text())
    silent=base/'media/逐步虚拟归位讲解.mp4';aac=base/'source/audio/旁白精确音轨.m4a';mp3=base/'media/逐步虚拟归位旁白.mp3';silent_html=base/'逐步虚拟归位.html'
    for p,expected in [(silent,ref['public_silent_movie_sha256']),(aac,ref['separate_audio_m4a_sha256']),(mp3,ref['separate_mp3_sha256']),(silent_html,ref['public_silent_html_sha256'])]:assert sha(p)==expected,p
    assert stream_hash(silent,'v')==ref['original_video_packet_sha256'] and stream_hash(aac,'a')==ref['original_audio_packet_sha256']
    page=silent_html.read_bytes();matches=list(PATTERN.finditer(page));assert len(matches)==1 and not matches[0].group(2)
    combined=PATTERN.sub(lambda m:m.group(1)+b'data:audio/mpeg;base64,'+base64.b64encode(mp3.read_bytes())+m.group(3),page)
    assert hashlib.sha256(combined).hexdigest()==ref['original_combined_html_sha256']
    dest.mkdir(parents=True);(dest/'media').mkdir()
    html=dest/'逐步虚拟归位.html';html.write_bytes(combined);movie=dest/'media/逐步虚拟归位讲解.mp4'
    run(['ffmpeg','-nostdin','-v','error','-i',str(silent),'-i',str(aac),'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(movie)])
    video_hash,audio_hash=stream_hash(movie,'v'),stream_hash(movie,'a')
    assert video_hash==ref['original_video_packet_sha256'] and audio_hash==ref['original_audio_packet_sha256']
    probe=json.loads(run(['ffprobe','-v','error','-count_frames','-show_entries','stream=codec_type,nb_read_frames,width,height,duration,sample_rate,channels','-of','json',str(movie)]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video');audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert int(video['nb_read_frames'])==6051 and (video['width'],video['height'])==(1280,720)
    assert int(audio['sample_rate'])==24000 and int(audio['channels'])==1
    assert abs(float(video['duration'])-201.7)<.04 and abs(float(audio['duration'])-201.7)<.05
    run(['ffmpeg','-nostdin','-v','error','-xerror','-err_detect','explode','-i',str(movie),'-f','null','-'])
    report={'scope':'Local research/noncommercial reconstruction; public GPL visual permissions remain unchanged','complete_html_original_bytes_recovered':sha(html)==ref['original_combined_html_sha256'],'video_and_audio_packet_sha256_match_prepublication_master':True,'movie_container_byte_identity_claimed':False,'video_reencoded':False,'audio_reencoded':False,'actual_frames':6051,'strict_full_decode_passed':True,'probe':probe,'html_sha256':sha(html),'movie_sha256':sha(movie),'video_packet_sha256':video_hash,'audio_packet_sha256':audio_hash,'next_required_acceptance':'Actually open the downloaded-restored HTML, test playback/seek/chapter/geometry/audio, play the MP4 and review screenshots before any cleanup. This script does not claim browser/playback acceptance.'}
    (dest/'local-restoration-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
