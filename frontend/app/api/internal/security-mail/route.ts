import nodemailer from 'nodemailer';
import {authenticateMail,mailContent,sender} from '../../../../server/security-mail';

export const maxDuration=30;
export async function POST(request:Request){
 const reply=(status:number)=>Response.json({ok:status===200},{status,headers:{'Cache-Control':'no-store'}});
 const secret=process.env.EMAIL_RELAY_SECRET||'';
 if(secret.length<32)return reply(503);
 if(Number(request.headers.get('content-length')||0)>4096)return reply(413);
 let data;
 try{
  const raw=await request.text();
  data=authenticateMail(raw,request.headers.get('x-biteai-mail-time')||'',request.headers.get('x-biteai-mail-signature')||'',secret);
 }catch{return reply(401)}
 // Await SMTP completion before returning; credentials and tokens never reach browser responses/logs.
 const transport=nodemailer.createTransport({host:'smtp.gmail.com',port:465,secure:true,auth:{user:sender,pass:data.smtp_password.replace(/\s/g,'')},connectionTimeout:8000,greetingTimeout:8000,socketTimeout:15000,logger:false,debug:false});
 try{
  await transport.sendMail(mailContent(data));
  return reply(200);
 }catch(error){
  const code=(error as {code?:string}).code;
  console.error('security_email_delivery_failed',{code:['EAUTH','ETIMEDOUT','ECONNECTION','ESOCKET'].includes(code||'')?code:'SMTP_ERROR'});
  return reply(503);
 }finally{transport.close()}
}
