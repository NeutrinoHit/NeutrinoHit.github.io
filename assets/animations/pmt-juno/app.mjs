import {PMTScene} from './scene.mjs';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const params=new URLSearchParams(location.search),film=params.has('film');
if(film)document.body.classList.add('film');
const embedded=window.PMT_EMBEDDED;
const model=embedded?.model??await(await fetch('./data/model.json')).json();
if(embedded)document.querySelector('.brand img').src=embedded.brand;
let scene;
try{scene=new PMTScene(model,$('#scene'));}
catch(error){$('#loading-text').textContent='Для интерактива нужен WebGL 2. Откройте страницу в современном браузере.';throw error;}
let event=null,time=-1,playing=false,chapter=0,request=0,seed=model.config.simulation.seed,tour=false,tourTime=0,last=performance.now(),busy=false;
const workerURL=embedded?URL.createObjectURL(new Blob([embedded.worker],{type:'text/javascript'})):'./worker.mjs';
const worker=new Worker(workerURL,{type:embedded?'classic':'module'}),eventWaiters=new Map();
const fmt=(x,n=1)=>Number.isFinite(x)?x.toFixed(n):'—';
const compact=n=>n>=1e6?`${fmt(n/1e6,2)} млн`:n>=1000?`${fmt(n/1000,1)} тыс.`:fmt(n,0);
const bindings=[['voltage','voltage',' В'],['wavelength','wavelength_nm',' нм'],['theta','theta_deg','°'],['phi','phi_deg','°'],['incidence','incidence_deg','°'],['magnetic','magnetic_uT',' мкТл']];
function input(){const out={seed,packets:model.config.simulation.packets,conditioned:$('#conditioned').checked};for(const [id,key] of bindings)out[key]=Number($('#'+id).value);return out;}
function updateOutputs(){for(const [id,,unit] of bindings)$('#'+id+'-value').textContent=$('#'+id).value+unit;}
function setBusy(value){busy=value;$('#fire').disabled=value;$('#compute-state').textContent=value?'Считаем траектории…':'Готово';}
function calculate(overrides={}){
  const id=++request;setBusy(true);const state={...input(),...overrides};
  worker.postMessage({type:'event',id,input:state});
  return new Promise((resolve,reject)=>eventWaiters.set(id,{resolve,reject}));
}
function installEvent(e){
  event=e;scene.setEvent(e);time=-.32;
  const sig=e.signal,n=Math.abs(sig.charge_pc)/1.602176634e-7;
  $('#gain').textContent=compact(n);$('#charge').textContent=`Q = ${fmt(sig.charge_pc,3)} пКл`;
  $('#transit').textContent=`Среднее время ${fmt(sig.centroid_ns)} нс`;
  $('#qe-label').textContent=`QE ≈ ${fmt(e.qe*100,0)}% · пример EA0077. Eγ = ${fmt(e.photon_energy_ev,2)} эВ`;
  $('#time').max=String(Math.max(140,(sig.centroid_ns||95)+50));
  $('#visual-scale').textContent=`Расчёт: до ${e.packets} макрочастиц на ступень · показана выборка`;
  for(const l of scene.labels){const found=l.el.childNodes[0]?.textContent.match(/^D(\d+)$/);if(found)l.el.querySelector('b').textContent=`${Math.round(model.potentials[Number(found[1])+2]*e.input.voltage/2000)} В`;}
  draw();
}
worker.onmessage=({data})=>{
  if(data.type==='progress')$('#loading progress').value=data.value;
  if(data.type==='ready')calculate().catch(showError);
  if(data.type==='event'){
    const waiter=eventWaiters.get(data.id);eventWaiters.delete(data.id);waiter?.resolve(data.event);
    if(data.id===request){installEvent(data.event);setBusy(false);$('#loading').style.opacity=0;setTimeout(()=>$('#loading').style.display='none',650);window.pmt.ready=true;}
  }
  if(data.type==='error')showError(Error(data.message));
};
worker.onerror=e=>showError(Error(e.message));
function showError(error){setBusy(false);$('#loading').style.display='flex';$('#loading').style.opacity=1;$('#loading-text').textContent=`Не удалось выполнить расчёт: ${error.message}`;for(const w of eventWaiters.values())w.reject(error);eventWaiters.clear();}
worker.postMessage({type:'init',model,packed:embedded?.packed});

function setChapter(index,seek=true){
  chapter=index;
  const c=model.texts.chapter[index],short=film&&innerWidth<700;$('#eyebrow').textContent=c.eyebrow;$('#title').textContent=short?c.short_title:c.title;$('#body').textContent=short?c.short_body:c.body;$('#formula').textContent=c.formula;
  $$('#chapters button').forEach((b,i)=>b.classList.toggle('active',i===index));
  if(seek&&event){
    const td=event.first?.t||55,ta=event.signal.centroid_ns||105;
    time=[-.6,1,td*.52,td+1,td+(ta-td)*.55,ta+7,ta+35][index];
  }
}

