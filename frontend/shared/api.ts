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
   onWaiting();
   await new Promise(resolve=>setTimeout(resolve,Math.min(1500,Math.max(0,deadline-Date.now()))));
  }
  throw new ApiError('The search service could not start yet. Please try again in a moment.',503);
 })();
 try{await waking}finally{waking=null}
}
