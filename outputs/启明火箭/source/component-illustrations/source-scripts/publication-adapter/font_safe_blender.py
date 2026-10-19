"""Evaluated FONT outlines in publication copies only. No source/native CAD edits."""
import bpy, sys, json, hashlib, argparse, datetime, math
from pathlib import Path
import numpy as np

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while b:=f.read(4*1024*1024):h.update(b)
    return h.hexdigest()

def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)

def mesh_hash(mesh):
    h=hashlib.sha256();counts=[len(mesh.vertices),len(mesh.edges),len(mesh.polygons),len(mesh.loops)];h.update(np.asarray(counts,dtype='<i8').tobytes())
    components={}
    for collection,attribute,n,dtype in [(mesh.vertices,'co',len(mesh.vertices)*3,'<f4'),(mesh.loops,'vertex_index',len(mesh.loops),'<i4'),(mesh.polygons,'loop_total',len(mesh.polygons),'<i4'),(mesh.polygons,'material_index',len(mesh.polygons),'<i4')]:
        data=np.empty(n,dtype=dtype);collection.foreach_get(attribute,data);h.update(data.tobytes());components[attribute]=hashlib.sha256(data.tobytes()).hexdigest()
    for uv in mesh.uv_layers:
        a=np.empty(len(uv.uv)*2,dtype='<f4');uv.uv.foreach_get('vector',a);h.update(uv.name.encode());h.update(a.tobytes());components['uv:'+uv.name]=hashlib.sha256(a.tobytes()).hexdigest()
    return {'sha256':h.hexdigest(),'vertices':counts[0],'polygons':counts[2],'component_sha256':components}

def evaluated_hash(ob,graph,uv_store=None):
    ev=ob.evaluated_get(graph);mesh=ev.to_mesh(preserve_all_data_layers=True,depsgraph=graph)
    try:
        if uv_store is not None:
            uv_store[ob.name]={}
            for uv in mesh.uv_layers:
                a=np.empty(len(uv.uv)*2,dtype='<f4');uv.uv.foreach_get('vector',a);uv_store[ob.name][uv.name]=a.copy()
        return mesh_hash(mesh)
    finally:ev.to_mesh_clear()

def snapshot_nonfont(names=None,uv_store=None):
    bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get();rows={}
    for ob in bpy.data.objects:
        if names is not None and ob.name not in names:continue
        if names is None and ob.type=='FONT':continue
        row={'type':ob.type,'world_matrix_sha256':hashlib.sha256(np.asarray(ob.matrix_world,dtype='<f8').tobytes()).hexdigest(),'local_matrix_sha256':hashlib.sha256(np.asarray(ob.matrix_local,dtype='<f8').tobytes()).hexdigest(),'hide_render':ob.hide_render,'hide_viewport':ob.hide_viewport}
        if ob.type=='MESH':row['base_mesh']=mesh_hash(ob.data)
        if ob.type in {'MESH','CURVE','SURFACE','META'}:row['evaluated_mesh']=evaluated_hash(ob,graph,uv_store)
        rows[ob.name]=row
    return rows

def compare_nonfont(reference,current,reference_uv,current_uv):
    assert set(reference)==set(current);variations=[]
    for name,a in reference.items():
        b=current[name]
        for key in set(a)|set(b):
            if key=='evaluated_mesh':continue
            assert a.get(key)==b.get(key),('Non-font base mesh/matrix/state changed',name,key)
        if 'evaluated_mesh' not in a:continue
        x,y=a['evaluated_mesh'],b['evaluated_mesh']
        assert x['vertices']==y['vertices'] and x['polygons']==y['polygons'],name
        assert set(x['component_sha256'])==set(y['component_sha256'])
        for key,h in x['component_sha256'].items():
            if key.startswith('uv:'):continue
            assert h==y['component_sha256'][key],('Evaluated position/topology/material changed',name,key)
        assert set(reference_uv.get(name,{}))==set(current_uv.get(name,{}))
        for layer,old in reference_uv.get(name,{}).items():
            new=current_uv[name][layer];assert old.shape==new.shape and np.all(np.isfinite(old)) and np.all(np.isfinite(new))
            maximum=float(np.max(np.abs(old.astype(np.float64)-new.astype(np.float64)))) if len(old) else 0.0
            # Render-only control on unchanged source reproduces5.96e-8 UV
            # rounding. Keep raw/base UV and all matrices/positions/topology
            # byte-exact; permit at most two float32 ULP at unit UV scale in
            # the ephemeral modifier UV result (<0.0004px at1600px).
            assert maximum<=2.5e-7,('Evaluated UV exceeds measured display tolerance',name,layer,maximum)
            if maximum:
                variations.append({'object':name,'uv_layer':layer,'maximum_abs_uv_difference':maximum,'changed_uv_values':int(np.count_nonzero(old!=new)),'absolute_tolerance':2.5e-7,'basis':'Unchanged-source render-only control; source base UV and evaluated positions/topology/materials remain byte-exact'})
    return variations