function drawScope(){
  const canvas=$('#scope'),rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio,2);
  const w=Math.max(1,Math.round(rect.width*dpr)),h=Math.max(1,Math.round(rect.height*dpr));
  if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);const W=w/dpr,H=h/dpr;ctx.clearRect(0,0,W,H);
  const vals=event?.signal.samples||[],mean=event?.signal.centroid_ns||100,lo=Math.max(0,mean-20),hi=mean+55;
  const peak=Math.max(5,Math.abs(event?.signal.peak_mv||0)*1.25),top=12,bottom=H-17;
  const X=t=>30+(t-lo)/(hi-lo)*(W-40),Y=v=>top-v/peak*(bottom-top);
  ctx.lineWidth=.65;ctx.font='8px Arial';ctx.fillStyle='#6c8897';ctx.strokeStyle='#203945';
  for(let v=0;v<=2;v++){const y=top+(bottom-top)*v/2;ctx.beginPath();ctx.moveTo(30,y);ctx.lineTo(W-10,y);ctx.stroke();ctx.fillText(`${fmt(-peak*v/2,0)}`,0,y+3);}
  for(let t=Math.ceil(lo/10)*10;t<hi;t+=10){const x=X(t);ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();ctx.fillText(fmt(t,0),x-8,H-3);}
  ctx.fillText('мВ',0,8);ctx.fillText('нс',W-13,H-3);
  if(vals.length){
    ctx.strokeStyle='#6ce7e5';ctx.lineWidth=1.6;ctx.shadowColor='#4dccd0';ctx.shadowBlur=5;ctx.beginPath();let started=false;
    for(const [t,v] of vals){if(t<lo||t>hi||t>time)continue;const x=X(t),y=Y(v);if(!started){ctx.moveTo(x,y);started=true;}else ctx.lineTo(x,y);}ctx.stroke();ctx.shadowBlur=0;
  }
  if(time>=lo&&time<=hi){ctx.strokeStyle='#eec16b';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(X(time),top);ctx.lineTo(X(time),bottom);ctx.stroke();}
}
function status(){
  if(!event)return 'Ожидание';if(time<0)return 'Фотон приближается';if(!event.converted)return 'Фотоэлектрон не возник';
  if(time<(event.first?.t||0))return 'Фотоэлектрон в электрическом поле';
  if(!event.signal.samples.length)return 'Каскад погас · заряда на аноде нет';
  if(time<event.signal.centroid_ns)return 'Вторичная эмиссия · каскад';return 'Электрический импульс';
}
function draw(transition=null){
  scene.draw(time,chapter,transition);$('#clock').textContent=fmt(Math.max(0,time));$('#time').value=time;$('#event-state').textContent=status();drawScope();
  const count=$('#cascade-count');count.style.display=(chapter===3||chapter===4)&&event?'block':'none';
  if(event){
    let latest=null;for(const stage of event.stages){const starts=event.tracks.filter(t=>t.from===stage.label).map(t=>t.start).sort((a,b)=>a-b);if(starts.length&&starts[Math.floor(starts.length/2)]<=time)latest=stage;}
    if(latest){$('#cascade-stage').textContent=`ПОСЛЕ ДИНОДА D${latest.label-2}`;$('#cascade-number').textContent=compact(latest.emitted);}else{$('#cascade-stage').textContent='ДО ПЕРВОГО УДАРА';$('#cascade-number').textContent='1';}
    if(film){const n=event.arrivals.reduce((s,a)=>s+(a.time<=time?a.weight:0),0);$('#gain').textContent=compact(n);$('#charge').textContent=`Q = ${fmt(-n*1.602176634e-7,3)} пКл`;}
  }
}
const bounds=model.config.film.chapter_seconds;
function filmFrame(seconds,duration=140){
  const t=Math.max(0,Math.min(140,seconds*140/duration));let ch=6;for(let i=0;i<7;i++)if(t<bounds[i+1]){ch=i;break;}
  const f=Math.min(1,(t-bounds[ch])/(bounds[ch+1]-bounds[ch]));
  const d1=event?.first?.t||55,anode=event?.signal.centroid_ns||105;
  const ranges=[[-.3,0],[0,3],[3,d1-.5],[d1-.5,d1+8],[d1+8,anode+3],[anode+3,anode+34],[anode+34,anode+40]];
  time=ranges[ch][0]+(ranges[ch][1]-ranges[ch][0])*f;setChapter(ch,false);
  const blend=Math.min(1,(t-bounds[ch])/2.5),smooth=blend*blend*(3-2*blend);
  scene.rotation=.08*Math.sin(t*.028);scene.elevation=ch===4?.09:.16;scene.zoom=1;
  draw(ch>0&&blend<1?{from:ch-1,to:ch,f:smooth}:null);
  return {chapter:ch,physical_ns:time,anode_electrons:event?.arrivals.reduce((s,a)=>s+a.weight,0)||0,charge_pc:event?.signal.charge_pc};
}
function animate(now){
  const dt=Math.min(.05,(now-last)/1000);last=now;
  if(!film){
    if(tour){tourTime+=dt;filmFrame(tourTime);if(tourTime>=140){tour=false;playing=false;}}
    else{if(playing){time+=dt*(time<0?.18:6);if(time>Number($('#time').max))playing=false;}draw();}
    $('#play').textContent=playing||tour?'Ⅱ':'▶';
  }
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);

