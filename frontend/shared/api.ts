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
