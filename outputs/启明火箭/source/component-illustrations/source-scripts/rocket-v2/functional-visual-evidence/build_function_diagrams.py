"""Independent teaching schematics. No original CAD or source files are opened.

Brief: 1600 x 1000 editorial diagrams; arbitrary teaching coordinates, no scale.
Colors indicate functional groups only. Editable geometry and text stay in each blend.
"""
import bpy, math, sys, json
from pathlib import Path
from mathutils import Vector

ROOT=Path('/Users/qianqiming/Documents/Codex/2026-10-19/ni')
OUT=ROOT/'outputs/rocket/assets/function-details'
SRC=ROOT/'outputs/rocket/functional-sources'
EVID=ROOT/'work/rocket-v2/functional-visual-evidence'
for d in (OUT,SRC,EVID): d.mkdir(parents=True,exist_ok=True)
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
NAMES={p['id']:p['name'] for p in json.loads((ROOT/'work/rocket/parts.json').read_text())}
COL={'ink':(0.035,0.07,0.10,1),'muted':(.28,.36,.40,1),'paper':(.93,.945,.94,1),
     'orange':(.95,.30,.075,1),'blue':(.065,.32,.48,1),'teal':(.04,.49,.47,1),
     'gray':(.43,.50,.53,1),'silver':(.66,.71,.72,1),'red':(.68,.12,.12,1),
     'black':(.045,.055,.065,1),'gold':(.66,.43,.16,1),'white':(.96,.97,.96,1)}
M={}

def material(k, flat=False):
    key=k+('_text' if flat else '')
    if key in M:return M[key]
    m=bpy.data.materials.new('Teaching_'+key);m.diffuse_color=COL[k]
    n=m.node_tree.nodes.get('Principled BSDF')
    n.inputs['Base Color'].default_value=COL[k]
    n.inputs['Roughness'].default_value=.58
    if k in ['silver','gold']:n.inputs['Metallic'].default_value=1
    if flat:
        m.node_tree.nodes.remove(n)
        n=m.node_tree.nodes.new('ShaderNodeEmission');n.inputs['Color'].default_value=COL[k]
        n.inputs['Strength'].default_value=1
        m.node_tree.links.new(n.outputs[0],m.node_tree.nodes.get('Material Output').inputs['Surface'])
    M[key]=m;return m

def box(name,loc,scale,k='blue',bevel=.08):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name
    o.dimensions=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material(k))
    if bevel:
        mod=o.modifiers.new('Soft teaching edges','BEVEL');mod.width=bevel;mod.segments=3
        mod=o.modifiers.new('Flat face normals','WEIGHTED_NORMAL')
    return o

def disc(name,x,y,r,k='orange',z=.35,depth=.22):
    bpy.ops.mesh.primitive_cylinder_add(vertices=80,radius=r,depth=depth,location=(x,y,z))
    o=bpy.context.object;o.name=name;o.data.materials.append(material(k))
    b=o.modifiers.new('Rounded edge','BEVEL');b.width=.035;b.segments=3
    o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o

def ring(name,x,y,ro,ri,k='orange',z=.45,depth=.16):
    n=96;v=[];faces=[]
    for zz in [z-depth/2,z+depth/2]:
        for r in [ro,ri]:
            v += [(x+r*math.cos(i*2*math.pi/n),y+r*math.sin(i*2*math.pi/n),zz) for i in range(n)]
    for i in range(n):
        j=(i+1)%n
        faces += [(i,j,2*n+j,2*n+i),(n+i,3*n+i,3*n+j,n+j),(i,n+i,n+j,j),(2*n+i,2*n+j,3*n+j,3*n+i)]
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(material(k))
    be=o.modifiers.new('Rounded ring edges','BEVEL');be.width=.025;be.segments=3
    o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o

def path(name,pts,k='orange',r=.07,z=.45):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=16
    s=cu.splines.new('BEZIER');s.bezier_points.add(len(pts)-1)
    for b,p in zip(s.bezier_points,pts):
        b.co=(p[0],p[1],p[2] if len(p)>2 else z);b.handle_left_type='AUTO';b.handle_right_type='AUTO'
    cu.bevel_depth=r;cu.bevel_resolution=3;cu.use_fill_caps=True
    o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);cu.materials.append(material(k));return o

