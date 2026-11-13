'use client';
import {FormEvent,useEffect,useState} from 'react';
async function api(path:string,body:unknown){const response=await fetch('/api'+path,{method:'POST',headers:{'Content-Type':'application/json','X-BiteAI-Client':'browser'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Request failed');return data;}
export function RecoveryForm({showTrigger=true}:{showTrigger?:boolean}){
 const [mode,setMode]=useState(''),[token,setToken]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[enabled,setEnabled]=useState(false);
 useEffect(()=>{fetch('/api/auth/email-availability').then(r=>r.json()).then(data=>setEnabled(data.enabled)).catch(()=>{});
 const params=new URLSearchParams(window.location.hash.slice(1));
 if(params.has('reset')){setMode('reset');setToken(params.get('reset')||'')}
 if(params.has('verify')){setMode('verify');setToken(params.get('verify')||'')}
 if(params.has('reset')||params.has('verify'))window.history.replaceState(null,'',window.location.pathname+window.location.search);
 },[]);
 async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();const values=Object.fromEntries(new FormData(event.currentTarget));setBusy(true);try{const data=await api(mode==='reset'?'/auth/reset-password':mode==='verify'?'/auth/verify-email':'/auth/forgot-password',mode==='reset'?{token,password:values.password}:mode==='verify'?{token}:{email:values.email});setMessage(data.message);if(mode!=='forgot'){setMode('done');setToken('')}}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 return <section className="account-recovery">{!mode&&showTrigger&&<button className="text-button" onClick={()=>setMode('forgot')}>Forgot your password?</button>}{mode&&<form onSubmit={submit}><h3>{mode==='reset'?'Choose a new password':mode==='verify'?'Verify your email':mode==='done'?'Account updated':'Reset your password'}</h3>{mode==='forgot'&&<><p>{enabled?'We’ll email a reset link if the account exists.':'Email delivery is not available yet. Please try again once the service is configured.'}</p><label>Recovery email<input name="email" type="email" required maxLength={254}/></label></>}{mode==='reset'&&<label>New password<input name="password" type="password" minLength={10} maxLength={128} required autoComplete="new-password"/></label>}{mode!=='done'&&<button className="secondary" disabled={busy||(mode==='forgot'&&!enabled)}>{mode==='verify'?'Confirm email verification':mode==='reset'?'Update password':'Send reset link'}</button>}<button type="button" className="text-button" onClick={()=>{setMode('');setMessage('');setToken('')}}>Close recovery</button></form>}{message&&<p role="status">{message}</p>}</section>;
}
export function EmailVerification({verified,onVerified}:{verified:boolean;onVerified:()=>void}){
 const [message,setMessage]=useState(''),[busy,setBusy]=useState(false),[failed,setFailed]=useState(false);
 async function send(){
  if(busy)return;
  setBusy(true);setFailed(false);setMessage('Sending your verification email…');
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),35000);
  try{
   const response=await fetch('/api/me/request-verification',{method:'POST',headers:{'Content-Type':'application/json','X-BiteAI-Client':'browser'},body:'{}',signal:controller.signal});
   const data=await response.json();
   if(!response.ok)throw new Error(response.status===429?'Too many requests. Wait five minutes before trying again.':response.status===401?'Your session expired. Sign in again.':typeof data.detail==='string'?data.detail:'Email could not be sent. Please try again later.');
   setMessage('Verification email sent. Check your inbox and spam folder.');onVerified();
  }catch(error){setFailed(true);setMessage(error instanceof Error&&error.name==='AbortError'?'Email delivery timed out. Please wait before trying again.':error instanceof Error?error.message:'Email could not be sent. Please try again later.')}
  finally{clearTimeout(timeout);setBusy(false)}
 }
 return <section className="panel" aria-label="Email verification"><h2>Email verification</h2>{verified?<p>Email verified.</p>:<><p>Your email has not been verified.</p><button type="button" className="secondary" disabled={busy} onClick={send}>{busy?'Sending verification email…':'Send verification email'}</button>{message&&<p role={failed?'alert':'status'}>{message}</p>}</>}</section>;
}
export function OwnershipVerification({restaurantId,verified}:{restaurantId:number;verified:boolean}){
 const [challenge,setChallenge]=useState<{record_name:string;record_value:string}|null>(null),[message,setMessage]=useState(''),[done,setDone]=useState(verified);
 useEffect(()=>{setDone(verified);setChallenge(null);setMessage('')},[restaurantId,verified]);
 async function run(check=false){try{const data=await api('/portal/restaurants/'+restaurantId+(check?'/verify-ownership':'/ownership-challenge'),{});if(check){setDone(true);setMessage(data.notice)}else{setChallenge(data);setMessage('Add this TXT record in your website’s DNS settings, then check verification.')}}catch(e){setMessage((e as Error).message)}}
 return <section className="panel"><h2>Verify your restaurant website</h2>{done?<p>Website control verified.</p>:<><p>Prove control of the website domain listed for your restaurant.</p><button className="secondary" onClick={()=>run()}>Create verification challenge</button>{challenge&&<><p>TXT name: <code>{challenge.record_name}</code></p><p>TXT value: <code>{challenge.record_value}</code></p><button className="primary" onClick={()=>run(true)}>Check DNS verification</button></>}</>}{message&&<p role="status">{message}</p>}</section>;
}
