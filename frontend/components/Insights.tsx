'use client';
import {useEffect,useState} from 'react';
type Restaurant={id:number;name:string;sample:boolean};
type Dish={name:string;price_paise:number;price_status?:string};
type Suggestion={restaurant:Restaurant;dish:Dish;reason?:string;appearances?:number};
type Analytics={cuisines:{label:string;count:number}[];dishes:{label:string;count:number}[];areas:{label:string;count:number}[];average_budget:number;funnel:{searches_with_results:number;searches_with_click:number;conversion_percent:number}};
const money=(value:number)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',minimumFractionDigits:value%100?2:0,maximumFractionDigits:2}).format(value/100);
export function FoodSuggestions({area,samples,signedIn,onSelect,revision}:{area:string;samples:boolean;signedIn:boolean;onSelect:(id:number)=>void;revision:number}){
 const [popular,setPopular]=useState<Suggestion[]>([]),[recommended,setRecommended]=useState<Suggestion[]>([]);
 useEffect(()=>{let active=true;fetch('/api/popular-dishes?include_samples='+samples).then(r=>r.ok?r.json():[]).then(rows=>{if(active)setPopular(rows)}).catch(()=>{});
 if(signedIn)fetch('/api/me/recommendations?area='+encodeURIComponent(area)+'&include_samples='+samples).then(r=>r.ok?r.json():[]).then(rows=>{if(active)setRecommended(rows)}).catch(()=>{});else setRecommended([]);
 return()=>{active=false};},[area,samples,signedIn,revision]);
 return <div className="two-column discovery-extras"><section className="panel"><h2>Popular dishes</h2><p className="subtle">Most frequently shown in recent searches. Sample dishes are labelled.</p>{popular.length?popular.map((row,index)=><button className="suggestion-row" key={row.restaurant.id+':'+index} onClick={()=>onSelect(row.restaurant.id)}><span>{row.restaurant.sample?'Sample · ':''}{row.dish.name}<small>{row.restaurant.name} · {row.appearances} search appearances{row.dish.price_status?' · '+row.dish.price_status:''}</small></span><b>{money(row.dish.price_paise)}</b></button>):<p>No dish trends yet. Search to explore the available menus.</p>}</section><section className="panel"><h2>Picked for you</h2>{signedIn?(recommended.length?recommended.map(row=><button className="suggestion-row" key={row.restaurant.id} onClick={()=>onSelect(row.restaurant.id)}><span>{row.restaurant.sample?'Sample · ':''}{row.dish.name}<small>{row.restaurant.name} · {row.reason}{row.dish.price_status?' · '+row.dish.price_status:''}</small></span><b>{money(row.dish.price_paise)}</b></button>):<p>No priced recommendations in this area yet.</p>):<p>Sign in and choose a favourite cuisine in Your space for personalised recommendations.</p>}</section></div>;
}
export function AnalyticsPanel(){
 const [data,setData]=useState<Analytics|null>(null);
 useEffect(()=>{fetch('/api/insights').then(r=>r.ok?r.json():null).then(setData).catch(()=>{})},[]);
 if(!data)return <p>Analytics are currently unavailable.</p>;
 return <section className="panel"><h2>Community appetite</h2><p>Average budget ₹{data.average_budget} · {data.funnel.conversion_percent}% of searches led to a restaurant click</p><p className="subtle">{data.funnel.searches_with_click} searches with an attributed click out of {data.funnel.searches_with_results} searches. A click is not a purchase.</p><div className="analytics-grid">{[{title:'Searched cuisines',rows:data.cuisines},{title:'Most requested dishes',rows:data.dishes},{title:'Popular search areas',rows:data.areas}].map(group=><div key={group.title}><h3>{group.title}</h3>{group.rows.length?group.rows.map(row=><div className="trend-row" key={row.label}><span>{row.label}</span><meter aria-label={row.label+' searches'} value={row.count} max={Math.max(...group.rows.map(r=>r.count),1)}/><b>{row.count}</b></div>):<p>No searches yet.</p>}</div>)}</div></section>;
}
export function CampaignPerformance({restaurantId,revision}:{restaurantId:number;revision:boolean}){
 const [data,setData]=useState<{funnel:{searches_with_results:number;searches_with_click:number;conversion_percent:number};campaigns:{id:number;title:string;reservations:number;discount_paise:number;reserved_order_paise:number}[]}|null>(null);
 useEffect(()=>{fetch('/api/portal/restaurants/'+restaurantId+'/performance').then(r=>r.ok?r.json():null).then(setData).catch(()=>{})},[restaurantId,revision]);
 if(!data)return null;
 return <section className="panel"><h2>Search and campaign performance</h2><p>{data.funnel.searches_with_results} searches displayed your restaurant · {data.funnel.searches_with_click} led to clicks · {data.funnel.conversion_percent}% conversion</p><p className="subtle">Only aggregate activity is shared. Reservations are not verified sales.</p>{data.campaigns.map(c=><div className="history-row" key={c.id}><span><b>{c.title}</b><small>{c.reservations} reservations · reserved order value {money(c.reserved_order_paise)}</small></span><span>{money(c.discount_paise)} discounts</span></div>)}</section>;
}