def font_inventory():
    return [{'name':f.name,'filepath':f.filepath,'users':f.users,'packed':bool(f.packed_file),'packed_bytes':len(f.packed_file.data) if f.packed_file else 0,'packed_sha256':hashlib.sha256(bytes(f.packed_file.data)).hexdigest() if f.packed_file else None} for f in bpy.data.fonts]

def open_file(path):
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    bpy.context.view_layer.update()

def render(path):
    scene=bpy.context.scene;old=scene.render.filepath;threads=(scene.render.threads_mode,scene.render.threads)
    scene.render.filepath=str(path);scene.render.threads_mode='FIXED';scene.render.threads=8
    try:bpy.ops.render.render(write_still=True)
    finally:scene.render.filepath=old;scene.render.threads_mode,scene.render.threads=threads

def convert_one(item,job,review_root,paired=False):
    source=Path(item['source_file']);dest=Path(item['output_file']);assert sha(source)==item['source_sha256']
    open_file(source);assert bpy.app.version>=(5,2,2)
    assert not bpy.data.libraries,'Do not silently pull external linked Blend libraries'
    assert not bpy.data.sounds and not bpy.data.movieclips and not bpy.data.cache_files
    baseline_uv={};baseline=snapshot_nonfont(uv_store=baseline_uv);fonts_before=font_inventory();camera=bpy.context.scene.camera
    camera_snapshot={'name':camera.name,'matrix':np.asarray(camera.matrix_world,dtype='<f8').tolist(),'type':camera.data.type,'lens':camera.data.lens,'ortho_scale':camera.data.ortho_scale}
    render_before=review_root/(item['family']+'-'+item['id']+'-before.png')
    render_after=review_root/(item['family']+'-'+item['id']+'-after.png')
    if paired:
        render(render_before)
        baseline_uv={};baseline=snapshot_nonfont(uv_store=baseline_uv)
    graph=bpy.context.evaluated_depsgraph_get();text_rows=[]
    for old in [o for o in bpy.data.objects if o.type=='FONT']:
        assert not old.animation_data and not old.constraints and not old.children,('Unsupported animated/parent text',old.name)
        original_name=old.name;data=old.data;matrix=old.matrix_world.copy();before=evaluated_hash(old,graph)
        evaluated=old.evaluated_get(graph)
        mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=graph)
        assert mesh_hash(mesh)==before,('Evaluated outline mismatch',original_name)
        params={k:getattr(data,k) for k in ['body','align_x','align_y','size','space_character','space_word','space_line','shear','extrude','bevel_depth','bevel_resolution','resolution_u','fill_mode','offset','overflow'] if hasattr(data,k)}
        row={'object_name':original_name,'text':data.body,'parameters':params,'original_font_resources':{k:getattr(data,k).name if getattr(data,k,None) else None for k in ['font','font_bold','font_italic','font_bold_italic']},'evaluated_mesh_before':before,'source_world_matrix':np.asarray(matrix,dtype='<f8').tolist()}
        old.name='__PUBLICATION_FONT_SOURCE_'+original_name
        new=bpy.data.objects.new(original_name,mesh)
        for collection in old.users_collection:collection.objects.link(new)
        new.parent=old.parent;new.parent_type=old.parent_type;new.parent_bone=old.parent_bone;new.rotation_mode=old.rotation_mode
        new.matrix_parent_inverse=old.matrix_parent_inverse.copy();new.matrix_basis=old.matrix_basis.copy()
        for attr in ['hide_render','hide_viewport','hide_select','show_in_front','display_type','color','visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:
            if hasattr(old,attr) and hasattr(new,attr):setattr(new,attr,getattr(old,attr))
        for k in old.keys():new[k]=old[k]
        new['publication_font_outline']=True;new['publication_original_text']=row['text'];new['publication_original_font']=row['original_font_resources']['font'] or ''
        bpy.data.objects.remove(old,do_unlink=True)
        if data.users==0:bpy.data.curves.remove(data)
        bpy.context.view_layer.update()
        error=float(np.max(np.abs(np.asarray(new.matrix_world)-np.asarray(matrix))));assert error<=1e-6,(original_name,error)
        row['publication_world_matrix_max_abs_error']=error;row['publication_mesh_hash']=mesh_hash(mesh);text_rows.append(row)
    for curve in list(bpy.data.curves):
        if isinstance(curve,bpy.types.TextCurve):
            assert curve.users==0;curve.use_fake_user=False;bpy.data.curves.remove(curve)
    removed=[]
    for font in list(bpy.data.fonts):
        if font.packed_file or font.filepath!='<builtin>':
            assert font.users==0,('Font still referenced',font.name,font.users)
            removed.append({'name':font.name,'packed':bool(font.packed_file)});font.use_fake_user=False;bpy.data.fonts.remove(font,do_unlink=True)
    assert not any(o.type=='FONT' for o in bpy.data.objects)
    assert not any(f.packed_file or f.filepath!='<builtin>' for f in bpy.data.fonts)
    # Actual direct images are already mirrored at their final relative package
    # locations, including the two self-rendered CAD previews outside original392.
    image_rows=[];inputs=job['image_inputs'];mirror=Path(job['publication_mirror'])
    bpy.data.use_autopack=False
    for image in bpy.data.images:
        if image.source!='FILE':continue
        old_path=image.filepath;original=bpy.path.abspath(image.filepath)
        packed=bytes(image.packed_file.data) if image.packed_file else None
        digest=hashlib.sha256(packed).hexdigest() if packed else sha(Path(original))
        candidates=[r for r in inputs if r['sha256']==digest]
        assert candidates,('Unmapped actual image input',image.name,old_path,digest)
        match=candidates[0];target=Path(match['local_mirror_file']);assert target.is_relative_to(mirror) and sha(target)==digest
        if image.packed_file:image.unpack(method='REMOVE')
        image.filepath=bpy.path.relpath(str(target),start=str(dest.parent));assert image.filepath.startswith('//')
        image_rows.append({'image':image.name,'original_path':old_path,'publication_relative_path':image.filepath,'release_target':match['release_path'],'sha256':digest,'already_in_original392':match['already_in_original392'],'packed_after':bool(image.packed_file)})
    current_uv={};current=snapshot_nonfont(set(baseline),current_uv)
    uv_variations=compare_nonfont(baseline,current,baseline_uv,current_uv)
    for scene in bpy.data.scenes:scene.render.filepath='//renders/'+item['family']+'-'+item['id']+'.png'
    bpy.context.scene['publication_text_mode']='Evaluated glyph mesh outlines; original body and layout parameters are in font-safe audit and object custom properties; no redistributed Apple font software.'
    bpy.context.scene['publication_original_blend_sha256']=item['source_sha256']
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Paths above already use the destination .blend directory. Blender's
    # default remapping would interpret them relative to the source file again.
    bpy.ops.wm.save_as_mainfile(filepath=str(dest),check_existing=False,compress=True,relative_remap=False)
    published_sha=sha(dest);open_file(dest)
    reopened_uv={};reopened=snapshot_nonfont(set(baseline),reopened_uv)
    reopen_variations=compare_nonfont(baseline,reopened,baseline_uv,reopened_uv)
    assert not any(o.type=='FONT' for o in bpy.data.objects)
    assert not any(f.packed_file or f.filepath!='<builtin>' for f in bpy.data.fonts)
    for row in text_rows:
        ob=bpy.data.objects[row['object_name']];assert ob.type=='MESH' and mesh_hash(ob.data)==row['publication_mesh_hash']
        assert ob['publication_original_text']==row['text']
    for image in bpy.data.images:
        if image.source=='FILE':
            assert image.filepath.startswith('//')
            resolved=Path(bpy.path.abspath(image.filepath)).resolve();assert resolved.is_relative_to(mirror) and resolved.is_file(),resolved
            image.reload()
            mapped=[r for r in image_rows if r['image']==image.name];assert len(mapped)==1
            assert sha(resolved)==mapped[0]['sha256'],('Reopened image bytes differ',image.name)
            # reload invalidates the lazily decoded buffer; reading pixels is
            # necessary before has_data is meaningful in background Blender.
            dimensions=tuple(image.size);pixel_count=len(image.pixels)
            first_pixel=tuple(image.pixels[:4])
            assert dimensions[0]>0 and dimensions[1]>0 and pixel_count==dimensions[0]*dimensions[1]*4 and len(first_pixel)==4,('Reopened image has no actual pixels',image.name)
            mapped[0]['decoded_image_size']=list(dimensions);mapped[0]['decoded_pixel_values']=pixel_count
    assert sha(source)==item['source_sha256'] and sha(dest)==published_sha
    if paired:render(render_after)
    return {**item,'status':'saved_and_actually_reopened_font_safe_publication_copy','published_sha256':published_sha,'published_bytes':dest.stat().st_size,'blender_version':bpy.app.version_string,'font_objects_before':len(text_rows),'font_objects_after':0,'fonts_before':fonts_before,'fonts_after_reopen':font_inventory(),'removed_font_resources':removed,'all_nonfont_base_mesh_uv_and_matrices_exact':True,'all_nonfont_evaluated_positions_topology_material_indices_exact':True,'ephemeral_modifier_uv_variations_before_save':uv_variations,'ephemeral_modifier_uv_variations_after_reopen':reopen_variations,'nonfont_reference':baseline,'original_source_sha256_unchanged':True,'text_outlines':text_rows,'image_inputs':image_rows,'all_file_image_dependencies_are_package_relative':True,'camera_reference':camera_snapshot,'paired_before_render':str(render_before) if paired else None,'paired_after_render':str(render_after) if paired else None,'render_output_path_is_package_relative':True,'source_geometry_created_or_redesigned':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--job',type=Path,required=True);p.add_argument('--only');p.add_argument('--pilot',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);job=json.loads(a.job.read_text());out=Path(job['component_root']);reviews=out/'review';reviews.mkdir(exist_ok=True)
    selected=[r for r in job['items'] if not a.only or r['family']+':'+r['id']==a.only]
    if a.pilot:selected=selected[:1]
    results=[];manifest=out/'font-safe-manifest.json'
    prior=json.loads(manifest.read_text()) if manifest.exists() else {'items':[]}
    cache={r['source_file']:r for r in prior['items']}
    representatives={('stock','A1-01'),('stock','A6-15'),('manual','C1-11'),('function','A3-10'),('source','A7-01')}
    for item in selected:
        cached=cache.get(item['source_file'])
        if cached and sha(Path(cached['output_file']))==cached['published_sha256'] and sha(Path(item['source_file']))==cached['source_sha256']:
            row=cached
        else:row=convert_one(item,job,reviews,(item['family'],item['id']) in representatives)
        cache[item['source_file']]=row;results.append(row)
        complete=[cache[i['source_file']] for i in job['items'] if i['source_file'] in cache]
        write(manifest,{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'purpose':'Publication-only font-safe editable illustration copies, no source/native CAD edits','actual_source_count_expected':len(job['items']),'actual_completed_count':len(complete),'all_completed':len(complete)==len(job['items']),'no_restricted_font_software_in_completed_copies':True,'image_inputs':job['image_inputs'],'items':complete})
        print('FONT_SAFE_CHECKPOINT '+json.dumps({'family':row['family'],'id':row['id'],'text_outlines':row['font_objects_before'],'bytes':row['published_bytes'],'source_unchanged':True},ensure_ascii=False),flush=True)
    print('RESULT '+json.dumps({'actual_this_run':len(results),'total_completed':len(cache),'manifest':str(manifest)}),flush=True)

if __name__=='__main__':main()
