/** Normalize upstream warm-up/gateway responses without caching them as readiness. */
export async function searchHealth(upstream:string,fetcher:typeof fetch=fetch):Promise<Response>{
 const headers={'Cache-Control':'no-store, max-age=0','Content-Type':'application/json'};
 try{
  const response=await fetcher(upstream.replace(/\/$/,'')+'/health',{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000)});
  if(!response.ok||!response.headers.get('content-type')?.includes('json'))throw new Error('Not ready');
  const data=await response.json();
  if(!data||data.status!=='ok'||data.database!=='connected')throw new Error('Not ready');
  return Response.json(data,{headers});
 }catch{
  return Response.json({status:'unavailable',detail:'The search service is temporarily unreachable.'},{status:503,headers:{...headers,'Retry-After':'3'}});
 }
}
