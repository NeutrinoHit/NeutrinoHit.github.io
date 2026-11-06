import * as THREE from './vendor/three.module.js';
import {domePoint,domeNormal} from './physics.mjs';
const to3=p=>new THREE.Vector3(p[0],p[2],p[1]);
const mix=(a,b,f)=>a.map((x,i)=>x+(b[i]-x)*f);
const clamp=x=>Math.max(0,Math.min(1,x));
function glowTexture(){
  const c=document.createElement('canvas');c.width=c.height=128;const x=c.getContext('2d');
  const g=x.createRadialGradient(64,64,0,64,64,64);g.addColorStop(0,'#ffffffff');g.addColorStop(.09,'#ffffffe0');g.addColorStop(.22,'#ffffff45');g.addColorStop(.55,'#ffffff12');g.addColorStop(1,'#ffffff00');x.fillStyle=g;x.fillRect(0,0,128,128);return new THREE.CanvasTexture(c);
}
export function dynodeGeometry(a,thickness){
  const shape=new THREE.Shape(),th=thickness/2,n=64;
  for(let i=0;i<=n;i++){const r=a.radius+th,t=(a.lo+(a.hi-a.lo)*i/n)*Math.PI/180,x=a.cx+r*Math.cos(t),y=a.cz+r*Math.sin(t);if(i===0)shape.moveTo(x,y);else shape.lineTo(x,y);}
  for(let i=n;i>=0;i--){const r=a.radius-th,t=(a.lo+(a.hi-a.lo)*i/n)*Math.PI/180;shape.lineTo(a.cx+r*Math.cos(t),a.cz+r*Math.sin(t));}shape.closePath();
  const geom=new THREE.ExtrudeGeometry(shape,{depth:a.width,bevelEnabled:false,steps:1,curveSegments:64});geom.translate(0,0,-a.width/2);return geom;
}
export class PMTScene{
  constructor(model,host){
    this.model=model;this.host=host;this.event=null;this.time=-1;this.chapter=0;this.cut=true;this.drawing=false;this.rotation=0;this.elevation=.16;this.zoom=1;this.labels=[];
    this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true,powerPreference:'high-performance'});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.renderer.setSize(innerWidth,innerHeight);
    this.renderer.setClearColor(0x061019,1);this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.35;
    host.append(this.renderer.domElement);this.world=new THREE.Scene();this.camera=new THREE.PerspectiveCamera(34,1,.05,6000);
    this.world.add(new THREE.HemisphereLight(0xa1d4e5,0x172329,2.3));
    const key=new THREE.DirectionalLight(0xc5e7ef,4.5);key.position.set(130,400,450);this.world.add(key);
    const rim=new THREE.DirectionalLight(0xffd59a,3);rim.position.set(-450,150,-150);this.world.add(rim);
    const fill=new THREE.DirectionalLight(0x43bce7,2.1);fill.position.set(400,-80,-300);this.world.add(fill);
    this.hardware=new THREE.Group();this.shells=new THREE.Group();this.housing=new THREE.Group();this.world.add(this.hardware,this.shells,this.housing);
    this.metal=new THREE.MeshStandardMaterial({color:0xa2bbc6,metalness:.72,roughness:.32,side:THREE.DoubleSide});
    this.gold=new THREE.MeshStandardMaterial({color:0xa8884d,metalness:.55,roughness:.4,side:THREE.DoubleSide,transparent:true,opacity:.32,depthWrite:false});
    this.glass=new THREE.MeshPhysicalMaterial({color:0x8fc9d7,metalness:.1,roughness:.17,transparent:true,opacity:.095,side:THREE.DoubleSide,depthWrite:false});
    this.edges=new THREE.LineBasicMaterial({color:0x6f9aaa,transparent:true,opacity:.37});
    this.makeHardware();this.makeShell();this.tex=glowTexture();
    this.trails=new THREE.Group();this.world.add(this.trails);
    this.dots=new THREE.Points(new THREE.BufferGeometry(),new THREE.PointsMaterial({color:0x70f1f0,size:13,map:this.tex,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,sizeAttenuation:false}));this.world.add(this.dots);
    this.photon=new THREE.Sprite(new THREE.SpriteMaterial({map:this.tex,color:0xffd584,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending}));this.world.add(this.photon);
    this.wave=new THREE.Line(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0xf6cf85,transparent:true,opacity:.8}));this.world.add(this.wave);
    this.impact=new THREE.Sprite(new THREE.SpriteMaterial({map:this.tex,color:0x9cffff,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending}));this.world.add(this.impact);
    this.makeLabels();this.bindOrbit();this.resize();
    addEventListener('resize',()=>this.resize());
  }
  line(points,color=0x6f9aaa,opacity=.45,parent=this.hardware){
    const g=new THREE.BufferGeometry().setFromPoints(points);
    const l=new THREE.Line(g,new THREE.LineBasicMaterial({color,transparent:true,opacity}));parent.add(l);return l;
  }
  makeShell(){
    this.shells.clear();const m=this.model;
    const points=m.bulb.map(([z,r])=>new THREE.Vector2(r,z));
    const theta=this.cut?Math.PI/2:0,length=this.cut?Math.PI:Math.PI*2;
    this.shells.add(new THREE.Mesh(new THREE.LatheGeometry(points,160,theta,length),this.glass));
    const upper=(m.bulb_inner||m.bulb).filter(([z])=>z>=0).map(([z,r])=>new THREE.Vector2(r,z));
    this.shells.add(new THREE.Mesh(new THREE.LatheGeometry(upper,160,theta,length),this.gold));
    for(const side of [-1,1])this.line(m.bulb.map(([z,r])=>new THREE.Vector3(side*r,z,0)),0xa9cbd6,.48,this.shells);
    for(const z of [0,-214,-279]){
      const nearest=m.bulb.reduce((a,b)=>Math.abs(b[0]-z)<Math.abs(a[0]-z)?b:a),r=nearest[1];
      this.line(Array.from({length:121},(_,i)=>new THREE.Vector3(r*Math.sin(theta+length*i/120),z,r*Math.cos(theta+length*i/120))),0x8eafba,.25,this.shells);
    }
    // Drawing dimensions are attached to the measured glass outline.
    this.dimensions=new THREE.Group();this.shells.add(this.dimensions);
    this.line([new THREE.Vector3(-254,215,0),new THREE.Vector3(254,215,0)],0x6ab6c6,.7,this.dimensions);
    for(const x of [-254,254])this.line([new THREE.Vector3(x,202,0),new THREE.Vector3(x,227,0)],0x6ab6c6,.7,this.dimensions);
    this.line([new THREE.Vector3(-285,-425,0),new THREE.Vector3(-285,186,0)],0x6ab6c6,.7,this.dimensions);
    this.dimensions.visible=this.drawing;
  }
  makeHardware(){
    const m=this.model,p=m.geometry;
    this.dynodes=new Map();
    for(const a of m.arcs){
      const geom=dynodeGeometry(a,p.thick);
      const mat=this.metal.clone();if(a.label===3)mat.color.set(0xb39d6f);if(a.label===13)mat.color.set(0x78bbb1);
      const mesh=new THREE.Mesh(geom,mat);this.hardware.add(mesh);this.dynodes.set(a.label,mesh);
      const edge=new THREE.LineSegments(new THREE.EdgesGeometry(geom,35),new THREE.LineBasicMaterial({color:a.label===3?0xdec78b:0xb3d4de,transparent:true,opacity:.34}));this.hardware.add(edge);
    }
    // The first dynode's end walls close the box in the same way as geometry.py.
    const zt=Math.max(p.rb*Math.sin(p.a_lip*Math.PI/180),p.z_up+Math.max(0,p.rd2-p.rd))-1;
    const shape=new THREE.Shape(),dx=p.stack_dx,zs=m.stack_z,xr=p.x2+p.rd2;
    shape.moveTo(dx,zs-p.rb);shape.lineTo(dx+xr,zs-p.rb);shape.lineTo(dx+xr,zs+zt);
    const at=Math.PI-Math.asin(zt/p.rb);shape.lineTo(dx+p.rb*Math.cos(at),zs+zt);
    for(let i=1;i<=80;i++){const t=at+(1.5*Math.PI-at)*i/80;shape.lineTo(dx+p.rb*Math.cos(t),zs+p.rb*Math.sin(t));}shape.closePath();
    const wallMat=this.metal.clone();wallMat.color.set(0x7c8771);wallMat.transparent=true;wallMat.opacity=.3;wallMat.depthWrite=false;
    const wall=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:p.thick,bevelEnabled:false}),wallMat);wall.position.z=-p.box_w/2;wall.userData.kind='dynode-box-endwall';this.boxEndwall=wall;this.hardware.add(wall);
    const conePoints=m.focus_segments.flatMap((seg,i)=>i?seg.slice(1):seg).map(([r,z])=>new THREE.Vector2(r,z));
    const focusMat=this.metal.clone();focusMat.transparent=true;focusMat.opacity=.28;focusMat.depthWrite=false;
    this.focus=conePoints.length>1?new THREE.Mesh(new THREE.LatheGeometry(conePoints,120,Math.PI/2,Math.PI),focusMat):new THREE.Group();this.housing.add(this.focus);
    for(const [r,z] of m.focus_segments.flat()){
      this.line(Array.from({length:81},(_,i)=>new THREE.Vector3(r*Math.sin(Math.PI/2+Math.PI*i/80),z,r*Math.cos(Math.PI/2+Math.PI*i/80))),0x96b5bf,.5,this.housing);
    }
    const shield=new THREE.Mesh(new THREE.CylinderGeometry(p.r_can,p.r_can,p.z_ap-p.z_can_bot,100,1,true,Math.PI/2,Math.PI),focusMat.clone());shield.position.y=(p.z_ap+p.z_can_bot)/2;shield.material.opacity=.11;this.housing.add(shield);
    const lid=new THREE.Mesh(new THREE.RingGeometry(p.r_ap,p.r_can,96,1,Math.PI,Math.PI),focusMat.clone());lid.rotation.x=Math.PI/2;lid.position.y=p.z_ap;lid.material.opacity=.2;this.housing.add(lid);
    for(const [x,z] of m.grid_wires){
      const wire=new THREE.Mesh(new THREE.CylinderGeometry(p.d_g/2,p.d_g/2,p.box_w,8),this.metal);wire.rotation.x=Math.PI/2;wire.position.set(x,z,0);this.hardware.add(wire);
    }
    for(const [label,x0,z0,x1,z1] of m.shield_segments){
      const a=new THREE.Vector3(x0,z0,-p.chain_w/2-2),b=new THREE.Vector3(x1,z1,-p.chain_w/2-2);
      this.line([a,b],0x3c6270,.6,this.housing);
    }
    // Supports and contact pins are shown as a schematic construction detail.
    const stem=-425;
    for(let i=0;i<20;i++){
      const a=i/20*2*Math.PI,r=24,pin=new THREE.Mesh(new THREE.CylinderGeometry(1.4,1.4,22,8),this.metal);
      pin.position.set(r*Math.cos(a),stem-8,r*Math.sin(a));this.hardware.add(pin);
    }
    const base=new THREE.Mesh(new THREE.CylinderGeometry(38,38,12,80),new THREE.MeshStandardMaterial({color:0x19323e,roughness:.55,metalness:.25}));base.position.y=stem+3;this.hardware.add(base);
  }
  addLabel(text,sub,p,chapters){
    const el=document.createElement('div');el.className='label';el.innerHTML=`${text}<b>${sub}</b>`;document.querySelector('#labels').append(el);this.labels.push({el,p:to3(p),chapters});
  }
  makeLabels(){
    const p=this.model.geometry,a=this.model.arcs;
    this.addLabel('ФОТОКАТОД','свет → электрон',[160,0,120],[0,1,2]);
    if(this.model.focus_segments.length)this.addLabel('ФОКУСИРУЮЩИЙ ЭЛЕКТРОД','электронная линза',[p.r_top,0,p.z_top],[0,2]);
    this.addLabel('ДИНОДНАЯ СИСТЕМА','Box & Line',[93,0,p.z_ap-40],[0]);
    this.addLabel('ПЕРВЫЙ ДИНОД','вторичная эмиссия',[a[0].cx-a[0].radius*.35,0,a[0].cz-a[0].radius],[3]);
    this.addLabel('АНОД','сбор заряда',[a.at(-1).cx+10,0,a.at(-1).cz],[4,5]);
    this.addLabel('Ø 508 ± 8 мм','чертёж Hamamatsu',[5,0,215],['drawing']);
    for(const arc of a.slice(1,-1))this.addLabel(`D${arc.label-2}`,`${Math.round(this.model.potentials[arc.label])} В`, [arc.cx,0,arc.cz+(arc.label%2?13:-13)],[4]);
  }
  bindOrbit(){
    let down=null;
    this.host.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];this.host.setPointerCapture(e.pointerId);});
    this.host.addEventListener('pointermove',e=>{if(!down)return;this.rotation+=(e.clientX-down[0])*.006;this.elevation=Math.max(-.7,Math.min(.8,this.elevation+(e.clientY-down[1])*.004));down=[e.clientX,e.clientY];});
    this.host.addEventListener('pointerup',()=>down=null);
    this.host.addEventListener('wheel',e=>{e.preventDefault();this.zoom=Math.max(.5,Math.min(2,this.zoom*Math.exp(e.deltaY*.001)));},{passive:false});
  }
  resize(){
    this.renderer.setSize(innerWidth,innerHeight);const film=document.body.classList.contains('film'),mobile=innerWidth<700;
    if(mobile)this.rect={x:0,y:film?innerHeight*.34:310,w:innerWidth,h:film?innerHeight*.38:330};
    else if(film)this.rect={x:innerWidth*.27,y:105,w:innerWidth*.72,h:innerHeight-350};
    else this.rect={x:innerWidth*.25,y:100,w:innerWidth*.50,h:innerHeight-360};
    this.camera.aspect=this.rect.w/this.rect.h;this.camera.updateProjectionMatrix();
  }
  setEvent(event){
    this.event=event;
    for(const child of [...this.trails.children]){child.geometry.dispose();child.material.dispose();this.trails.remove(child);}
    for(const tr of event.tracks){
      if(tr.path.length<2)continue;
      const line=this.line(tr.path.map(s=>to3(s.slice(1))),tr.from===1?0x7df0ed:0x58d3da,tr.from===1?.65:.15,this.trails);
      line.userData.track=tr;
    }
  }
  cameraPose(chapter){
    const a=this.model.arcs,p=this.model.geometry;
    const poses=[{p:[0,-95,0],d:1150},{p:[0,100,0],d:570},{p:[0,-55,0],d:680},
      {p:[a[0].cx+8,a[0].cz-8,0],d:180},{p:[(a[1].cx+a.at(-1).cx)/2+5,a[1].cz-5,0],d:150},
      {p:[a.at(-1).cx-18,a.at(-1).cz,0],d:155},{p:[0,-95,0],d:1150}];
    return poses[Math.max(0,Math.min(6,chapter))];
  }
  draw(time,chapter=0,transition=null){
    this.time=time;this.chapter=chapter;let pose=this.cameraPose(chapter);
    if(transition){const a=this.cameraPose(transition.from),b=this.cameraPose(transition.to);pose={p:mix(a.p,b.p,transition.f),d:a.d+(b.d-a.d)*transition.f};}
    const angle=this.rotation+.18,dist=pose.d*this.zoom;
    this.camera.position.set(pose.p[0]+Math.sin(angle)*dist,pose.p[1]+Math.sin(this.elevation)*dist,Math.cos(angle)*Math.cos(this.elevation)*dist);
    this.camera.lookAt(...pose.p);this.camera.updateMatrixWorld();
    this.housing.visible=chapter<3||chapter===6;this.shells.visible=chapter<3||chapter===6;
    for(const [label,mesh] of this.dynodes){mesh.material.wireframe=this.drawing;mesh.material.emissive.set(0x0b7779);mesh.material.emissiveIntensity=0;}
    const points=[];let flash=0,flashPos=null;
    if(this.event){
      const e=this.event;
      for(const line of this.trails.children){
        const tr=line.userData.track,age=time-tr.start;
        let k=0;while(k<tr.path.length&&tr.path[k][0]<=age)k++;
        line.geometry.setDrawRange(0,k);line.visible=age>=0&&(tr.from!==1||chapter<4);
        line.material.opacity=(tr.from===1?.75:.25)*(chapter===0?.4:1);
        if(k>0&&k<tr.path.length){
          const a=tr.path[k-1],b=tr.path[k],f=clamp((age-a[0])/(b[0]-a[0]));points.push(...mix(a.slice(1),b.slice(1),f).map((v,i,arr)=>i===0?v:i===1?arr[2]:arr[1]));
        }
        const impactAge=age-tr.t;
        if(impactAge>=0&&impactAge<.7&&tr.label>=3&&tr.label<=13){
          const mesh=this.dynodes.get(tr.label);if(mesh)mesh.material.emissiveIntensity=Math.max(mesh.material.emissiveIntensity,.8*(1-impactAge/.7));
          if(1-impactAge/.7>flash){flash=1-impactAge/.7;flashPos=tr.p;}
        }
      }
      this.dots.geometry.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
      const theta=e.input.theta_deg*Math.PI/180,phi=e.input.phi_deg*Math.PI/180,n=domeNormal(this.model,theta,phi);
      let tangent=new THREE.Vector3(-Math.sin(phi),Math.cos(phi),0),nn=new THREE.Vector3(...n);
      const inc=e.input.incidence_deg*Math.PI/180,dir=nn.multiplyScalar(Math.cos(inc)).add(tangent.multiplyScalar(Math.sin(inc))).toArray();
      const photonDist=Math.max(0,-time)*299.792458;
      const ph=e.start.map((x,i)=>x-dir[i]*photonDist);
      this.photon.position.copy(to3(ph));this.photon.scale.setScalar(chapter===0?32:14);this.photon.visible=time<=0&&time>=-1.3;
      const wave=[];for(let j=0;j<120;j++){
        const s=(j/119-.5)*65,waveAmp=4*Math.sin(j/119*Math.PI*12)*Math.exp(-(((j/119-.5)*3)**2));
        wave.push(to3(ph.map((x,i)=>x+s*dir[i]+(i===0?waveAmp:0))));
      }
      this.wave.geometry.dispose();this.wave.geometry=new THREE.BufferGeometry().setFromPoints(wave);this.wave.visible=this.photon.visible;
      if(time>=0&&time<1.2){flash=Math.max(flash,1-time/1.2);flashPos=e.start;}
      this.impact.visible=!!flashPos;if(flashPos){this.impact.position.copy(to3(flashPos));this.impact.scale.setScalar((chapter<3?42:10)*(1+.8*(1-flash)));this.impact.material.opacity=flash*.85;}
    }
    const r=this.rect;this.renderer.setViewport(0,0,innerWidth,innerHeight);this.renderer.clear();this.renderer.setViewport(r.x,innerHeight-r.y-r.h,r.w,r.h);this.renderer.render(this.world,this.camera);
    for(const l of this.labels){
      const visible=(l.chapters.includes(chapter)||(this.drawing&&l.chapters.includes('drawing')))&&!(chapter===4&&l.el.textContent.startsWith('D')&&innerWidth<900)&&!(innerWidth<700&&chapter===0&&!l.el.textContent.startsWith('ФОТОКАТОД'));
      const q=l.p.clone().project(this.camera),x=r.x+(q.x+1)/2*r.w,y=r.y+(1-q.y)/2*r.h;
      l.el.style.display=visible&&q.z<1&&x>r.x&&x<r.x+r.w-30&&y>r.y&&y<r.y+r.h?'block':'none';l.el.style.left=`${Math.min(x,r.x+r.w-l.el.offsetWidth-8)}px`;l.el.style.top=`${y}px`;
    }
  }
}
