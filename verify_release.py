"""Verify downloaded assets/files, optionally extract into a separate directory. Never deletes."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, os, tarfile

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(4*1024*1024):h.update(b)
    return h.hexdigest()

def safe_path(root,name):
    rel=PurePosixPath(name)
    assert not rel.is_absolute() and '..' not in rel.parts and rel.parts, name
    target=root.joinpath(*rel.parts)
    assert target.resolve().is_relative_to(root.resolve()),name
    return target

def extract_assets(assets,root,layer='all'):
    checks={name:digest for digest,name in (line.split(None,1) for line in (assets/'SHA256SUMS').read_text().splitlines() if line.strip())}
    for name in ['assets.json','release-manifest.json']:assert sha(assets/name)==checks[name],('Metadata checksum mismatch',name)
    entries=[r for r in json.loads((assets/'assets.json').read_text())['assets'] if layer=='all' or r['layer']==layer]
    assert entries
    for entry in entries:
        path=assets/entry['name'];assert path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],entry['name']
    links=[]
    for entry in entries:
        with tarfile.open(assets/entry['name'],'r:gz') as tar:
            for member in tar:
                dest=safe_path(root,member.name)
                if member.issym():
                    target=(dest.parent/member.linkname).resolve()
                    assert target.is_relative_to(root.resolve()),member.name
                    links.append((dest,member.linkname));continue
                assert member.isfile(),('Unsupported archive member',member.name)
                assert not dest.is_symlink()
                source=tar.extractfile(member);assert source
                if dest.exists():
                    incoming=hashlib.sha256()
                    while block:=source.read(4*1024*1024):incoming.update(block)
                    assert sha(dest)==incoming.hexdigest(),('Refusing to overwrite changed local file',str(dest))
                    continue
                dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as out:
                    while block:=source.read(4*1024*1024):out.write(block)
    for dest,target in links:
        if dest.is_symlink():assert os.readlink(dest)==target
        else:
            assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(target)
    return entries

def verify(root,manifest,layer='all'):
    rows=[];errors=[]
    for r in manifest['files']:
        if layer!='all' and r['layer']!=layer:continue
        p=safe_path(root,r['path'])
        ok=p.is_file() and p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
        rows.append({'path':r['path'],'passed':ok})
        if not ok:errors.append(r['path'])
    for l in manifest['symlinks'] if layer!='audio-noncommercial' else []:
        p=safe_path(root,l['path']);ok=p.is_symlink() and os.readlink(p)==l['target'] and p.exists()
        if not ok:errors.append(l['path'])
    # Independent original-source392 identity check, not only delivery hashes.
    original_errors=[]
    if layer!='audio-noncommercial':
        original_path=root/'outputs/启明火箭/source/original-project-manifest.json'
        original=json.loads(original_path.read_text());snapshot=original_path.parent/'original-project'
        original_errors=[r['relative_path'] for r in original['files'] if not (snapshot/r['relative_path']).is_file() or (snapshot/r['relative_path']).stat().st_size!=r['bytes'] or sha(snapshot/r['relative_path'])!=r['sha256']]
        assert len(original['files'])==392
    return {'selected_layer':layer,'file_count':len(rows),'all_files_sha256_passed':not errors,'file_errors':errors,'original_snapshot_count':392 if layer!='audio-noncommercial' else None,'original_392_sha256_passed':not original_errors if layer!='audio-noncommercial' else None,'original_errors':original_errors,'passed':not errors and not original_errors}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--asset-dir',type=Path);p.add_argument('--extract',action='store_true');p.add_argument('--layer',choices=['all','visual','audio-noncommercial'],default='all');a=p.parse_args();root=a.root.resolve();root.mkdir(parents=True,exist_ok=True)
    if a.extract:
        assert a.asset_dir;extract_assets(a.asset_dir.resolve(),root,a.layer)
    mp=a.manifest or ((a.asset_dir/'release-manifest.json') if a.asset_dir else root/'release-manifest.json')
    report=verify(root,json.loads(mp.read_text()),a.layer);print(json.dumps(report,ensure_ascii=False,indent=2))
    (root/'download-integrity-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert report['passed'],'Downloaded restoration is incomplete; no cleanup is authorized by this tool.'

if __name__=='__main__':main()
