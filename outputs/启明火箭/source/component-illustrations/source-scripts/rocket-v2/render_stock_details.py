"""Independent Blender raw-material illustrations, never finished flight geometry."""
import bpy, bmesh, hashlib, json, math, sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path('/Users/qianqiming/Documents/Codex/2026-10-19/ni')
OUT=ROOT/'outputs/rocket/assets/stock-details'; WORK=ROOT/'work/rocket-v2/stock-visual-evidence'
SOURCES=ROOT/'outputs/rocket/stock-detail-sources'
for p in [OUT,WORK,SOURCES]:p.mkdir(parents=True,exist_ok=True)
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
ROWS=[
 ('A1-01','bar',(4,.5),'6061 铝圆棒','圆盘状毛坯，还不是带接口的封头。'),
 ('A1-02','bar',(4,3),'6061 铝圆棒','实心原料，还不是有空腔和密封圈的活塞。'),
 ('A1-03','tube',(4,.125,36),'6061 铝管','空心长管，对应贮箱筒体的原料。'),
 ('A1-04','tube',(4,.5,3),'6061 厚壁铝管','壁厚原文冲突：物项 1/2 英寸；供应商 1/4 英寸。'),
 ('A2-11','flex',(),'尼龙管材','柔性管材；本条用于氧化剂加注连接。'),
 ('A2-15','bar',(.75,6),'6061-T6 铝圆棒','实心圆棒，对应快卸接头的原料。'),
 ('A3-13','filament',(),'PLA+ 打印线材','连续细线状原料；不是已经打印的结构件。'),
 ('A4-01','bar',(3,6),'6061 铝圆棒','同一原料条目用于喷注器与喷管相关成品。'),
 ('A4-02','tube',(3,.5,6),'6061 厚壁铝管','空心厚壁管，对应燃烧室筒体原料。'),
 ('A4-03','copper',(1.5,2),'110 紫铜圆棒','铜色只帮助识别材料类别，尚未形成喉部。'),
 ('A6-09','paper',(4,None,36),'箭体纸管','纸质空心管；这里不是金属贮箱。'),
 ('A6-15','angle',(1,1,.125,24),'L 形角铝','先认 L 形截面；孔位和成品支架另看。'),
 ('A6-17','board',(12,24,.25),'桦木胶合板','平板原料，还没有尾翼的外轮廓。'),
 ('A7-02','tarp',(),'六角天幕材料','平面的柔性材料；不是已经展开的降落伞。'),
 ('A7-03','cord',(),'Kevlar 细绳材料','细绳与宽尼龙扁带不同；本条对应主伞承力绳材。'),
 ('C1-34','flex',(),'尼龙管材余料','与加注管同类的管材，记录地面系统材料用途。'),
 ('C1-35','filament',(),'PLA+ 打印线材','打印原料用于地面定制件；不是飞行安装件。'),
]
PARTS={p['id']:p for p in json.loads((ROOT/'work/rocket/parts.json').read_text())}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mat(name,color,metal=0,emit=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();o=nt.nodes.new('ShaderNodeOutputMaterial')
 n=nt.nodes.new('ShaderNodeEmission' if emit else 'ShaderNodeBsdfPrincipled')
 n.inputs['Color' if emit else 'Base Color'].default_value=(*color,1)
 if not emit:n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=.35
 nt.links.new(n.outputs[0],o.inputs['Surface']);return m
def bevel(o,w=.015):
 b=o.modifiers.new('Soft physical edge','BEVEL');b.width=w;b.segments=3
 return o
def mesh(name,verts,faces,m):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.validate();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(m);return o
def tube(od,wall,length,m):
 ro=od/2;ri=ro-wall;n=96;verts=[]
 for x,r in [(-length/2,ro),(length/2,ro),(-length/2,ri),(length/2,ri)]:
  verts.extend((x,r*math.cos(i*2*math.pi/n),r*math.sin(i*2*math.pi/n)) for i in range(n))
 faces=[]
 for i in range(n):
  j=(i+1)%n;faces.extend([(i,j,n+j,n+i),(2*n+j,2*n+i,3*n+i,3*n+j),(j,i,2*n+i,2*n+j),(n+i,n+j,3*n+j,3*n+i)])
 return bevel(mesh('Unmachined open tube',verts,faces,m),min(.012,wall*.12))
def cylinder(d,l,m):
 bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=d/2,depth=l,rotation=(0,math.pi/2,0));o=bpy.context.object;o.name='Solid unmachined bar';o.data.materials.append(m);return bevel(o,min(.025,d*.02))
