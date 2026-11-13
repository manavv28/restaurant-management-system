'use client';
import {useState,type FormEvent} from 'react';

export type SearchIntent={cuisine:string|null;dish:string|null;max_budget:number;radius_km:number;location:string|null;unresolved_location?:string|null;diet:string|null;dietary_constraints?:string[];mode:string;party_size:number;budget_scope:string;open_now:boolean;walking_requested:boolean;excluded_dishes:string[];excluded_cuisines:string[]};
export type SearchOrigin={kind:'gps'|'area_centre'|'unresolved';label:string;distance_type:string};

export function SearchConstraints({intent,origin,area,areas,onApply,busy}:{intent:SearchIntent;origin?:SearchOrigin;area:string;areas:string[];onApply:(query:string)=>void;busy:boolean}){
 const [open,setOpen]=useState(false);
 function apply(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const data=new FormData(event.currentTarget);
  const place=String(data.get('area')||'');
  const query=[data.get('cuisine'),data.get('dish'),'under ₹'+data.get('budget'),'within '+data.get('radius')+' km',
   place?'in '+place:'',data.get('diet'),intent.mode==='any'?'':intent.mode,
   data.get('scope')==='total'?'total':'per item',intent.party_size>1?'for '+intent.party_size+' people':'',
   intent.open_now?'open now':'',intent.walking_requested?'walking distance':'',
   ...intent.excluded_dishes.map(term=>'no '+term),...intent.excluded_cuisines.map(term=>'no '+term)].filter(Boolean).join(' ');
  setOpen(false);onApply(query);
 }
 return <section className="search-constraints" aria-label="Interpreted search constraints">
  <div className="constraint-chips"><span>{intent.dish||intent.cuisine||'Any meal'}</span><span>Up to ₹{intent.max_budget}{intent.budget_scope==='total'?' total':' / item'}</span><span>{intent.radius_km} km straight-line</span><span>{origin?.label||area+' area centre'}</span>{(intent.dietary_constraints?.length?intent.dietary_constraints:(intent.diet?[intent.diet]:[])).map(diet=><span key={diet}>{diet}</span>)}<button type="button" className="text-button" disabled={busy} aria-expanded={open} aria-controls="constraint-editor" onClick={()=>setOpen(value=>!value)}>{open?'Close filters':'Edit search'}</button></div>
  {open&&<form id="constraint-editor" className="constraint-editor" onSubmit={apply}><label>Dish<input name="dish" defaultValue={intent.dish||''} maxLength={150}/></label><label>Cuisine<input name="cuisine" defaultValue={intent.cuisine||''} maxLength={100}/></label><label>Budget (₹)<input name="budget" type="number" min={1} max={100000} defaultValue={intent.max_budget} required/></label><label>Budget applies to<select name="scope" defaultValue={intent.budget_scope}><option value="item">Per item</option><option value="total">Total budget</option></select></label><label>Radius (km)<input name="radius" type="number" min={0.1} max={50} step={0.1} defaultValue={intent.radius_km} required/></label><label>Search location<select name="area" defaultValue={origin?.kind==='gps'?'':intent.location||area}>{origin?.kind==='gps'&&<option value="">Your shared GPS location</option>}{areas.map(value=><option key={value}>{value}</option>)}</select></label><label>Diet<select name="diet" defaultValue={intent.dietary_constraints?.includes('vegan')&&intent.dietary_constraints.includes('gluten-free')?'vegan gluten-free':intent.diet||''}><option value="">Any / undeclared</option><option value="vegetarian">Vegetarian</option><option value="jain">Jain</option><option value="halal">Halal</option><option value="vegan">Vegan</option><option value="gluten-free">Gluten-free</option><option value="vegan gluten-free">Vegan + gluten-free</option></select></label><button className="primary" disabled={busy}>Apply search filters</button></form>}
 </section>;
}
