'use client';
import {useEffect,useRef,useState} from 'react';
import {apiRequest} from '../shared/api';
type Voucher={id:string;restaurant_name:string;state:string;expires_at:string;amount_paise:number;discount_paise:number;test_mode:boolean;code:string|null};
export function MyVouchers({revision}:{revision:number}){
 const [rows,setRows]=useState<Voucher[]>([]),[message,setMessage]=useState('');
 useEffect(()=>{const controller=new AbortController();apiRequest<Voucher[]>('/me/vouchers',{signal:controller.signal}).then(setRows).catch(()=>{if(!controller.signal.aborted)setMessage('Vouchers could not be loaded. Refresh Your space to retry.')});return()=>controller.abort()},[revision]);
 return <section className="panel"><h2>Your deal vouchers</h2><p>Only a signed payment capture issues a voucher. Pending or cancelled checkouts cannot be redeemed.</p>{message&&<p role="status">{message}</p>}{rows.length?rows.map(row=><article className="voucher-card" key={row.id}><h3>{row.restaurant_name}</h3><p>{row.state} · ₹{row.amount_paise/100} paid · ₹{row.discount_paise/100} discount</p>{row.test_mode&&<strong className="sample-badge">TEST MODE · NO REAL MONEY MOVED</strong>}{row.state==='issued'&&row.code&&<><img src={'/api/me/vouchers/'+row.id+'/qr'} alt={'Redemption QR for '+row.restaurant_name} width={220} height={220}/><label>Voucher code<textarea readOnly value={row.code} aria-label={'Voucher code for '+row.restaurant_name}/></label><small>Show the restaurant this QR or code. Expires {new Date(row.expires_at).toLocaleString()}.</small></>}</article>):<p>No vouchers yet. Eligible restaurant checkout must be configured before you can buy a deal.</p>}</section>;
}
export function VoucherScanner(){
 const [code,setCode]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[camera,setCamera]=useState(false);
 const alive=useRef(true);const video=useRef<HTMLVideoElement>(null),stream=useRef<MediaStream|null>(null),timer=useRef<ReturnType<typeof setTimeout>|null>(null);
 function stop(){stream.current?.getTracks().forEach(track=>track.stop());stream.current=null;if(timer.current)clearTimeout(timer.current);setCamera(false)}
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;stream.current?.getTracks().forEach(track=>track.stop());if(timer.current)clearTimeout(timer.current)}},[]);
 async function scan(){
  type Detector={detect:(element:HTMLVideoElement)=>Promise<{rawValue:string}[]>};
  const C=(window as unknown as {BarcodeDetector?:new(options:{formats:string[]})=>Detector}).BarcodeDetector;
  if(!C){setMessage('Camera QR scanning is not supported in this browser. Paste the voucher code below.');return}
  try{const media=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false});if(!alive.current){media.getTracks().forEach(track=>track.stop());return}stream.current=media;setCamera(true);const detector=new C({formats:['qr_code']});
   const tick=async()=>{if(!stream.current)return;if(video.current){video.current.srcObject=stream.current;await video.current.play();const results=await detector.detect(video.current);if(!alive.current||!stream.current)return;if(results[0]){setCode(results[0].rawValue);stop();setMessage('QR read. Check the code, then redeem.');return}}timer.current=setTimeout(()=>void tick().catch(()=>{stop();setMessage('Camera scanning stopped. Paste the voucher code instead.')}),350)};timer.current=setTimeout(()=>void tick().catch(()=>{stop();setMessage('Camera could not read this QR. Paste the code instead.')}),100);
  }catch{stop();setMessage('Camera access is unavailable. Paste the voucher code instead.')}
 }
 return <section className="panel"><h2>Redeem a deal voucher</h2><p>Only vouchers paid for your restaurant can be redeemed, once. Refunds and disputes block redemption.</p><button className="secondary" onClick={()=>camera?stop():void scan()}>{camera?'Stop camera':'Scan voucher QR'}</button>{camera&&<video ref={video} playsInline muted className="voucher-camera"/>}<form onSubmit={async event=>{event.preventDefault();setBusy(true);try{const row=await apiRequest<Voucher>('/portal/vouchers/redeem',{method:'POST',body:JSON.stringify({code})});setMessage('Voucher redeemed for '+row.restaurant_name+(row.test_mode?' · TEST MODE, no real money moved.':'.'));setCode('')}catch(error){setMessage((error as Error).message)}finally{setBusy(false)}}}><label>Voucher code<textarea value={code} onChange={event=>setCode(event.target.value)} minLength={20} maxLength={2000} required/></label><button className="primary" disabled={busy}>{busy?'Checking voucher…':'Redeem voucher'}</button></form>{message&&<p role="status">{message}</p>}</section>;
}
