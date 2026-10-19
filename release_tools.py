"""Prepare local publication layers only. No GitHub writes, upload or deletion."""
from pathlib import Path, PurePosixPath
import argparse, base64, datetime, hashlib, io, json, os, re, shutil, subprocess, tarfile

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[1]
PROJECT = 'outputs/启明火箭'
VIRTUAL = 'outputs/virtual-assembly'
MOVIE = PROJECT + '/media/逐步虚拟归位讲解.mp4'
FILM_HTML = PROJECT + '/逐步虚拟归位.html'
SOURCE_AUDIO = PROJECT + '/source/audio/'
COMPONENT = PROJECT + '/source/component-illustrations'
AUDIO_PATTERN = re.compile(rb'(<script id="narration-audio"[^>]*>)(.*?)(</script>)', re.S)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while data := f.read(4*1024*1024): h.update(data)
    return h.hexdigest()

def write(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    tmp.replace(path)

def run(command):
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-2500:])
    return p.stdout

def probe(path):
    return json.loads(run(['ffprobe','-v','error','-count_frames','-show_entries','stream=codec_type,codec_name,nb_read_frames,width,height,duration,sample_rate,channels','-of','json',str(path)]))

def stream_hash(path, kind):
    return run(['ffmpeg','-nostdin','-v','error','-i',str(path),'-map',f'0:{kind}:0','-c','copy','-f','hash','-hash','sha256','-']).strip().split('=')[-1]

def bind_master_reference(root):
    ref=json.loads((HERE/'derived/restoration-reference.json').read_text())
    for relative,key in [(MOVIE,'original_movie_sha256'),(FILM_HTML,'original_combined_html_sha256'),(PROJECT+'/media/逐步虚拟归位旁白.mp3','separate_mp3_sha256')]:
        assert sha(root/relative)==ref[key],('Master changed since derive; rerun derive before freezing/packing',relative)
    for path,key in [(HERE/'derived/逐步虚拟归位讲解.mp4','public_silent_movie_sha256'),(HERE/'derived/逐步虚拟归位.html','public_silent_html_sha256'),(HERE/'derived/旁白精确音轨.m4a','separate_audio_m4a_sha256')]:
        assert sha(path)==ref[key],('Derived publication artifact changed',str(path))

def derive(root):
    out = HERE/'derived'; out.mkdir(exist_ok=True)
    original = root/MOVIE; original_html = root/FILM_HTML
    silent = out/'逐步虚拟归位讲解.mp4'; audio = out/'旁白精确音轨.m4a'; html = out/'逐步虚拟归位.html'
    reference = probe(original); video = next(s for s in reference['streams'] if s['codec_type']=='video')
    assert int(video['nb_read_frames']) == 6051 and (video['width'],video['height']) == (1280,720)
    before_sha = sha(original)
    run(['ffmpeg','-nostdin','-y','-v','error','-i',str(original),'-map','0:v:0','-c:v','copy','-an','-movflags','+faststart',str(silent)])
    run(['ffmpeg','-nostdin','-y','-v','error','-i',str(original),'-map','0:a:0','-c:a','copy','-vn','-movflags','+faststart',str(audio)])
    new = probe(silent)
    assert len(new['streams'])==1 and new['streams'][0]['codec_type']=='video'
    assert int(new['streams'][0]['nb_read_frames'])==int(video['nb_read_frames'])
    vh, ah = stream_hash(original,'v'), stream_hash(original,'a')
    assert stream_hash(silent,'v')==vh and stream_hash(audio,'a')==ah
    page = original_html.read_bytes(); matches = list(AUDIO_PATTERN.finditer(page)); assert len(matches)==1
    mp3 = root/PROJECT/'media/逐步虚拟归位旁白.mp3'
    expected = b'data:audio/mpeg;base64,'+base64.b64encode(mp3.read_bytes())
    assert matches[0].group(2)==expected, 'Current HTML does not contain the delivered MP3'
    stripped = AUDIO_PATTERN.sub(lambda m:m.group(1)+m.group(3),page)
    assert b'data:audio/' not in stripped and len(AUDIO_PATTERN.findall(stripped))==1
    html.write_bytes(stripped)
    assert AUDIO_PATTERN.sub(lambda m:m.group(1)+expected+m.group(3),stripped)==page
    run(['ffmpeg','-nostdin','-v','error','-xerror','-err_detect','explode','-i',str(silent),'-f','null','-'])
    assert sha(original)==before_sha
    record = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_movie_sha256':before_sha,'original_movie_probe':reference,'original_video_packet_sha256':vh,'original_audio_packet_sha256':ah,'public_silent_movie_sha256':sha(silent),'public_silent_movie_probe':new,'separate_audio_m4a_sha256':sha(audio),'original_combined_html_sha256':sha(original_html),'public_silent_html_sha256':sha(html),'separate_mp3_sha256':sha(mp3),'html_byte_exact_recovery_from_delivered_mp3_proven_in_memory':True,'video_no_reencode':True,'audio_no_reencode':True,'original_source_unmodified':True,'silent_full_decode_passed':True}
    builder=root/PROJECT/'source/assembly-film/build.mjs'
    code=builder.read_text();lines=code.splitlines();needle=[line for line in lines if line.startswith("await w('<script id=\"narration-audio\"")]
    assert len(needle)==1
    replacement="const voicePath=resolve(root,'media/逐步虚拟归位旁白.mp3'),voicePayload=!process.argv.includes('--silent')&&existsSync(voicePath)?'data:audio/mpeg;base64,'+readFileSync(voicePath).toString('base64'):'';\nawait w('<script id=\"narration-audio\" type=\"application/octet-stream\">'+voicePayload+'</script>');"
    (out/'assembly-film-build.mjs').write_text(code.replace(needle[0],replacement))
    record['visual_builder_adaptation']='Copied source can build without the independent audio package; --silent explicitly omits audio. Original builder archived separately.'
    write(out/'restoration-reference.json',record)
    print(json.dumps(record,ensure_ascii=False))

