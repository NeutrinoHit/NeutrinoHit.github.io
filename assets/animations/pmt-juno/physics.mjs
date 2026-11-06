// Units: mm, ns, V, T, eV. Electron charge is negative.
// Same node arrays, interpolation, Boris split and collision bisection as Python.
export const ACC = 0.1758820010758378;
export const OMEGA = 175.8820010758378;
export const ELECTRON_PC = 1.602176634e-7;
export const HC_EV_NM = 1239.841984332;
export const norm = v => Math.hypot(...v);
const dot = (a,b) => a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const unit = a => {const s=norm(a);return a.map(x=>x/s);};
const inside = (g,p) => p.every((x,i)=>x>g.interior_lo[i]&&x<g.interior_hi[i]);
export const speed = energy => Math.sqrt(2*ACC*energy);
export const energy = v => dot(v,v)/(2*ACC);

export class Random {
  constructor(seed=12860){this.state=seed>>>0;}
  uniform(){let t=this.state+=0x6D2B79F5;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return (((t^(t>>>14))>>>0)+0.5)/4294967296;}
  normal(){return Math.sqrt(-2*Math.log(this.uniform()))*Math.cos(2*Math.PI*this.uniform());}
  poisson(mu){
    if(!(mu>0))return 0;
    if(mu>50)return Math.max(0,Math.round(mu+Math.sqrt(mu)*this.normal()));
    const stop=Math.exp(-mu);let p=1,k=0;do{k++;p*=this.uniform();}while(p>stop);return k-1;
  }
}

export function interpolate(table,x){
  if(x<=table[0][0])return table[0][1];
  if(x>=table.at(-1)[0])return table.at(-1)[1];
  let lo=0,hi=table.length-1;
  while(hi-lo>1){const m=(lo+hi)>>1;if(table[m][0]>x)hi=m;else lo=m;}
  const f=(x-table[lo][0])/(table[hi][0]-table[lo][0]);return table[lo][1]*(1-f)+table[hi][1]*f;
}

export class Field {
  constructor(manifest, arrays){
    this.manifest=manifest;
    this.levels=manifest.levels.map(g=>({...g,phi:arrays[g.potential],lab:arrays[g.labels]}));
  }
  level(p){return inside(this.levels[2],p)?this.levels[2]:inside(this.levels[1],p)?this.levels[1]:this.levels[0];}
  label(p){
    const g=this.level(p),ij=p.map((x,k)=>Math.floor((x-g.origin[k])/g.h+.5));
    if(ij.some((x,k)=>x<0||x>=g.shape[k]))return 255;
    return g.lab[(ij[0]*g.shape[1]+ij[1])*g.shape[2]+ij[2]];
  }
  sample(p,scale=1){
    const g=this.level(p),h=g.h;
    const u=(p[0]-g.origin[0])/h,v=(p[1]-g.origin[1])/h,w=(p[2]-g.origin[2])/h;
    const i=Math.floor(u),j=Math.floor(v),k=Math.floor(w),[nx,ny,nz]=g.shape;
    if(i<0||j<0||k<0||i>=nx-1||j>=ny-1||k>=nz-1)return null;
    const a=u-i,b=v-j,c=w-k,idx=(i*ny+j)*nz+k,f=g.phi;
    const f000=f[idx],f100=f[idx+ny*nz],f010=f[idx+nz],f110=f[idx+(ny+1)*nz];
    const f001=f[idx+1],f101=f[idx+ny*nz+1],f011=f[idx+nz+1],f111=f[idx+(ny+1)*nz+1];
    const ex=-((1-b)*(1-c)*(f100-f000)+b*(1-c)*(f110-f010)+(1-b)*c*(f101-f001)+b*c*(f111-f011))/h*scale;
    const ey=-((1-a)*(1-c)*(f010-f000)+a*(1-c)*(f110-f100)+(1-a)*c*(f011-f001)+a*c*(f111-f101))/h*scale;
    const ez=-((1-a)*(1-b)*(f001-f000)+a*(1-b)*(f101-f100)+(1-a)*b*(f011-f010)+a*b*(f111-f110))/h*scale;
    const potential=((1-a)*(1-b)*(1-c)*f000+a*(1-b)*(1-c)*f100+(1-a)*b*(1-c)*f010+a*b*(1-c)*f110+
      (1-a)*(1-b)*c*f001+a*(1-b)*c*f101+(1-a)*b*c*f011+a*b*c*f111)*scale;
    return {e:[ex,ey,ez],potential,h};
  }
}

function rotate(v,t){
  const t2=dot(t,t);if(!t2)return v;
  const s=t.map(x=>2*x/(1+t2)),a=cross(v,t),w=v.map((x,i)=>x+a[i]),b=cross(w,s);
  return v.map((x,i)=>x+b[i]);
}