def line(name,pts,k='muted',r=.018,z=1.6):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D'
    s=cu.splines.new('POLY');s.points.add(len(pts)-1)
    for q,p in zip(s.points,pts):q.co=(p[0],p[1],z,1)
    cu.bevel_depth=r;cu.bevel_resolution=2;cu.use_fill_caps=True
    o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);cu.materials.append(material(k,True));return o

def poly(name,pts,k='blue',z=.4,thick=.15):
    v=[(x,y,z) for x,y in pts]+[(x,y,z+thick) for x,y in pts];n=len(pts)
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me)
    bpy.context.collection.objects.link(o);o.data.materials.append(material(k));return o

def text(body,x,y,size=.30,k='ink',align='LEFT',z=2.4):
    cu=bpy.data.curves.new('Text_'+body,'FONT');cu.body=body;cu.size=size;cu.align_x=align
    cu.font=bpy.data.fonts.load(FONT,check_existing=True);cu.space_character=1.05
    o=bpy.data.objects.new('Label_'+body,cu);bpy.context.collection.objects.link(o);o.location=(x,y,z)
    cu.materials.append(material(k,True));return o

def label(body,x,y,target,side='LEFT',color='ink'):
    text(body,x,y,.32,color,side)
    tx=x+.10 if side=='LEFT' else x-.10
    line('Leader_'+body,[(tx,y-.17),(tx,y-.34),target],r=.015)
    disc('Label point',target[0],target[1],.045,'orange',z=1.65,depth=.01)

def arrow(name,a,b,k='orange',w=.045):
    line(name,[a,b],k,w,1.8)
    v=Vector((b[0]-a[0],b[1]-a[1]));v.normalize();n=Vector((-v.y,v.x))
    p=Vector(b);q=p-v*.24
    poly(name+'_tip',[p,q+n*.14,q-n*.14],k,z=1.78,thick=.01)

def module(name,x,y,w=1.3,h=.9,k='blue',ports='left'):
    box(name,(x,y,.35),(w,h,.5),k)
    sx=x-w/2-.08 if ports=='left' else x+w/2+.08
    for i in range(3):box(name+'_port_'+str(i),(sx,y+(i-1)*.18,.4),(.18,.10,.12),'gold',.015)

def screw(x,y):
    disc('Generic screw head',x,y,.23,'silver',z=.565,depth=.18)
    line('Cross slot A',[(x-.12,y),(x+.12,y)],'ink',.025,.70)
    line('Cross slot B',[(x,y-.12),(x,y+.12)],'ink',.025,.70)

def common(pid):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    M.clear();s=bpy.context.scene;s.render.engine='CYCLES'
    s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.max_bounces=3
    s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.film_transparent=False
    s.world.color=(.8,.8,.8);s.view_settings.view_transform='Standard';s.view_settings.look='None'
    s.view_settings.exposure=0;s.view_settings.gamma=1
    backdrop=box('Paper backdrop',(0,0,-.18),(17,11,.1),'paper',0)
    backdrop.data.materials.clear();backdrop.data.materials.append(material('paper',True))
    rule=box('Header rule',(-6.7,3.50,.05),(1.1,.055,.02),'orange',0)
    rule.data.materials.clear();rule.data.materials.append(material('orange',True))
    text(pid,-7.20,4.34,.24,'muted');text(NAMES[pid],-7.20,3.75,.48)
    text('功能示意 · 不代表原件外形或尺寸',-7.20,-4.35,.30,'ink')
    text('颜色仅用于教学区分',7.15,-4.34,.22,'muted','RIGHT')
    line('Footer separator',[(-7.2,-3.83),(7.2,-3.83)],'silver',.012,.05)
    bpy.ops.object.camera_add(location=(0,0,30));cam=bpy.context.object;cam.name='Diagram orthographic camera'
    cam.data.type='ORTHO';cam.data.ortho_scale=16.0;cam.rotation_euler=(0,0,0);s.camera=cam
    # Camera's local -Z already points toward the XY drawing plane.
    for name,loc,power,size in [('Key',(-5,6,10),1050,8),('Fill',(5,-2,8),500,7)]:
        bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.name=name;l.data.energy=power;l.data.shape='DISK';l.data.size=size
        l.rotation_euler=(Vector((0,0,0))-l.location).to_track_quat('-Z','Y').to_euler()
    s['diagram_status']='teaching_schematic';s['real_scale']='arbitrary teaching coordinates; no dimensions'
    s['identity_limit']='Not original CAD, product appearance, material color, pinout, rating or manufacturing evidence.'