def inventory(root,final_freeze=False):
    if final_freeze:bind_master_reference(root)
    component_root=HERE/'derived/public-tree'/COMPONENT
    font_manifest=json.loads((component_root/'font-safe-manifest.json').read_text())
    font_audit=json.loads((component_root/'fresh-reopen-audit.json').read_text())
    assert font_manifest['all_completed'] and font_manifest['actual_completed_count']==62
    assert font_audit['all_passed'] and font_audit['file_count_checked']==62
    assert font_audit['font_safe_manifest_sha256']==sha(component_root/'font-safe-manifest.json')
    rows=[]; links=[];original_paths=set()
    for relative_root in [PROJECT,VIRTUAL]:
        for p in sorted((root/relative_root).rglob('*')):
            rel=p.relative_to(root).as_posix()
            if p.is_symlink():
                target=p.resolve(); assert target.is_relative_to(root/PROJECT) or target.is_relative_to(root/VIRTUAL), ('External symlink',rel)
                assert target.exists(), ('Broken symlink',rel)
                links.append({'path':rel,'target':os.path.relpath(target,p.parent),'original_link':os.readlink(p)})
                continue
            if not p.is_file():continue
            original_paths.add(rel)
            category='visual'
            replacement=None
            if rel.startswith(SOURCE_AUDIO) or (p.suffix.lower() in {'.wav','.mp3','.m4a','.pcm','.flac','.ogg'}):category='audio-noncommercial'
            if rel in [MOVIE,FILM_HTML]:
                replacement=str(HERE/'derived'/p.name)
                assert Path(replacement).is_file(), 'Run derive first'
            if rel==PROJECT+'/source/assembly-film/build.mjs':
                replacement=str(HERE/'derived/assembly-film-build.mjs')
            selected=Path(replacement) if replacement else p
            rows.append({'path':rel,'bytes':selected.stat().st_size,'sha256':sha(selected),'layer':category,'input_file':str(selected),'original_sha256':sha(p) if replacement else None,'public_replacement':bool(replacement)})
    # Independent exact audio track extracted from the final movie, only in NC layer.
    for relative,actual,layer in [
        (PROJECT+'/source/audio/旁白精确音轨.m4a',HERE/'derived/旁白精确音轨.m4a','audio-noncommercial'),
        (PROJECT+'/source/audio/reference.wav',HERE/'derived/reference.wav','audio-noncommercial'),
        (PROJECT+'/source/audio/reference-manifest.json',HERE/'derived/reference-manifest.json','audio-noncommercial'),
        ('release-metadata/restoration-reference.json',HERE/'derived/restoration-reference.json','visual'),
        (PROJECT+'/source/assembly-film/build-original-with-audio.mjs',root/PROJECT/'source/assembly-film/build.mjs','visual'),
    ]:
        assert actual.is_file()
        existing=next((r for r in rows if r['path']==relative),None)
        if existing:
            assert existing['sha256']==sha(actual),('Conflicting publication input',relative)
            continue
        rows.append({'path':relative,'bytes':actual.stat().st_size,'sha256':sha(actual),'layer':layer,'input_file':str(actual),'original_sha256':None,'public_replacement':True})
    # These publication-only illustration copies replace FONT objects with
    # evaluated glyph geometry. Raw partner Blend/font binaries are not inputs.
    font_originals={r['release_path']:r['source_sha256'] for r in font_manifest['items']}
    for actual in sorted(component_root.rglob('*')):
        if not actual.is_file():continue
        assert not actual.is_symlink() and not actual.name.endswith(('.blend1','.blend2','.tmp'))
        assert actual.suffix.lower() not in {'.ttf','.ttc','.otf','.woff','.woff2'}
        relative=COMPONENT+'/'+actual.relative_to(component_root).as_posix()
        existing=next((r for r in rows if r['path']==relative),None)
        if existing:
            assert existing['sha256']==sha(actual),('Final local component copy differs',relative)
            if relative in font_originals:
                existing['original_sha256']=font_originals[relative];existing['public_replacement']=True
            continue
        rows.append({'path':relative,'bytes':actual.stat().st_size,'sha256':sha(actual),'layer':'visual','input_file':str(actual),'original_sha256':font_originals.get(relative),'public_replacement':True})
    if final_freeze:
        for item in font_manifest['items']:
            assert sha(root/item['release_path'])==item['published_sha256'],('Required editable illustration missing from actual local delivery',item['release_path'])
    source_manifest=json.loads((root/PROJECT/'source/original-project-manifest.json').read_text())
    source_checks=[]
    for r in source_manifest['files']:
        p=root/PROJECT/'source/original-project'/r['relative_path']; assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
        source_checks.append(r['relative_path'])
    assert len(source_checks)==392
    if final_freeze:
        current_paths={p.relative_to(root).as_posix() for base in [root/PROJECT,root/VIRTUAL] for p in base.rglob('*') if p.is_file() and not p.is_symlink()}
        assert current_paths==original_paths,'Public tree file set changed during freeze inventory'
        for r in rows:
            p=Path(r['input_file']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],('Public input changed during freeze',r['path'])
    transforms={'policy':'Only publication copies changed. Historical original hashes retained; release-manifest contains actual public bytes. Source CAD392 and native CAD/assembly Blend/GLB geometry are unchanged. The62 separate illustration copies contain evaluated text outlines and relocated image references; raw and published Blend hashes are recorded separately.',
                'files':[{'path':r['path'],'original_sha256':r['original_sha256'],'published_sha256':r['sha256'],'published_bytes':r['bytes']} for r in rows if r.get('original_sha256')]}
    transform_path=HERE/'publication-transformations.json';write(transform_path,transforms)
    rows.append({'path':'release-metadata/publication-transformations.json','bytes':transform_path.stat().st_size,'sha256':sha(transform_path),'layer':'visual','input_file':str(transform_path),'original_sha256':None,'public_replacement':True})
    data={'schema_version':1,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workspace':str(root),'status':'final_frozen_local_snapshot' if final_freeze else 'local_prepublication_snapshot; rerun after final freeze','full_public_tree_count':len(rows),'full_logical_bytes':sum(r['bytes'] for r in rows),'original_392_file_snapshot_verified':True,'original_snapshot_count':392,'layers':{layer:{'files':sum(r['layer']==layer for r in rows),'bytes':sum(r['bytes'] for r in rows if r['layer']==layer)} for layer in ['visual','audio-noncommercial']},'no_combined_Breeze_HTML_or_MP4_in_public_layers':True,'symlinks':links,'files':rows}
    write(HERE/'inventory.private.json',data)
    public={k:v for k,v in data.items() if k!='workspace'}
    public['files']=[{k:v for k,v in r.items() if k!='input_file'} for r in rows]
    write(HERE/'release-manifest.json',public)
    print(json.dumps({k:v for k,v in public.items() if k not in ['files','symlinks']},ensure_ascii=False))

def stage(root):
    inv=json.loads((HERE/'inventory.private.json').read_text())
    assert inv['status']=='final_frozen_local_snapshot','A fresh accepted final freeze is required; superseded inventories cannot be staged'
    repo=HERE/'repo-stage'
    # Retain the previous local staging snapshot, then build a fresh tree so
    # removed/renamed inputs cannot silently survive into a later publication.
    if repo.exists():
        assert not (repo/'.git').exists(),'Refuse to replace a Git-initialized publication checkout'
        history=HERE/'staging-history'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        history.parent.mkdir(exist_ok=True);repo.rename(history)
    repo.mkdir()
    # Repository holds small editable text sources; all real geometry, original
    # source snapshots, media, large audit JSONs and preview images stay Release assets.
    suffixes={'.py','.mjs','.js','.md','.json','.css','.csv','.txt','.srt','.ass','.sh'}
    total=0; copied=[]
    for r in inv['files']:
        rel=r['path'];p=Path(r['input_file'])
        if r['layer']!='visual' or r['bytes']>2*1024**2:continue
        eligible=(rel.startswith(PROJECT+'/source/') and not rel.startswith(PROJECT+'/source/original-project/')) or (rel.startswith(VIRTUAL+'/') and len(PurePosixPath(rel).parts)==3)
        if not eligible or (p.suffix.lower() not in suffixes and p.name!='LICENSE'):continue
        assert sha(p)==r['sha256'],('Input changed after inventory',rel)
        if p.name.startswith('.env') or p.suffix in {'.pem','.key'}:raise RuntimeError('Private input forbidden')
        out=repo/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out);copied.append(rel);total+=r['bytes']
    assert total<100*1024**2
    for name in ['release_tools.py','restore_local.py','verify_release.py','prepare_blender_rebuild.py','browser_smoke.mjs','review_downloaded.mjs','release-notes.md','README.md','LICENSES.md','publication-plan.md']:
        p=HERE/name;assert p.is_file();shutil.copy2(p,repo/name)
    docs=repo/'docs';docs.mkdir(exist_ok=True)
    for p in sorted((HERE/'preview-docs').iterdir()):
        assert p.suffix.lower() in {'.png','.json'} and p.is_file()
        shutil.copy2(p,docs/p.name)
    shutil.copy2(HERE/'release-manifest.json',repo/'release-manifest.json')
    license_dir=repo/'LICENSES';license_dir.mkdir(exist_ok=True)
    for src,name in [(root/PROJECT/'LICENSE-Half-Cat.txt','Half-Cat-GPL-3.0-or-later.txt'),(root/PROJECT/'source/vendor/machine/LICENSE','Machine-MIT.txt'),(root/PROJECT/'source/vendor/machine/THREE-LICENSE.txt','Three-MIT.txt'),(root/PROJECT/'source/audio/license-evidence/README.md','Breeze-model-output-README.md')]:
        shutil.copy2(src,license_dir/name)
    shutil.copy2(root/PROJECT/'LICENSE-Half-Cat.txt',repo/'LICENSE')
    helperroot=Path('/Users/qianqiming/Desktop/skill-repos/scenario-labs--blender-expert-skills')
    helpers=repo/'rebuild/vendor/scenario';helpers.mkdir(parents=True,exist_ok=True)
    for name in ['bx_anim.py','bx_common.py']:
        p=helperroot/'scenario-blender-animation/scripts'/name
        if not p.exists():p=helperroot/'scenario-blender-expert/scripts'/name
        if p.exists():shutil.copy2(p,helpers/name)
    shutil.copy2(helperroot/'LICENSE',helpers/'LICENSE')
    # Capture only rebuild-specific input metadata that was still outside public outputs.
    for src,rel in [(root/'work/native-cad/vehicle.name-source-map.json','rebuild/vehicle.name-source-map.json'),(root/'work/virtual-assembly/narration-draft.json','rebuild/narration-draft.json')]:
        assert src.is_file();dst=repo/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    audio_source=repo/'rebuild/audio-sources';audio_source.mkdir(parents=True,exist_ok=True)
    provenance=[];base=root/'work/assembly-film/breeze-prep'
    for relative in ['client.py','offline_asr.py','paraformer_crosscheck.py','level_audio.py','prepare_bundle.py','collect_breeze.py','publish_canonical.py','pilot-leveling-contract.json','revision-53db8ccf997e/client.py','revision-53db8ccf997e/offline_asr.py','revision-53db8ccf997e/paraformer_crosscheck.py','revision-53db8ccf997e/level_audio.py']:
        src=base/relative;assert src.is_file();dst=audio_source/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);provenance.append({'path':relative,'sha256':sha(src)})
    write(audio_source/'source-provenance.json',{'scope':'Actual original production scripts, for inspection/reproduction evidence. Historical Spark paths are retained, not an auto-running TTS installer. Offline models/weights and shared service installation are not included. These code sources are separate from NC sound output licensing. Do not run a source publishing/dispatch script without adapting its explicit inputs and coordinating its shared writer.','files':provenance})
    (audio_source/'README.md').write_text('Actual source scripts for whole-paragraph Breeze synthesis, offline independent Whisper/Paraformer review and sample-count-preserving2:1 compression/static gain. These are historical source, not portable service setup. Use delivered WAV/MP3/AAC for local restoration. Model weights/runtime are not bundled; no TTS is invoked by restore_local.py. Software code and audio output licensing are separate; see root LICENSES.md.\n')
    (repo/'.gitignore').write_text('node_modules/\nrelease-assets/\nrestored-lecture/\n/outputs/启明火箭/source/original-project/\n*.blend\n*.glb\n*.usdc\n*.mp4\n*.wav\n*.mp3\n*.m4a\n*.pcm\n*.zip\n*.tar*\n*.html\n*.png\n!docs/*.png\n*.jpg\n*.jpeg\n*.pdf\n*.SLDPRT\n*.SLDASM\n*.SLDDRW\n*.step\n*.stp\n*.dxf\n__pycache__/\n.DS_Store\n')
    write(HERE/'staging-report.json',{'local_only':True,'github_writes':0,'git_initialized':False,'large_binary_files_staged':0,'preview_png_files_staged':len(list(docs.glob('*.png'))),'copied_small_source_files':len(copied),'copied_source_bytes':total,'repository_stage':str(repo),'stage_paths':copied,'note':'Two current real preview PNGs are explicitly allowed in docs; large models/media remain Release assets. No create/push/release/delete action exists in this tool. Review and final freeze required before root publishes.'})
    print('LOCAL_REPO_STAGE',repo,total)