export function track(field,position,velocity,options={}){
  const {scale=1,B=[0,0,0],ignore=0,dtMax=.1,cfl=.3,tMax=180,record=true}=options;
  let p=[...position],v=[...velocity],t=0,armed=false,lastRecord=-1;
  const path=record?[[0,...p]]:[];
  const finish=(label)=>{if(record)path.push([t,...p]);return {p,v,t,label,path,energy:energy(v)};};
  for(let n=0;n<400000;n++){
    const f=field.sample(p,scale);if(!f)return finish(255);
    const am=ACC*norm(f.e),sp=norm(v);
    const dt=Math.max(1e-5,Math.min(dtMax,sp>1e-12?cfl*f.h/sp:dtMax,am>1e-12?Math.sqrt(cfl*f.h/am):dtMax));
    const rot=B.map(x=>-.25*dt*OMEGA*x);
    let vm=v.map((x,i)=>x-.5*dt*ACC*f.e[i]);vm=rotate(vm,rot);
    const pn=p.map((x,i)=>x+vm[i]*dt),vp=rotate(vm,rot),fn=field.sample(pn,scale);
    const vn=vp.map((x,i)=>x-(fn?.e[i]||0)*.5*dt*ACC);
    let label=field.label(pn);if(label===1)label=0;
    if(label===0)armed=true;
    else if(armed||label!==ignore){
      let lo=0,hi=1;
      for(let j=0;j<14;j++){
        const m=(lo+hi)/2,L=field.label(p.map((x,i)=>x+m*(pn[i]-x)));
        if(L===0||L===1||(!armed&&L===ignore))lo=m;else hi=m;
      }
      p=p.map((x,i)=>x+lo*(pn[i]-x));v=v.map((x,i)=>x+lo*(vn[i]-x));t+=lo*dt;
      return finish(label);
    }
    p=pn;v=vn;t+=dt;
    if(record&&t-lastRecord>(f.h<1?.07:.22)){path.push([t,...p]);lastRecord=t;}
    if(t>tMax)return finish(254);
  }
  return finish(253);
}

export function cosineDirection(n,rng){
  const a=Math.abs(n[2])<.9?[0,0,1]:[1,0,0],u=unit(cross(n,a)),v=cross(n,u);
  const s=Math.sqrt(rng.uniform()),c=Math.sqrt(1-s*s),phi=2*Math.PI*rng.uniform();
  return n.map((x,i)=>c*x+s*(Math.cos(phi)*u[i]+Math.sin(phi)*v[i]));
}

export function domePoint(model,theta,phi){
  const r=interpolate(model.dome,Math.abs(theta));return [r*Math.sin(theta)*Math.cos(phi),r*Math.sin(theta)*Math.sin(phi),r*Math.cos(theta)];
}
export function domeNormal(model,theta,phi){
  const a=domePoint(model,theta-.001,0),b=domePoint(model,theta+.001,0);
  return unit([(b[2]-a[2])*Math.cos(phi),(b[2]-a[2])*Math.sin(phi),-(b[0]-a[0])]);
}

export function activeNormal(model,label,p){
  const a=model.arcs.find(a=>a.label===label);
  if(!a)return null;
  if(label===3&&Math.abs(p[1])>model.geometry.box_w/2-Math.max(model.geometry.thick,.5))return [0,-Math.sign(p[1]),0];
  return unit([a.cx-p[0],0,a.cz-p[2]]);
}

export function activeHit(model,label,p,v){
  if(label===13)return true;
  const a=model.arcs.find(a=>a.label===label);if(!a)return false;
  const n=activeNormal(model,label,p),angle=((Math.atan2(p[2]-a.cz,p[0]-a.cx)*180/Math.PI-a.lo)%360+360)%360;
  const width=a.width??(label<=4?model.geometry.box_w:model.geometry.chain_w);
  const face=Math.hypot(p[0]-a.cx,p[2]-a.cz)<a.radius&&angle<=a.hi-a.lo&&Math.abs(p[1])<width/2;
  const end=label===3&&Math.abs(p[1])>model.geometry.box_w/2-Math.max(model.geometry.thick,.5);
  return (face||end)&&dot(v,n)<0;
}

export function qe(model,wavelength){
  return wavelength<300||wavelength>660?0:interpolate(model.qe_curve,wavelength);
}

export function pulse(arrivals,settings){
  const {resistance_ohm:R,tau_ns:tau,step_ns:dt}=settings;
  let charge=0,first=Infinity,mean=0;
  for(const a of arrivals){charge+=a.weight;mean+=a.weight*a.time;first=Math.min(first,a.time);}
  if(!charge)return {samples:[],charge_pc:0,centroid_ns:null,peak_mv:0,cfd_ns:null};
  mean/=charge;
  const end=Math.max(...arrivals.map(a=>a.time))+16*tau;
  const start=Math.max(0,first-10),samples=[];
  // Integral of h(t) = t^2 exp(-t/tau)/(2 tau^3) for t>=0 is one.
  for(let t=start;t<=end;t+=dt){
    let current=0;for(const a of arrivals){const x=t-a.time;if(x>=0)current+=a.weight*x*x*Math.exp(-x/tau)/(2*tau**3);}
    samples.push([t,-R*ELECTRON_PC*current]); // pC/ns = mA, mA*ohm = mV
  }
  const peak=Math.min(...samples.map(s=>s[1]));let cfd=null;
  for(let i=1;i<samples.length;i++)if(samples[i][1]<=peak*.5){
    const [ta,ya]=samples[i-1],[tb,yb]=samples[i];cfd=ta+(peak*.5-ya)*(tb-ta)/(yb-ya);break;
  }
  return {samples,charge_pc:-charge*ELECTRON_PC,centroid_ns:mean,peak_mv:peak,cfd_ns:cfd};
}