bindings.forEach(([id])=>$('#'+id).addEventListener('input',updateOutputs));
$('#fire').onclick=async()=>{seed++;tour=false;await calculate();playing=true;};
$('#play').onclick=()=>{tour=false;playing=!playing;};
$('#time').oninput=()=>{tour=false;playing=false;time=Number($('#time').value);};
$('#tour').onclick=()=>{tour=true;tourTime=0;playing=false;};
$('#explore').onclick=()=>{tour=false;setChapter(0);$('.controls').scrollIntoView({behavior:'smooth',block:'center'});$('#voltage').focus({preventScroll:true});};
$$('#chapters button').forEach(b=>b.onclick=()=>{tour=false;playing=false;setChapter(Number(b.dataset.chapter));scene.rotation=0;scene.zoom=1;});
$('#cut').onchange=()=>{scene.cut=$('#cut').checked;scene.makeShell();};
$('#drawing').onchange=()=>{scene.drawing=$('#drawing').checked;scene.dimensions.visible=scene.drawing;};
$('#reset-view').onclick=()=>{scene.rotation=0;scene.elevation=.16;scene.zoom=1;};
$$('[data-preset]').forEach(b=>b.onclick=async()=>{
  $('#voltage').value=2000;$('#theta').value=25;$('#magnetic').value=0;
  if(b.dataset.preset==='earth')$('#magnetic').value=50;if(b.dataset.preset==='edge')$('#theta').value=75;
  updateOutputs();tour=false;await calculate();playing=true;
});
$('#about').onclick=()=>$('#model-dialog').showModal();$('#close-dialog').onclick=()=>$('#model-dialog').close();
$('#model-dialog').onclick=e=>{if(e.target===$('#model-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}};
for(const src of model.sources){const a=document.createElement('a');a.textContent=src.title+' ↗';a.href=src.url;a.target='_blank';a.rel='noopener';$('#sources').append(a);}
const validation=model.validation;
$('#numerics').textContent=validation?`Независимая проверка (${validation.n} фотоэлектронов): средний gain ${(validation.mean_gain/1e6).toFixed(2)} ± ${(validation.gain_standard_error/1e6).toFixed(2)} млн (SE), средний центроид ${validation.mean_centroid_ns.toFixed(1)} нс. TTS по 50% CFD ≈ ${validation.cfd_fwhm_ns.toFixed(1)} нс; паспортные 2.4 нс не достигнуты. Сетки 4/2/0.5 мм; при сгущении до 0.25 мм перенос заряда меняется примерно на треть. Реконструкция не является предсказательной моделью серийного прибора.`:'Поле: вложенные сетки 4 / 2 / 0.5 мм. Точность серийного прибора из этого расчёта не следует.';
function download(name,data,type){const blob=new Blob([data],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
$('#export').onclick=()=>event&&download('pmt-event.json',JSON.stringify({model:'R12860 parametric reconstruction, opaque electrodes',...event},null,2),'application/json');
$('#download-drawing').onclick=()=>{if(embedded){download('r12860-model.svg',embedded.drawing,'image/svg+xml');return;}const a=document.createElement('a');a.href='./data/drawing.svg';a.download='r12860-model.svg';a.click();};
window.pmt={ready:false,model,scene,get event(){return event;},calculate,
  frame:filmFrame,setChapter:i=>{setChapter(i);draw();},setTime:t=>{time=t;draw();},
  check:()=>({ready:!!event,webgl:scene.renderer.capabilities.isWebGL2,tracks:event?.tracks.length,finite:event?.tracks.every(t=>Number.isFinite(t.t)&&t.p.every(Number.isFinite)),signal:event?.signal.charge_pc,overflow:document.documentElement.scrollWidth>innerWidth+1})};