def pack(root,limit):
    inv=json.loads((HERE/'inventory.private.json').read_text());out=HERE/'release-assets';out.mkdir(exist_ok=True)
    assert inv['status']=='final_frozen_local_snapshot','Final root freeze is required before making upload archives; run inventory --final-freeze after the accepted atlas is finished.'
    bind_master_reference(root)
    assets=[]
    for layer in ['visual','audio-noncommercial']:
        parts=[];current=[];used=0
        for row in inv['files']:
            if row['layer']!=layer:continue
            if current and used+row['bytes']>limit:parts.append(current);current=[];used=0
            current.append(row);used+=row['bytes']
        if current:parts.append(current)
        for number,rows in enumerate(parts,1):
            path=out/f'qiming-{layer}-{number:03d}-of-{len(parts):03d}.tar.gz'
            with tarfile.open(path,'w:gz',format=tarfile.PAX_FORMAT) as tar:
                for row in rows:
                    p=Path(row['input_file']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],('Stale input',row['path'])
                    tar.add(p,arcname=row['path'],recursive=False)
                # Only visual internal aliases, normalized to portable relative targets.
                if number==1 and layer=='visual':
                    for link in inv['symlinks']:
                        info=tarfile.TarInfo(link['path']);info.type=tarfile.SYMTYPE;info.linkname=link['target'];tar.addfile(info)
            assert path.stat().st_size<2*1024**3
            assets.append({'name':path.name,'bytes':path.stat().st_size,'sha256':sha(path),'layer':layer,'file_count':len(rows)})
    shutil.copy2(HERE/'release-manifest.json',out/'release-manifest.json')
    write(out/'assets.json',{'assets':assets,'note':'Independent GPL visual and NC audio aggregation; no combined narrated HTML/MP4 uploaded.'})
    (out/'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['name']}\n" for r in assets)+f"{sha(out/'release-manifest.json')}  release-manifest.json\n"+f"{sha(out/'assets.json')}  assets.json\n")
    print(json.dumps({'assets':len(assets),'bytes':sum(a['bytes'] for a in assets)}))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['derive','inventory','stage','pack']);p.add_argument('--workspace',type=Path,default=DEFAULT_ROOT);p.add_argument('--part-mib',type=int,default=512);p.add_argument('--final-freeze',action='store_true',help='Parent confirms accepted public atlas/media/QA is frozen; recheck every file before archive creation');a=p.parse_args();root=a.workspace.resolve()
    assert (root/PROJECT).is_dir() and (root/VIRTUAL).is_dir()
    if a.action=='derive':derive(root)
    elif a.action=='inventory':inventory(root,a.final_freeze)
    elif a.action=='stage':stage(root)
    else:pack(root,a.part_mib*1024**2)

if __name__=='__main__':main()