def curve(name,points,r,m):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=r;c.bevel_resolution=4;c.use_fill_caps=True
 sp=c.splines.new('POLY');sp.points.add(len(points)-1)
 for p,xyz in zip(sp.points,points):p.co=(*xyz,1)
 o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);c.materials.append(m);return o
def cube(name,d,m):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.dimensions=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m);return bevel(o,.012)
def flexible_hollow_tube(points,outer,inner,m):
 n=32;verts=[]
 for j,p in enumerate(points):
  p=Vector(p);t=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])).normalized();up=Vector((0,0,1));u=t.cross(up).normalized();v=t.cross(u).normalized()
  for r in [outer,inner]:
   verts.extend(p+r*(math.cos(i*2*math.pi/n)*u+math.sin(i*2*math.pi/n)*v) for i in range(n))
 faces=[];stride=2*n
 for j in range(len(points)-1):
  for i in range(n):
   q=(i+1)%n;a=j*stride;b=(j+1)*stride
   faces.extend([(a+i,a+q,b+q,b+i),(a+n+q,a+n+i,b+n+i,b+n+q)])
 for i in range(n):
  q=(i+1)%n;last=(len(points)-1)*stride
  faces.extend([(i,n+i,n+q,q),(last+i,last+q,last+n+q,last+n+i)])
 ob=mesh('Generic hollow nylon stock; wall thickness symbolic',verts,faces,m)
 for f in ob.data.polygons:f.use_smooth=True
 return ob
def build(kind,d,m,pid):
 objects=[]
 if kind in ['bar','copper']:objects=[cylinder(*d,m)]
 elif kind=='tube':objects=[tube(*d,m)]
 elif kind=='paper':objects=[tube(d[0]+2*.08,.08,d[2],m)] # source supplier ID and BOM wall note guide type only; no dimensional certification
 elif kind=='angle':
  a,b,t,L=d;poly=[(0,0),(a,0),(a,t),(t,t),(t,b),(0,b)];verts=[(x,y-a/2,z-b/2) for x in [-L/2,L/2] for y,z in poly];faces=[tuple(reversed(range(6))),tuple(range(6,12))]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)];objects=[bevel(mesh('L section raw stock',verts,faces,m),.008)];objects[0].rotation_euler.x=math.radians(100)
 elif kind=='board':objects=[cube('Uncut plywood',(d[1],d[0],d[2]),m)]
 elif kind in ['flex','filament','cord']:
  radius={'flex':.10,'filament':.035,'cord':.055}[kind];points=[]
  if kind=='flex' and pid=='C1-34':
   for i in range(151):
    t=i/150;points.append((-2.7+5.4*t,-1.05*math.sin(math.pi*t),.08*math.sin(math.pi*t)))
  elif kind=='flex':
   for i in range(151):
    t=i/150;points.append((-2.7+5.4*t,.62*math.sin(2*math.pi*t),.18*math.sin(math.pi*t)))
  else:
   for i in range(451):
    t=i/450;angle=t*math.pi*(4 if pid=='C1-35' else 6);r=1.6-.8*t;points.append((r*math.cos(angle),(0.80 if pid=='C1-35' else 1)*r*math.sin(angle),.04*t))
   points.extend([(points[-1][0]+i*.04,points[-1][1]-.015*i,.04) for i in range(1,36)])
  if kind=='flex':
   # Turn only the generic free end toward the camera so the original hollow type is readable.
   count=30;laststep=Vector(points[-1])-Vector(points[-2]);toward=Vector((6.5,-9,6)).normalized()*laststep.length
   correction=(toward-laststep)*(count/2)
   for j in range(count+1):
    idx=len(points)-count-1+j;points[idx]=tuple(Vector(points[idx])+correction*(j/count)**2)
  objects=[flexible_hollow_tube(points,radius,radius*.68,m) if kind=='flex' else curve('Continuous raw material',points,radius,m)]
 elif kind=='tarp':
  verts=[(2.5*math.cos(i*math.pi/3),2.5*math.sin(i*math.pi/3),.02*math.cos(i*math.pi/3)) for i in range(6)]
  ob=mesh('Flat hexagonal tarp outline',verts,[tuple(range(6))],m);so=ob.modifiers.new('Cloth thickness symbolic','SOLIDIFY');so.thickness=.018;objects=[ob]
 # Normalize only the display size; material-class ratios are kept for explicitly stated dimensions.
 bpy.context.view_layer.update();corners=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box];lo=Vector(tuple(min(p[i] for p in corners) for i in range(3)));hi=Vector(tuple(max(p[i] for p in corners) for i in range(3)));center=(lo+hi)/2;scale=5/max(hi-lo)
 root=bpy.data.objects.new('Display normalization only',None);bpy.context.collection.objects.link(root)
 for o in objects:o.parent=root;o.location-=center
 root.scale=(scale,)*3;return objects
