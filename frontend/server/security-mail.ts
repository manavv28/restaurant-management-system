import {createHmac,timingSafeEqual} from 'node:crypto';

export const sender='letsbiteai@gmail.com';
export const publicApp='https://restaurant-management-system-qxtx.vercel.app';
export type SecurityMail={to:string;purpose:'verify'|'reset'|'test';token:string;smtp_password:string};
export function authenticateMail(raw:string,timestamp:string,signature:string,secret:string,now=Date.now()):SecurityMail{
 if(secret.length<32||raw.length>4096||!/^\d{10}$/.test(timestamp)||Math.abs(now/1000-Number(timestamp))>60||!/^\w{64}$/.test(signature))throw new Error('Invalid request');
 const expected=createHmac('sha256',secret).update(timestamp+'.'+raw).digest('hex');
 if(!timingSafeEqual(Buffer.from(signature),Buffer.from(expected)))throw new Error('Invalid request');
 const data=JSON.parse(raw);
 if(typeof data.to!=='string'||data.to.length>254||!/^\S+@[^\s@]+\.[^\s@]+$/.test(data.to)||!['verify','reset','test'].includes(data.purpose)||typeof data.token!=='string'||!/^[-_A-Za-z0-9]{32,128}$/.test(data.token)||typeof data.smtp_password!=='string'||data.smtp_password.length>128||data.smtp_password.replace(/\s/g,'').length!==16)throw new Error('Invalid request');
 if(data.purpose==='test'&&data.to!==sender)throw new Error('Invalid request');
 return data;
}
export function mailContent(data:SecurityMail){
 if(data.purpose==='test')return {from:sender,to:sender,subject:'BiteAI email delivery test',text:'BiteAI successfully reached Gmail through its secure email delivery service. This is a setup test; no action is required.'};
 const action=data.purpose==='verify'?'verify your email':'reset your password';
 return {from:sender,to:data.to,subject:data.purpose==='verify'?'Verify your BiteAI email':'Reset your BiteAI password',text:`Open this link to ${action}:\n${publicApp}/#${data.purpose}=${data.token}\n\nThis link expires in 20 minutes. Ignore it if you did not request it.`};
}
