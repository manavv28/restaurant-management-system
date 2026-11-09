'use client';
import {useEffect,useRef,useState} from 'react';
import type {Restaurant} from '../app/page';
import 'leaflet/dist/leaflet.css';
export default function Map({restaurants,onSelect}:{restaurants:Restaurant[];onSelect:(id:number)=>void}) {
 const el=useRef<HTMLDivElement>(null);const [tilesUnavailable,setTilesUnavailable]=useState(false);
 useEffect(()=>{let disposed=false;let map:import('leaflet').Map|undefined;
 import('leaflet').then(L=>{if(disposed||!el.current)return;
 map=L.map(el.current).setView([19.0596,72.8295],12);
 L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19}).on('tileerror',()=>setTilesUnavailable(true)).addTo(map);
 const points: [number,number][]=[];
 restaurants.forEach(r=>{points.push([r.latitude,r.longitude]);const marker=L.circleMarker([r.latitude,r.longitude],{radius:11,color:'#fff',weight:3,fillColor:'#e95c38',fillOpacity:1}).addTo(map!); const popup=document.createElement('button');popup.textContent=r.name;popup.onclick=()=>onSelect(r.id);marker.bindPopup(popup);const node=marker.getElement();if(node){node.setAttribute('role','button');node.setAttribute('tabindex','0');node.setAttribute('aria-label','Map marker: '+r.name);node.addEventListener('keydown',e=>{if((e as KeyboardEvent).key==='Enter')marker.openPopup()});}});
 if(points.length)map.fitBounds(L.latLngBounds(points),{padding:[40,40],maxZoom:14});
 });return()=>{disposed=true;map?.remove()};},[restaurants,onSelect]);
 return <div className="map-wrapper"><div ref={el} className="map" aria-label="Interactive restaurant map"/>{tilesUnavailable&&<p className="map-warning" role="status">Street map tiles are unavailable on this network. Restaurant markers still show their coordinates; use list view for full details.</p>}</div>;
}