export function simulate(field,model,input={}){
  const opt={...model.config.simulation,...input},rng=new Random(opt.seed),scale=opt.voltage/field.manifest.reference_v_total;
  const B=[0,opt.magnetic_uT*1e-6,0],theta=opt.theta_deg*Math.PI/180,phi=opt.phi_deg*Math.PI/180;
  const p0=domePoint(model,theta,phi),normal=domeNormal(model,theta,phi);
  const q=qe(model,opt.wavelength_nm),converted=opt.conditioned!==false||rng.uniform()<q;
  const result={input:opt,qe:q,converted,photon_energy_ev:HC_EV_NM/opt.wavelength_nm,start:p0,normal,
    tracks:[],stages:[],arrivals:[],lost:0,backside:0,packets:opt.packets};
  if(!converted){result.signal=pulse([],model.config.signal);return result;}
  const v0=cosineDirection(normal,rng).map(x=>x*speed(opt.photoelectron_energy_ev));
  const first=track(field,p0,v0,{scale,B,ignore:1,dtMax:.25,cfl:.4,tMax:800});
  result.tracks.push({...first,start:0,weight:1,from:1});
  result.first=first;
  const buckets=Array.from({length:14},()=>[]);
  if(first.label>=3&&first.label<=12)buckets[first.label].push({...first,time:first.t,weight:1});
  else result.lost=1;
  const refVolt=field.manifest.electrode_potentials_at_reference;
  const k=model.yield_exponent,c=model.yields_nominal[0]/refVolt['3']**k*(opt.yield_scale??model.gain_calibration?.yield_scale??1);
  for(let label=3;label<=12;label++){
    const parents=buckets[label],children=[];let total=0,incident=0,backside=0;
    for(const hit of parents){
      incident+=hit.weight;
      const n=activeNormal(model,label,hit.p);
      // A reflecting dynode emits into the vacuum on its active concave side.
      // Convex-side hits are absorbed; no through-metal shortcut is permitted.
      if(!activeHit(model,label,hit.p,hit.v)){result.lost+=hit.weight;result.backside+=hit.weight;backside+=hit.weight;continue;}
      const yieldMean=c*Math.max(hit.energy,0)**k;
      const count=rng.poisson(hit.weight*yieldMean);
      if(count>0){total+=count;children.push({hit,n,count,end:total});}
    }
    const count=Math.min(Math.round(total),opt.packets),weight=count?total/count:0;
    let delivered=0,anode=0;const off=rng.uniform();
    for(let j=0,ix=0;j<count;j++){
      const target=(j+off)*weight;while(children[ix].end<target)ix++;
      const {hit,n}=children[ix],ev=-opt.secondary_kT_ev*Math.log(rng.uniform()*rng.uniform());
      const velocity=cosineDirection(n,rng).map(x=>x*speed(ev));
      const visibleLimit=opt.visible_per_stage?.[label-3]??24;
      const tr=track(field,hit.p,velocity,{scale,B,ignore:0,record:j<visibleLimit});
      if(j<visibleLimit)result.tracks.push({...tr,start:hit.time,weight,from:label});
      const time=hit.time+tr.t;
      if(tr.label===13){result.arrivals.push({time,weight});anode+=weight;}
      else if(tr.label>label&&tr.label<=12){buckets[tr.label].push({...tr,time,weight});delivered+=weight;}
      else result.lost+=weight;
    }
    result.stages.push({label,incident,emitted:total,delivered,anode,backside,packets:count});
  }
  result.signal=pulse(result.arrivals,model.config.signal);
  return result;
}

export async function loadField(base='./data/',progress=()=>{}){
  const get=async path=>{const r=await fetch(path);if(!r.ok)throw Error(`Не удалось загрузить ${path}: ${r.status}`);return r;};
  const manifest=await(await get(base+'manifest.json')).json(),arrays={};let done=0;
  const files=Object.keys(manifest.files);
  await Promise.all(files.map(async name=>{
    const res=await get(base+name+'.gz');
    const raw=await new Response(res.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
    const hex=[...new Uint8Array(await crypto.subtle.digest('SHA-256',raw))].map(x=>x.toString(16).padStart(2,'0')).join('');
    if(hex!==manifest.files[name].sha256)throw Error(`Нарушена целостность поля: ${name}`);
    arrays[name]=name.endsWith('.f32')?new Float32Array(raw):new Uint8Array(raw);
    progress(++done/files.length);
  }));
  return new Field(manifest,arrays);
}
