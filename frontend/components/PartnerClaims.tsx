'use client';
import {useState} from 'react';
import {apiRequest} from '../shared/api';
export function ClaimProfile({restaurantId}:{restaurantId:number}){
 const [reference,setReference]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 return <details className="portal-details"><summary>Claim this restaurant profile</summary><p>Claim review checks business credentials and control of the public business contact. Submission alone does not verify ownership.</p><form onSubmit={async event=>{event.preventDefault();setBusy(true);try{const result=await apiRequest<{notice:string}>('/partner/claim',{method:'POST',body:JSON.stringify({restaurant_id:restaurantId,business_reference:reference})});setMessage(result.notice)}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}}><label>FSSAI licence number or GSTIN<input value={reference} onChange={e=>setReference(e.target.value.trim().toUpperCase())} minLength={14} maxLength={15} required/></label><button className="primary" disabled={busy}>Submit profile claim</button></form>{message&&<p role="status">{message}</p>}</details>;
}
export function OfferCopilot({restaurantId,onApply}:{restaurantId:number;onApply:(value:{percent:number;min_searches:number;min_order_paise:number;max_discount_paise:number;daily_budget_paise:number;title:string;min_tier:string})=>void}){
 const [message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 return <div className="source-note"><strong>Saudagar offer copilot</strong><p>Get a bounded suggestion based on actual engagement. You review and publish it.</p><button type="button" className="secondary" disabled={busy} onClick={async()=>{setBusy(true);try{const result=await apiRequest<{suggestions:Parameters<typeof onApply>[0][];notice:string;impressions_30d:number}>('/portal/restaurants/'+restaurantId+'/offer-suggestions');if(result.suggestions[0])onApply(result.suggestions[0]);setMessage(result.impressions_30d+' search impressions in 30 days. '+result.notice)}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}}>Suggest a campaign</button>{message&&<p role="status">{message}</p>}</div>;
}