def projected_bbox(objects,s,cam):
 bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();pixels=[]
 for ob in objects:
  ev=ob.evaluated_get(deps);me=ev.to_mesh()
  for v in me.vertices:
   p=world_to_camera_view(s,cam,ev.matrix_world@v.co);pixels.append((p.x*s.render.resolution_x,(1-p.y)*s.render.resolution_y))
  ev.to_mesh_clear()
 return [min(p[0] for p in pixels),min(p[1] for p in pixels),max(p[0] for p in pixels),max(p[1] for p in pixels)]
def fit_projected_geometry(objects,s,cam,target=(300,280,1350,760)):
 # Fit measured evaluated geometry, not a world-axis box or largest object dimension.
 root=objects[0].parent;before=projected_bbox(objects,s,cam)
 fac=min((target[2]-target[0])/(before[2]-before[0]),(target[3]-target[1])/(before[3]-before[1]))*.96
 root.scale*=fac;bpy.context.view_layer.update();scaled=projected_bbox(objects,s,cam)
 dx=(target[0]+target[2]-scaled[0]-scaled[2])/2;dy=(target[1]+target[3]-scaled[1]-scaled[3])/2
 aspect=s.render.resolution_x/s.render.resolution_y;rot=cam.rotation_euler.to_quaternion()
 root.location+=rot@Vector((dx*cam.data.ortho_scale/s.render.resolution_x,-dy*cam.data.ortho_scale/aspect/s.render.resolution_y,0))
 after=projected_bbox(objects,s,cam)
 assert after[0]>=target[0]-1 and after[1]>=target[1]-1 and after[2]<=target[2]+1 and after[3]<=target[3]+1,after
 return {'beforePixels':before,'afterPixels':after,'targetPixels':list(target),'scaleFactor':fac,'method':'actual evaluated mesh/curve vertices projected by final camera; uniform scale and camera-plane translation'}
def label(body,x,y,size,m,camera):
 c=bpy.data.curves.new('Editable Chinese label','FONT');c.body=body;c.font=bpy.data.fonts.load(FONT,check_existing=True);c.size=size*12/1600;c.space_character=1.03
 o=bpy.data.objects.new(body,c);bpy.context.collection.objects.link(o);c.materials.append(m)
 rot=camera.rotation_euler.to_quaternion();o.rotation_euler=camera.rotation_euler;o.location=camera.location+rot@Vector(((x/1600-.5)*12,(.5-y/1000)*7.5,-9));return o
evidence=[]
merged={x['id']:x for x in json.loads((WORK/'render-evidence.json').read_text())} if (WORK/'render-evidence.json').exists() else {}
for x in merged.values():
 if x.get('kind')=='paper':
  x['displayDimensionsSourceInches']=None;x['symbolicWallThicknessNotSourceSpecification']=False;x['paperWallSourceNoteInches']=.08
