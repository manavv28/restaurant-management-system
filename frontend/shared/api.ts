'use client';
export class ApiError extends Error{
 constructor(message:string,public status:number){super(message);this.name='ApiError'}
}
export async function apiRequest<T>(path:string,options:RequestInit={},timeout=30000):Promise<T>{
 const timer=new AbortController();const id=setTimeout(()=>timer.abort(),timeout);
 const signal=options.signal?AbortSignal.any([options.signal,timer.signal]):timer.signal;
 try{
  const response=await fetch('/api'+path,{cache:'no-store',...options,signal,headers:{'Content-Type':'application/json','X-BiteAI-Client':'browser',...options.headers}});
  const text=await response.text();let data;
  try{
   if(!(response.headers.get('content-type')||'').includes('json'))throw new Error('Not JSON');
   data=JSON.parse(text);
  }catch{throw new ApiError('The service is temporarily unavailable or still starting. Please try again shortly.',response.status>=400?response.status:503)}
  if(!response.ok)throw new ApiError(typeof data?.detail==='string'?data.detail:'The request could not be completed. Please try again.',response.status);
  return data as T;
 }catch(error){
  if(options.signal?.aborted)throw error;
  if(timer.signal.aborted)throw new ApiError('The service is taking longer than expected. Please try again shortly.',504);
  if(error instanceof ApiError)throw error;
  throw new ApiError('Could not reach the service. Check your connection and try again.',503);
 }finally{clearTimeout(id)}
}
let readyUntil=0;let waking:Promise<void>|null=null;
export async function ensureSearchReady(onWaiting:()=>void){
 if(Date.now()<readyUntil)return;
 if(waking){onWaiting();return waking}
 waking=(async()=>{
  const deadline=Date.now()+90000;
  while(Date.now()<deadline){
   try{
    const health=await apiRequest<{status:string}>('/health',{},Math.min(12000,deadline-Date.now()));
    if(health.status==='ok'){readyUntil=Date.now()+10000;return}
   }catch(error){if(error instanceof ApiError&&error.status>=400&&error.status<500)throw error}
   // A successful catalog read also proves that the API and database are reachable.
   // Do not block a usable search solely on an unavailable health probe.
   const remaining=deadline-Date.now();
   if(remaining>0){
    try{
     const coverage=await apiRequest<{real_restaurants:number;fresh_source_menu_items:number}>('/catalog/coverage',{},Math.min(5000,remaining));
     if(Number.isInteger(coverage.real_restaurants)&&coverage.real_restaurants>=0&&typeof coverage.fresh_source_menu_items==='number'){
      readyUntil=Date.now()+10000;return;
     }
    }catch(error){if(error instanceof ApiError&&error.status>=400&&error.status<500)throw error}
   }
   onWaiting();
   await new Promise(resolve=>setTimeout(resolve,Math.min(1500,Math.max(0,deadline-Date.now()))));
  }
  throw new ApiError('Could not reach the search service. Check your connection and retry.',503);
 })();
 try{await waking}finally{waking=null}
}

export type QueryStep={event:string;agent?:string;message?:string;[key:string]:unknown};
export async function queryRequest<T>(body:unknown,onStep:(step:QueryStep)=>void,signal:AbortSignal):Promise<T>{
 const response=await fetch('/api/search',{method:'POST',cache:'no-store',signal:AbortSignal.any([signal,AbortSignal.timeout(30000)]),headers:{'Content-Type':'application/json','X-BiteAI-Client':'browser','Accept':'text/event-stream'},body:JSON.stringify(body)});
 const type=response.headers.get('content-type')||'';
 if(!type.includes('text/event-stream')){
  if(!type.includes('json'))throw new ApiError('The service is temporarily unavailable or still starting. Please try again shortly.',response.status>=400?response.status:503);
  const data=await response.json();if(!response.ok)throw new ApiError(typeof data.detail==='string'?data.detail:'Search could not finish. Please retry.',response.status);return data;
 }
 if(!response.ok||!response.body)throw new ApiError('Search could not start. Please retry.',response.status);
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',total=0,result:T|undefined;
 try{
  while(true){
   const {value,done}=await reader.read();if(done)break;
   total+=value.byteLength;if(total>2_000_000)throw new Error('Search response exceeded its limit');
   buffer+=decoder.decode(value,{stream:true}).replace(/\r\n/g,'\n');let split;
   while((split=buffer.indexOf('\n\n'))>=0){
    const frame=buffer.slice(0,split);buffer=buffer.slice(split+2);const event=frame.split('\n').find(line=>line.startsWith('event:'))?.slice(6).trim();const lines=frame.split('\n').filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart());
    if(!event||!lines.length)continue;
    const data=JSON.parse(lines.join('\n'));
    if(event==='error')throw new ApiError(data.message||'Search could not finish. Please retry.',503);
    if(event==='verdict')result=data as T;else onStep({event,...data});
   }
  }
  if(!result)throw new ApiError('Search ended before a verdict arrived. Please retry.',503);
  return result;
 }finally{await reader.cancel().catch(()=>{});reader.releaseLock()}
}
