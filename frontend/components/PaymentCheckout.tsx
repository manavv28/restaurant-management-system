'use client';
import {FormEvent,useEffect,useState} from 'react';

type Order={test_mode?:boolean;order_id:string;key_id:string;amount_paise:number;currency:string};
type CheckoutOptions={key:string;order_id:string;amount:number;currency:string;name:string;handler:()=>void;modal:{ondismiss:()=>void}};
type CheckoutConstructor=new(options:CheckoutOptions)=>{open:()=>void};
declare global {interface Window {Razorpay?:CheckoutConstructor}}
let checkoutScript:Promise<void>|null=null;
function loadCheckout(){
 if(window.Razorpay)return Promise.resolve();
 if(!checkoutScript)checkoutScript=new Promise<void>((resolve,reject)=>{
  const script=document.createElement('script');script.src='https://checkout.razorpay.com/v1/checkout.js';
  script.onload=()=>window.Razorpay?resolve():reject(new Error('Checkout unavailable'));
  script.onerror=()=>{script.remove();checkoutScript=null;reject(new Error('Unable to load payment checkout'))};
  document.head.appendChild(script);
 });
 return checkoutScript;
}
async function paymentRequest<T>(path:string,options:RequestInit={}):Promise<T>{
 const response=await fetch('/api/payments'+path,{...options,headers:{'Content-Type':'application/json','X-BiteAI-Client':'browser'}});
 const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Payment request failed');return data;
}
export default function PaymentCheckout({restaurantId,consent,onVerified,campaignId,initialAmount}:{campaignId?:number;initialAmount?:number;restaurantId:number;consent:boolean;onVerified:()=>Promise<void>}){
 const [enabled,setEnabled]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[order,setOrder]=useState<Order|null>(null);
 useEffect(()=>{let active=true;paymentRequest<{enabled:boolean}>('/availability/'+restaurantId).then(data=>{if(active)setEnabled(data.enabled)}).catch(()=>{});return()=>{active=false};},[restaurantId]);
 async function checkStatus(value:Order){
  try{
   const status=await paymentRequest<{state:string;test_mode?:boolean}>('/orders/'+value.order_id);
   if(status.state==='captured'){setMessage(status.test_mode?'Test payment verified. No real money moved. Your voucher is in Your space.':'Payment verified by the provider webhook.');await onVerified()}
   else setMessage('Awaiting the signed provider webhook. No verified spending has been credited yet.');
  }catch(error){setMessage((error as Error).message)}
 }
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();setBusy(true);setMessage('');
  const rupees=String(new FormData(event.currentTarget).get('amount'));
  const amount=Math.round(Number(rupees)*100);
  try{
   await loadCheckout();
   const value=await paymentRequest<Order>('/orders',{method:'POST',body:JSON.stringify({restaurant_id:restaurantId,amount_paise:amount,campaign_id:campaignId})});
   setOrder(value);
   const checkout=new window.Razorpay!({key:value.key_id,order_id:value.order_id,amount:value.amount_paise,currency:value.currency,name:'BiteAI',
    handler:()=>{setBusy(false);void checkStatus(value)},modal:{ondismiss:()=>{setBusy(false);setMessage('Checkout closed. Check order status before trying another payment.')}}});
   checkout.open();
  }catch(error){setBusy(false);setMessage((error as Error).message)}
 }
 if(!enabled)return campaignId?<section className="panel"><h3>Deal checkout is not configured</h3><p>This restaurant needs payment-provider onboarding before BiteAI can issue a paid voucher. The offer is a preview; no payment or voucher has been created.</p></section>:null;
 return <section className="panel"><h3>{campaignId?'Get a test-mode deal voucher':'Test checkout'}</h3><strong className="sample-badge">RAZORPAY TEST MODE · NO REAL MONEY MOVES</strong><p>Confirm your bill with the restaurant. Payment opens in Razorpay checkout; only its signed webhook verifies spending.</p><form onSubmit={submit}><label>Bill amount (₹)<input name="amount" type="number" min="1" max="100000" step="0.01" defaultValue={initialAmount} required/></label><button className="primary" disabled={!consent||busy||!!order}>{busy?'Opening checkout…':'Open secure checkout'}</button></form>{!consent&&<p>Enable payment-data consent in Your space first.</p>}{order&&<><button className="secondary" onClick={()=>checkStatus(order)}>Check payment status</button> <button className="text-button" onClick={async()=>{try{await paymentRequest('/orders/'+order.order_id+'/cancel',{method:'POST',body:'{}'});setOrder(null);setMessage('Unpaid checkout cancelled.')}catch(error){setMessage((error as Error).message)}}}>Cancel unpaid checkout</button></>}{message&&<p role="status">{message}</p>}</section>;
}