def build(pid):
    common(pid)
    if pid=='A3-10':
        # Side section: a wide washer face sits between screw head and connected rocker.
        box('Connected rocker left',(-1.65,-.40,.37),(2.5,.72,.45),'blue')
        box('Connected rocker right',(1.65,-.40,.37),(2.5,.72,.45),'blue')
        box('Screw shank',(0,-.65,.55),(.58,2.85,.42),'gray',.04)
        box('Screw head',(0,.505,.58),(1.80,.65,.55),'silver',.12)
        box('Washer section left',(-.81,.07,.67),(1.02,.22,.24),'orange',.025)
        box('Washer section right',(.81,.07,.67),(1.02,.22,.24),'orange',.025)
        for yy in [-1.20,-.90,-.60,-.30,0]:line('Thread suggestion',[(-.28,yy),(.28,yy+.12)],'muted',.022,.9)
        label('螺钉头',-5.6,2.1,(-.75,.55))
        label('平垫圈：铺宽接触面',2.4,1.75,(.99,.07))
        label('被连接的摇臂',2.7,-1.7,(2.1,-.4))
    elif pid=='A3-11':
        module('Servo block',-4.8,.3,1.6,1.25,'blue',ports='right');disc('Servo output symbol',-4.8,.3,.36,'silver',z=.76)
        module('Controller block',5.0,.3,1.7,1.25,'gray')
        for i,k in enumerate(['black','red','orange']):
            yy=(i-1)*.17
            path('Distinct three-core extension '+k,[(-4.0,.3+yy),(-2.6,.3+yy),(-1.1,-.65+yy),(1.15,-.65+yy),(2.6,.3+yy),(4.15,.3+yy)],k,.065)
        box('Extension connector one',(-2.5,.3,.45),(.45,.8,.42),'black');box('Extension connector two',(2.7,.3,.45),(.45,.8,.42),'black')
        label('舵机',-6.2,2.05,(-4.8,.8));label('三芯联系延长',-1.8,2.0,(0,-.55));label('控制接口',3.8,2.05,(5,.8))
    elif pid=='A3-12':
        module('One compatible interface',-4.9,.25,1.6,1.1,'gray',ports='right')
        module('Servo upper',4.7,1.75,1.5,1.1);module('Servo lower',4.7,-1.55,1.5,1.1)
        for i,k in enumerate(['black','red','orange']):
            yy=(i-1)*.15
            path('Common incoming '+k,[(-4.1,.25+yy),(-2.2,.25+yy),(0,.25+yy)],k,.058)
            path('Branch upper '+k,[(0,.25+yy),(1.5,1.75+yy),(3.9,1.75+yy)],k,.058)
            path('Branch lower '+k,[(0,.25+yy),(1.5,-1.55+yy),(3.9,-1.55+yy)],k,.058)
        box('Insulated Y junction',(0,.25,.55),(.6,.65,.40),'black',.15)
        label('共同控制联系',-6.4,2.30,(-3.4,.25))
        label('分支到舵机 1',2.55,2.85,(4.0,1.75))
        label('分支到舵机 2',2.55,-2.6,(4.0,-1.55))
    elif pid=='A6-19':
        # Local layer section only; lower edges remain clear.
        box('Outer paper tube section',(0,1.37,.35),(9.6,.80,.45),'blue')
        box('Thin shimming tape',(0,.885,.47),(7.9,.17,.23),'orange',.025)
        box('Coupler section',(0,.35,.4),(8.0,.90,.42),'gray')
        label('外筒内表面',-6.7,2.65,(-3.5,1.37));label('胶带薄贴合层',1.9,2.65,(1.6,.885));label('连接筒外表面',-1.3,-1.75,(0,.35))
    elif pid=='A7-04':
        # Generic canopy, deliberately not a product reconstruction.
        pts=[(-2.4,1.0)]+[(-2.4+4.8*i/32,1.0+1.55*math.sin(math.pi*i/32)) for i in range(33)]+[(2.4,1.0)]
        poly('Generic inflated canopy',pts,'orange',z=.5,thick=.15)
        for xx in [-2.3,-1.15,0,1.15,2.3]:line('Generic shroud',[(xx,1.0),(0,-1.6)],'muted',.028,.7)
        box('Recovery body',(0,-2.30,.45),(.65,1.2,.4),'blue');path('Shock cord',[(0,-1.6),(0,-1.85)],'gray',.045)
        arrow('Drag upward',(-4.0,-.6),(-4.0,1.5),'teal',.065)
        arrow('Descent downward',(3.7,.8),(3.7,-1.1),'blue',.065)
        text('空气阻力',-5.95,1.75,.32,'teal');text('下降方向',3.0,1.75,.32,'blue')
        label('伞面与绳系',.8,2.85,(1.25,1.6))
    elif pid=='A7-14':
        # Two separate roles; no separating animation or assumed shear properties.
        box('Electronics board',(-3.5,.3,.35),(3.3,2.2,.25),'teal')
        for x in [-4.65,-2.35]:
            for y in [-.4,1.0]:screw(x,y)
        module('Electronic component',-3.5,.3,.8,.65,'black')
        box('Tube segment A',(2.7,.3,.35),(1.7,2.65,.35),'blue')
        box('Tube segment B',(4.5,.3,.35),(1.7,2.65,.35),'gray')
        line('Separable section boundary',[(3.6,-1.2),(3.6,1.8)],'orange',.045,.7)
        for y in [-.55,1.15]:screw(3.6,y)
        text('电子板固定',-5.4,2.25,.32);text('舱段临时约束',2.2,2.25,.32)
        text('分离作用须由具体设计验证',0,-2.25,.32,'orange','CENTER')
    elif pid=='B1-01':
        # Name and abstract material role, no container shape or operation.
        for xx,k in [(-4.7,'blue'),(-3.5,'blue'),(-2.3,'red')]:disc('Molecular concept sphere',xx,.6,.50,k,depth=.65)
        path('Molecular conceptual bond',[(-4.3,.6),(-2.7,.6)],'gray',.12,z=.35)
        box('Reaction role boundary',(2.6,.6,.34),(3.1,2.6,.35),'white')
        ring('Reaction participation symbol',2.6,.6,.78,.62,'orange')
        arrow('Role relation',(-.9,.6),(.65,.6),'blue',.05)
        text('N2O · 物质名称',-5.7,2.25,.34,'blue');text('氧化剂角色',-5.6,-1.25,.32)
        text('与燃料共同参与反应',1.0,2.25,.32)
    elif pid=='B1-02':
        # Droplet is a material-category icon, not an observed color sample.
        drop=[(-3.6,2.1)]+[(-3.6+1.10*math.cos(math.radians(150+240*i/48)),-.1+1.05*math.sin(math.radians(150+240*i/48))) for i in range(49)]
        poly('Generic mixed-fuel icon',drop,'orange',z=.5,thick=.25)
        for x,y,r,k in [(-3.8,.2,.22,'red'),(-3.3,-.4,.16,'gold'),(-3.75,-.65,.12,'white')]:disc('Mixed material symbol',x,y,r,k,z=.8,depth=.06)
        box('Reaction role boundary',(2.4,.5,.34),(3.1,2.6,.35),'white');ring('Shared reaction concept',2.4,.5,.78,.62,'orange')
        arrow('Role link',(-1.4,.5),(.45,.5),'orange',.05)
        text('E85 · 混合燃料',-5.7,2.5,.34,'orange');text('燃料的工作角色',-5.4,-2.15,.32)
        text('与氧化剂共同参与反应',.55,2.4,.32)
    elif pid=='B1-05':
        # Only the authorized signal → short energy → separation relationship.
        module('Recovery signal symbol',-5,.15,1.2,1.25,'blue')
        for i in range(3):line('Signal wave',[(-5.35+i*.16,-.1),(-5.35+i*.16,.45)],'white',.025,.8)
        poly('Abstract short energy symbol',[(-.3,1.55),(.7,1.55),(.15,.35),(.85,.35),(-.45,-1.35),(-.1,-.1),(-.75,-.1)],'orange',.5,.15)
        box('Separated section left',(3.8,.15,.4),(1.0,2.2,.4),'blue');box('Separated section right',(5.65,.15,.4),(1.0,2.2,.4),'gray')
        arrow('Signal to energy',(-3.9,.15),(-1.2,.15),'orange',.05);arrow('Energy to separation',(1.1,.15),(3.0,.15),'orange',.05)
        text('回收信号',-5.75,2.15,.34);text('短时能量',-.75,2.15,.34);text('舱段分开',3.7,2.15,.34)
    elif pid=='B1-06':
        glove=[(-2.4,-2.1),(-2.6,-.4),(-3.6,.75),(-3.5,1.12),(-3.15,1.22),(-2.45,.45),(-2.5,2.10),(-2.28,2.33),(-2.03,2.10),(-1.90,.85),(-1.65,2.58),(-1.40,2.70),(-1.17,2.48),(-1.22,.85),(-.78,2.25),(-.48,2.35),(-.30,2.05),(-.65,.62),(-.08,1.40),(.23,1.43),(.43,1.13),(-.42,-.55),(-.72,-2.1)]
        poly('Generic thin-film glove outline',glove,'teal',z=.4,thick=.09)
        line('Glove cuff',[(-2.4,-1.8),(-.8,-1.8)],'white',.035,.65)
        label('丁腈手套轮廓',-6.4,2.5,(-2.0,1.2))
        label('柔性薄膜',2.8,1.8,(-1.3,.1))
        text('原表：一次性辅助耗材',1.5,-1.35,.34)
    elif pid=='B1-07':
        # Partial covering exposes conductor concept without assembly instructions.
        for yy,k in [(.8,'red'),(-.8,'black')]:
            path('Insulated wire '+k,[(-5.3,yy),(-2.2,yy),(-1.0,yy),(1.0,yy),(2.2,yy),(5.3,yy)],k,.18)
            path('Conductor at generic joint '+k,[(-1.25,yy),(1.25,yy)],'gold',.12,z=.70)
            box('Insulating tape coverage '+k,(.75,yy,.83),(1.85,.58,.25),'blue',.12)
        label('金属导体',-5.8,2.25,(-1.0,.8));label('胶带绝缘边界',1.3,2.25,(1.0,.8))
        text('阻隔意外导电接触',0,-2.2,.34,'blue','CENTER')
    elif pid=='C1-04':
        box('Power source',(-5.4,.2,.35),(1.3,1.6,.5),'gray')
        box('Ground electrical module',(5.25,.2,.35),(1.5,1.6,.5),'blue')
        for yy,k in [(.65,'red'),(-.30,'black')]:
            path('Ground wire '+k,[(-4.75,yy),(-3.1,yy),(0,yy-.8),(3.0,yy),(4.5,yy)],k,.18)
        # Independent magnified section lets jacket and conductor be read together.
        disc('Magnified insulation cross section',.2,1.75,.65,'red',depth=.25)
        disc('Magnified conductor cross section',.2,1.75,.28,'gold',z=.55,depth=.18)
        label('电源 ↔ 电气模块',-6.5,2.6,(-5.3,.5));label('金属导体',1.8,2.85,(.2,1.75));label('红黑绝缘外皮',1.8,-2.1,(1.7,-.7))
    elif pid=='C1-10':
        # Ground equipment context differs from the on-rocket servo extension.
        box('Ground equipment tray',(0,.1,.1),(11.7,4.2,.16),'silver',.15)
        module('Ground receiver',-4.25,.2,1.45,1.3,'teal',ports='right');module('Ground control module',4.25,.2,1.45,1.3,'blue')
        for i,k in enumerate(['black','red','orange']):
            yy=(i-1)*.16
            path('Ground three-core extension '+k,[(-3.525,.2+yy),(-2.6,.2+yy),(-1.9,-1.0+yy),(1.9,-1.0+yy),(2.6,.2+yy),(3.525,.2+yy)],k,.06,z=.55)
        box('Ground inline connector',(-2.5,.05,.7),(.52,.82,.3),'black');box('Ground end connector',(2.5,.05,.7),(.52,.82,.3),'black')
        label('地面接收控制端',-6.6,2.65,(-4.25,.2));label('三芯电气延长',-1.4,2.7,(0,-1));label('相邻控制模块',3.3,2.65,(4.25,.2))
    elif pid=='C1-15':
        # Storage boundary is deliberately a conceptual field, no invented bottle silhouette.
        box('Ground storage conceptual field',(-3.15,.25,.22),(4.8,4.1,.15),'blue',.2)
        for x,y,r in [(-4.5,.8,.20),(-3.6,-.4,.28),(-2.7,1.2,.17),(-2.1,-.8,.22),(-4.4,-1.0,.15)]:disc('Stored material conceptual mark',x,y,r,'teal',z=.5,depth=.1)
        line('Ground baseline',[(-6.1,-2.15),(-.2,-2.15)],'gray',.07,.2)
        poly('Distant generic flight body',[(3.8,-1.3),(4.5,-1.3),(4.5,1.4),(4.15,2.1),(3.8,1.4)],'gray',z=.4,thick=.2)
        poly('Fin left',[(3.8,-.7),(3.25,-1.4),(3.8,-1.2)],'gray',z=.4,thick=.15)
        poly('Fin right',[(4.5,-.7),(5.05,-1.4),(4.5,-1.2)],'gray',z=.4,thick=.15)
        text('地面物料储存边界',-5.5,2.75,.34,'blue')
        text('留在地面',-4.2,-2.85,.34);text('随箭贮箱是另一边界',1.6,2.75,.32,'muted')
    elif pid=='C1-18':
        pts=[(-4.4,1.1),(-3.7,-.5),(-2.3,-1.45),(0,-1.2),(2.1,.4),(3.7,1.0),(4.4,.2)]
        path('Flexible internal passage',pts,'gray',.25)
        path('Conceptual fluid passage',pts,'blue',.12,z=.70)
        # Smooth conceptual braid: two crossing strand families follow the bent path.
        dense=[]
        for j in range(len(pts)-1):
            p0=Vector(pts[max(j-1,0)]);p1=Vector(pts[j]);p2=Vector(pts[j+1]);p3=Vector(pts[min(j+2,len(pts)-1)])
            for i in range(35):
                t=i/35
                p=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
                dense.append(p)
        dense.append(Vector(pts[-1]));arc=[0]
        for i in range(1,len(dense)):arc.append(arc[-1]+(dense[i]-dense[i-1]).length)
        for sign in [-1,1]:
            for phase in [0,2*math.pi/3,4*math.pi/3]:
                strand=[]
                for i,p in enumerate(dense):
                    d=(dense[min(i+1,len(dense)-1)]-dense[max(i-1,0)]).normalized();n=Vector((-d.y,d.x))
                    ang=sign*arc[i]*9+phase;q=p+n*.265*math.cos(ang)
                    strand.append((q.x,q.y,.55+.265*math.sin(ang)))
                path('Conceptual crossing braid',strand,'silver',.033)
        # Generic side-view connector bodies; no apparent washer rings or real thread details.
        for j in [0,-1]:
            p=Vector(pts[j]);d=(p-Vector(pts[1] if j==0 else pts[-2])).normalized();n=Vector((-d.y,d.x))
            outline=[(-.2,-.26),(.06,-.26),(.17,-.38),(.55,-.38),(.7,-.26),(.7,.26),(.55,.38),(.17,.38),(.06,.26),(-.2,.26)]
            xy=[p+d*u+n*v for u,v in outline]
            poly('Generic hose connection end',xy,'gold',z=.73,thick=.22)
            mouth=p+d*.70
            line('Generic connection end face',[mouth-n*.24,mouth+n*.24],'gray',.055,1.0)
        label('两端连接界面',-6.6,2.5,pts[0]);label('编织外层',-2.5,2.55,(-2.2,-1.43));label('可弯曲的内部通道',1.7,2.55,(2.05,.35))
    else:raise ValueError(pid)
    bpy.context.view_layer.update()
    s=bpy.context.scene
    s['part_id']=pid
    s['teaching_label_count']=3
    # Preserve all editable text; pack the loaded local font for portable editing.
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SRC/f'{pid}.blend'),compress=True)
    s.render.filepath=str(EVID/f'{pid}.png');bpy.ops.render.render(write_still=True)
    counts={'objects':len(s.objects),'meshes':sum(o.type=='MESH' for o in s.objects),'texts':[o.data.body for o in s.objects if o.type=='FONT']}
    print('RESULT '+json.dumps({'id':pid,'blend':str(SRC/f'{pid}.blend'),'png':s.render.filepath,'audit':counts},ensure_ascii=False),flush=True)

def main():
    ids=sys.argv[sys.argv.index('--')+1:]
    for pid in ids:build(pid)

if __name__=='__main__':main()
