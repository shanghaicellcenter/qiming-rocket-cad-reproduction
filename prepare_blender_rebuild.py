"""Generate relocated rebuild copies; leaves delivered .blend/source scripts untouched."""
from pathlib import Path
import argparse,json,shutil,hashlib,py_compile,subprocess,re

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--blender',type=Path);a=p.parse_args();root=a.root.resolve();out=root/'rebuild/virtual-assembly';out.mkdir(parents=True,exist_ok=True)
    runtime=None
    if a.blender:
        result=subprocess.run([str(a.blender),'--version'],capture_output=True,text=True,check=True)
        match=re.search(r'Blender (\d+)\.(\d+)\.(\d+)',result.stdout);assert match
        version=tuple(map(int,match.groups()));assert version>=(5,2,2),'Use actual5.2.2-compatible runtime, not old4.4.x.'
        runtime={'executable':str(a.blender.resolve()),'actual_version_header':result.stdout.splitlines()[0],'runtime_version_checked_only':True,'full_model_rebuild_executed':False}
    delivery=root/'outputs/virtual-assembly';project=root/'outputs/启明火箭'
    for name in ['assembly-stages.json','alignment-qc.json']:
        src=delivery/name;assert src.is_file();shutil.copy2(src,out/name)
    plan=json.loads((out/'assembly-stages.json').read_text());plan['source_blend']=str(project/'assembly/vehicle-browse.blend');plan['source_usd']=str(project/'native-cad/vehicle-browse.usdc')
    assert Path(plan['source_blend']).is_file() and Path(plan['source_usd']).is_file()
    assert hashlib.sha256(Path(plan['source_usd']).read_bytes()).hexdigest()==plan['source_usd_sha256']
    (out/'assembly-stages.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    changes=[]
    for name in ['build_virtual_assembly.py','plan_assembly_stages.py','verify_virtual_assembly.py']:
        source=(delivery/name).read_text()
        old="ROOT=Path('/Users/qianqiming/Documents/Codex/2026-10-19/new-chat')";assert old in source
        source=source.replace(old,"ROOT=Path(__file__).resolve().parents[2]")
        source=source.replace("ROOT/'work/virtual-assembly'","ROOT/'rebuild/virtual-assembly'")
        source=source.replace("ROOT/'work/native-cad/vehicle-blender/vehicle-browse.audit.json'","ROOT/'outputs/启明火箭/assembly/vehicle-browse.audit.json'")
        source=source.replace("ROOT/'work/native-cad/vehicle-blender/vehicle-browse.blend'","ROOT/'outputs/启明火箭/assembly/vehicle-browse.blend'")
        source=source.replace("ROOT/'work/native-cad/vehicle-browse.usdc'","ROOT/'outputs/启明火箭/native-cad/vehicle-browse.usdc'")
        source=source.replace("ROOT/'work/native-cad/vehicle.name-source-map.json'","ROOT/'rebuild/vehicle.name-source-map.json'")
        source=source.replace("sys.path.append('/Users/qianqiming/.codex/skills/scenario-blender-animation/scripts')","sys.path.insert(0,str(ROOT/'rebuild/vendor/scenario'))")
        if name=='build_virtual_assembly.py':
            source=source.replace("OUT=ROOT/'outputs/virtual-assembly'","OUT=ROOT/'rebuilt/virtual-assembly'")
        elif name=='verify_virtual_assembly.py':
            source=source.replace("DELIVERY=ROOT/'outputs/virtual-assembly'","DELIVERY=ROOT/'rebuilt/virtual-assembly'")
        assert '/Users/' not in source and "ROOT/'work/" not in source
        destination=out/name;destination.write_text(source);py_compile.compile(str(destination),doraise=True);changes.append(name)
    assert (root/'rebuild/vendor/scenario/bx_anim.py').is_file() and (root/'rebuild/vendor/scenario/LICENSE').is_file()
    assert (root/'rebuild/vehicle.name-source-map.json').is_file()
    changed_files=[{'path':name,'historical_original_sha256':hashlib.sha256((delivery/name).read_bytes()).hexdigest(),'generated_portable_sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in [*changes,'assembly-stages.json']]
    (out/'PORTABILITY-CHANGES.json').write_text(json.dumps({'changes':'Relocated root, input metadata, MIT animation helper and output paths only. Delivered source scripts and source geometry remain unchanged. New rendering/rebuild not claimed tested by preparation alone.','files':changed_files,'blender_requirement':'Actual source version5.2.2 LTS, build d13f752e3b9c, or compatible newer version; Blender4.4.3 cannot open5.x files','runtime_check':runtime,'generated_output_directory':'rebuilt/virtual-assembly','original_delivery_preserved':True},ensure_ascii=False,indent=2)+'\n')
    generated=[{'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.iterdir() if p.is_file() and p.name!='delivery-manifest.json']
    (out/'delivery-manifest.json').write_text(json.dumps({'scope':'Generated portable copies only; hashes do not impersonate the original delivery manifest.','historical_original_delivery_manifest_sha256':hashlib.sha256((delivery/'delivery-manifest.json').read_bytes()).hexdigest(),'files':generated},ensure_ascii=False,indent=2)+'\n')
    print(out)

if __name__=='__main__':main()
