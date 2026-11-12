import {test,expect} from '@playwright/test';
import {createHmac} from 'node:crypto';
import {authenticateMail,mailContent,sender} from '../server/security-mail';
const secret='isolated-relay-test-secret-1234567890';
const timestamp='1800000000';
const mail={to:'fixture@example.test',purpose:'verify',token:'a'.repeat(43),smtp_password:'abcd efgh ijkl mnop'};
const raw=JSON.stringify(mail);
const sign=(body=raw,time=timestamp)=>createHmac('sha256',secret).update(time+'.'+body).digest('hex');

test('security mail authenticates exact payload and fixes sender and link',()=>{
 const data=authenticateMail(raw,timestamp,sign(),secret,Number(timestamp)*1000);
 const message=mailContent(data);
 expect(message.from).toBe(sender);expect(message.to).toBe(mail.to);
 expect(message.text).toContain('https://restaurant-management-system-qxtx.vercel.app/#verify=');
 expect(message.text).not.toContain(mail.smtp_password);
});
test('security mail rejects missing credentials, tampering and stale signatures',()=>{
 for(const args of [[raw,timestamp,'',secret],[raw+' ',timestamp,sign(),secret],[raw,timestamp,sign(),'']])
  expect(()=>authenticateMail(args[0],args[1],args[2],args[3],Number(timestamp)*1000)).toThrow();
 expect(()=>authenticateMail(raw,timestamp,sign(),secret,Number(timestamp)*1000+61000)).toThrow();
});
test('security mail rejects arbitrary templates and injected recipient headers',()=>{
 for(const altered of [{...mail,purpose:'promotion'},{...mail,to:'fixture@example.test\r\nBcc:other@example.test'},{...mail,token:'https://evil.example'}]){
  const body=JSON.stringify(altered);
  expect(()=>authenticateMail(body,timestamp,sign(body),secret,Number(timestamp)*1000)).toThrow();
 }
});
test('verification click shows pending, failures and rate limit without duplicate sends',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('button',{name:'New here? Create an account'}).click();
 await page.getByLabel('Your name').fill('Verification fixture');
 await page.getByLabel('Email',{exact:true}).fill('verification-'+Date.now()+'@example.test');
 await page.getByLabel('Password',{exact:true}).fill('isolated-browser-password-123');
 await page.getByRole('button',{name:'Create account',exact:true}).click();
 await expect(page.getByRole('dialog')).not.toBeVisible();
 await page.getByRole('button',{name:'Your space'}).click();
 let sends=0;let release:()=>void=()=>{};
 const pending=new Promise<void>(resolve=>{release=resolve});
 await page.route('**/api/me/request-verification',async route=>{sends++;await pending;await route.fulfill({status:503,json:{detail:'Email could not be sent. Please try again later or contact support.'}})});
 await page.getByRole('button',{name:'Send verification email',exact:true}).click();
 await expect(page.getByRole('button',{name:'Sending verification email…'})).toBeDisabled();
 expect(sends).toBe(1);release();
 await expect(page.getByRole('region',{name:'Email verification'}).getByRole('alert')).toContainText('Email could not be sent');
 await page.unroute('**/api/me/request-verification');
 await page.route('**/api/me/request-verification',route=>route.fulfill({status:429,json:{detail:'Too many attempts'}}));
 await page.getByRole('button',{name:'Send verification email',exact:true}).click();
 await expect(page.getByRole('region',{name:'Email verification'}).getByRole('alert')).toContainText('Wait five minutes');
 await page.unroute('**/api/me/request-verification');
 await page.route('**/api/me/request-verification',route=>route.fulfill({json:{message:'Check your email'}}));
 await page.getByRole('button',{name:'Send verification email',exact:true}).click();
 await expect(page.getByRole('region',{name:'Email verification'}).getByRole('status')).toContainText('Verification email sent');
});