for id,kind,d,material,description in ROWS:
 if '--only' in sys.argv and id not in sys.argv[sys.argv.index('--only')+1].split(','):continue
 bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=4
 s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='Standard'
 s.world=bpy.data.worlds.new('Soft studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.82,.86,.86,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.4
 m=mat(material,{'copper':(.65,.25,.09),'paper':(.67,.69,.66),'board':(.65,.47,.25),'tarp':(.16,.36,.39),'cord':(.68,.45,.07),'filament':(.46,.50,.52),'flex':(.40,.46,.49)}.get(kind,(.57,.65,.68)),0 if kind in ['paper','board','tarp','cord','filament','flex'] else .65)
 if kind in ['filament','flex']:
  bsdf=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Roughness'].default_value=.75;bsdf.inputs['Specular IOR Level'].default_value=.20
 if kind=='paper':
  bsdf=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Roughness'].default_value=.82;bsdf.inputs['Specular IOR Level'].default_value=.15
 objects=build(kind,d,m,id)
 bpy.ops.object.camera_add(location=(6.5,-9,6));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=12;s.camera=cam
 fit=fit_projected_geometry(objects,s,cam)
 rot=cam.rotation_euler.to_quaternion();paper=mat('Uniform pale presentation background',(.93,.95,.94),emit=True)
 mesh('Background card',[cam.location+rot@Vector((x,y,-20)) for x,y in [(-8,-6),(8,-6),(8,6),(-8,6)]],[(0,1,2,3)],paper)
 for name,pos,energy,size in [('Key',(-3,-4,7),850,5),('Rim',(3,3,5),600,4)]:
  ld=bpy.data.lights.new(name,'AREA');ld.energy=energy;ld.shape='DISK';ld.size=size;lo=bpy.data.objects.new(name,ld);s.collection.objects.link(lo);lo.location=pos;lo.rotation_euler=(-lo.location).to_track_quat('-Z','Y').to_euler()
 # Emission background avoids blotchy shadow fields and reflected duplicate text.
 ink=mat('Flat legible ink',(.035,.095,.12),emit=True);muted=mat('Secondary ink',(.17,.25,.27),emit=True)
 label('启明火箭 · 原料形态示意',70,70,24,muted,cam);label(id+'  '+PARTS[id]['name'],70,140,42,ink,cam)
 label(material,70,220,29,ink,cam);label(description,70,845,29,ink,cam)
 label('类型示意 · 不代表供应商实物、成品外形或尺寸检验',70,925,25,muted,cam)
 label('来源：原物料表 '+id+'；材料记录与成品分别解释',70,970,20,muted,cam)
 bpy.context.view_layer.update();audit=[]
 for o in objects:
  if o.type!='MESH':continue
  bm=bmesh.new();bm.from_mesh(o.data);audit.append({'name':o.name,'vertices':len(bm.verts),'faces':len(bm.faces),'nonManifoldEdges':sum(not e.is_manifold for e in bm.edges)});bm.free()
 bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 s['raw_stock_part_id']=id;s['raw_stock_illustration']=True;s['source_dimension_certified']=False
 s['symbolic_wall_thickness']=bool(kind=='flex');s['product_identity_verified']=False
 if kind=='paper':s['paper_wall_source_note_inch']=.08
 s['fit_projected_pixels']=fit['afterPixels']
 blend=SOURCES/(id+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True);png=WORK/(id+'.png');s.render.filepath=str(png);bpy.ops.render.render(write_still=True)
 evidence.append({'id':id,'kind':kind,'sourceItemName':PARTS[id]['sourceItemName'],'sourceRef':PARTS[id]['sourceRef'],'displayDimensionsSourceInches':d if kind not in ['paper','flex','filament','cord','tarp'] else None,'notDimensionCertified':True,'symbolicWallThicknessNotSourceSpecification':bool(kind=='flex'),'blend':str(blend),'png':str(png),'audit':audit,'projectionFit':fit,'blenderVersion':bpy.app.version_string,'review':'pending actual image inspection'})
 merged[id]=evidence[-1]
 (WORK/'render-evidence.json').write_text(json.dumps([merged[r[0]] for r in ROWS if r[0] in merged],ensure_ascii=False,indent=2));print(json.dumps({'id':id,'rendered':str(png)},ensure_ascii=False),flush=True)
print(json.dumps({'rendered':len(evidence),'scope':'raw material illustrations only'},ensure_ascii=False))
