import {Field,loadField,simulate} from './physics.mjs';
let field,model;
onmessage=async ({data})=>{
  try{
    if(data.type==='init'){
      model=data.model;
      if(data.packed){
        const arrays={},names=Object.keys(data.packed.files);let done=0;
        for(const name of names){
          const zipped=Uint8Array.from(atob(data.packed.files[name]),c=>c.charCodeAt(0));
          const raw=await new Response(new Blob([zipped]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
          const hex=[...new Uint8Array(await crypto.subtle.digest('SHA-256',raw))].map(x=>x.toString(16).padStart(2,'0')).join('');
          if(hex!==data.packed.manifest.files[name].sha256)throw Error('Ошибка контрольной суммы поля');
          arrays[name]=name.endsWith('.f32')?new Float32Array(raw):new Uint8Array(raw);postMessage({type:'progress',value:++done/names.length});
        }
        field=new Field(data.packed.manifest,arrays);
      }else field=await loadField('./data/',value=>postMessage({type:'progress',value}));
      postMessage({type:'ready'});
    }else if(data.type==='event'){
      const started=performance.now(),event=simulate(field,model,data.input);
      postMessage({type:'event',id:data.id,event,wall_ms:performance.now()-started});
    }
  }catch(error){postMessage({type:'error',message:error.message});}
};
