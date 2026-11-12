'use client';
import {useEffect,useState,FormEvent} from 'react';
import {apiRequest} from '../shared/api';
type Coverage={real_restaurants:number;sample_restaurants:number;fresh_source_menu_items:number;last_successful_collection:string|null;coverage:string;attribution:string};
export function CatalogCoverage(){
 const [data,setData]=useState<Coverage|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[retry,setRetry]=useState(0);
 useEffect(()=>{
  let active=true;let version=0;let controller:AbortController|null=null;
  async function load(){
   const requestVersion=++version;controller?.abort();controller=new AbortController();setBusy(true);
   try{
    const next=await apiRequest<Coverage>('/catalog/coverage',{signal:controller.signal});
    if(typeof next.real_restaurants!=='number'||typeof next.fresh_source_menu_items!=='number')throw new Error('Invalid coverage');
    if(active&&requestVersion===version){setData(next);setError('')}
   }catch{if(active&&requestVersion===version)setError('Menu coverage could not be refreshed.')}
   finally{if(active&&requestVersion===version)setBusy(false)}
  }
  const refresh=()=>{if(document.visibilityState==='visible')void load()};
  void load();window.addEventListener('focus',refresh);window.addEventListener('biteai:catalog-updated',refresh);document.addEventListener('visibilitychange',refresh);
  return()=>{active=false;controller?.abort();window.removeEventListener('focus',refresh);window.removeEventListener('biteai:catalog-updated',refresh);document.removeEventListener('visibilitychange',refresh)};
 },[retry]);
 return <aside className="catalog-panel"><strong>Our Mumbai data collection</strong>{data?<><div className="catalog-numbers"><span><b>{data.real_restaurants}</b> real listings</span><span><b>{data.fresh_source_menu_items}</b> fresh source-backed menu prices</span><span><b>{data.sample_restaurants}</b> fictional samples</span></div><p>{data.coverage}</p><small>{data.last_successful_collection?'Last collection: '+new Date(data.last_successful_collection).toLocaleString():'No successful automated collection yet. Sample data is not real coverage.'}</small><small>{data.attribution}</small></>:<p>{busy?'Checking menu coverage…':'Menu coverage is temporarily unavailable.'}</p>}{error&&<p role="status">{error} <button type="button" disabled={busy} onClick={()=>setRetry(value=>value+1)}>Retry coverage</button></p>}</aside>;
}
type Job={id:number;state:string;attempts:number;error:string|null};
type Source={id:number;enabled:boolean;url:string;checked_at:string|null;jobs:Job[]};
export function SourceManager({restaurantId}:{restaurantId:number}){
 const [rows,setRows]=useState<Source[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const headers=()=>({'Content-Type':'application/json','X-BiteAI-Client':'browser'});
 async function load(){
  const r=await fetch('/api/portal/restaurants/'+restaurantId+'/sources',{headers:headers()});
  if(r.ok)setRows(await r.json());
 }
 useEffect(()=>{load().catch(()=>{});},[restaurantId]);
 async function updateSource(source:Source,refresh=false){
  setBusy(true);
  try{
   const r=await fetch('/api/portal/restaurants/'+restaurantId+'/sources/'+source.id+(refresh?'/refresh':''),{method:refresh?'POST':'PUT',headers:headers(),body:JSON.stringify(refresh?{}:{enabled:!source.enabled})});
   const data=await r.json();if(!r.ok)throw new Error(data.detail||'Source update failed');
   setMessage(data.message||(data.state==='running'?'Collection already running.':'Collection queued.'));await load();
  }catch(e){setMessage((e as Error).message)}finally{setBusy(false)}
 }
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const values=Object.fromEntries(new FormData(event.currentTarget));setBusy(true);
  try{
   const r=await fetch('/api/portal/restaurants/'+restaurantId+'/sources',{method:'POST',headers:headers(),body:JSON.stringify({...values,refresh_hours:24})});
   const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'Unable to register source');
   setMessage(data.message);await load();
  }catch(e){setMessage((e as Error).message)}finally{setBusy(false)}
 }
 return <section className="panel"><h2>Let the menu agent do the updating</h2><p className="subtle">Register an approved menu page on your restaurant website. The worker checks permission rules, extracts explicitly listed INR prices, records evidence and refreshes them daily. A site operator must allow the exact hostname in APPROVED_MENU_HOSTS first.</p><form onSubmit={submit}><label>Menu page (HTTPS)<input name="url" type="url" pattern="https://.*" required/></label><label>Permission to collect this page<input name="permission_note" minLength={10} placeholder="I operate this website and permit BiteAI menu collection" required/></label><button className="primary" disabled={busy}>Register source & queue collection</button></form>{message&&<p role="status">{message}</p>}<button className="text-button" onClick={()=>load().catch(()=>setMessage('Unable to load source jobs'))}>Refresh agent status</button>{rows.map(source=><div key={source.id} className="source-note"><strong>{source.url}</strong><p>{source.enabled?'Collection enabled':'Collection paused; prices withdrawn'}</p><button disabled={busy} onClick={()=>updateSource(source)}>{source.enabled?'Pause source':'Enable source'}</button><button disabled={busy||!source.enabled} onClick={()=>updateSource(source,true)}>Queue refresh</button><p>Last success: {source.checked_at?new Date(source.checked_at).toLocaleString():'Not collected yet'}</p>{source.jobs.map(job=><p key={job.id}>Job #{job.id}: {job.state} · {job.attempts} attempts{job.error?' · '+job.error:''}</p>)}</div>)}</section>;
}
