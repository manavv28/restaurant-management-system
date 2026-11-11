'use client';
import {useEffect,useRef,useState} from 'react';
import type {Restaurant} from '../app/page';
type GMap={fitBounds:(bounds:unknown)=>void};
type GMarker={addListener:(event:string,callback:()=>void)=>void;map:GMap|null};
type GMaps={importLibrary:(name:string)=>Promise<unknown>;Map:new(el:HTMLElement,options:unknown)=>GMap;LatLngBounds:new()=>{extend:(point:{lat:number;lng:number})=>void};InfoWindow:new(options:unknown)=>{open:(options:unknown)=>void};marker:{AdvancedMarkerElement:new(options:unknown)=>GMarker}};
declare global{interface Window{google?:{maps:GMaps};biteaiMapsReady?:()=>void}}
let ready:Promise<void>|null=null;
function loadMaps(){
 if(window.google?.maps)return Promise.resolve();
 if(!ready)ready=new Promise<void>((resolve,reject)=>{
  window.biteaiMapsReady=()=>resolve();
  const script=document.createElement('script');script.src='https://maps.googleapis.com/maps/api/js?loading=async&libraries=marker&callback=biteaiMapsReady&key='+encodeURIComponent(process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY||'');
  script.onerror=()=>{script.remove();ready=null;reject(new Error('Google Maps could not load'))};document.head.appendChild(script);
 });
 return ready;
}
export default function GoogleMap({restaurants,onSelect}:{restaurants:Restaurant[];onSelect:(id:number)=>void}){
 const element=useRef<HTMLDivElement>(null),[error,setError]=useState('');
 useEffect(()=>{let active=true;const markers:GMarker[]=[];
 loadMaps().then(async()=>{const maps=window.google!.maps;await Promise.all([maps.importLibrary('maps'),maps.importLibrary('marker')]);if(!active||!element.current)return;
 const map=new maps.Map(element.current,{center:{lat:19.0596,lng:72.8295},zoom:12,mapId:process.env.NEXT_PUBLIC_GOOGLE_MAP_ID||'DEMO_MAP_ID'});
 const bounds=new maps.LatLngBounds();
 restaurants.forEach(restaurant=>{const position={lat:restaurant.latitude,lng:restaurant.longitude};bounds.extend(position);const marker=new maps.marker.AdvancedMarkerElement({map,position,title:restaurant.name});markers.push(marker);
 const button=document.createElement('button');button.textContent=restaurant.name;button.onclick=()=>onSelect(restaurant.id);const info=new maps.InfoWindow({content:button});marker.addListener('click',()=>info.open({map,anchor:marker}));});if(restaurants.length)map.fitBounds(bounds);
 }).catch(()=>{if(active)setError('Google Maps is unavailable. Use list view to explore restaurants.')});return()=>{active=false;markers.forEach(marker=>{marker.map=null})};},[restaurants,onSelect]);
 return <div><div className="map" aria-label="Interactive restaurant map" ref={element}/>{error&&<p role="status">{error}</p>}</div>;
}
