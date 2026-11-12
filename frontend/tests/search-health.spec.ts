import {test,expect} from '@playwright/test';
import {searchHealth} from '../shared/search-health';

test('health proxy preserves JSON readiness and forbids caching',async()=>{
 let path='';let options:RequestInit|undefined;
 const response=await searchHealth('https://backend.example.test/api/',async(input,init)=>{
  path=String(input);options=init;
  return Response.json({status:'ok',database:'connected',payment_simulation:false,release:'fixture'});
 });
 expect(path).toBe('https://backend.example.test/api/health');
 expect(options?.cache).toBe('no-store');expect(options?.redirect).toBe('error');
 expect(response.status).toBe(200);expect(response.headers.get('cache-control')).toContain('no-store');
 expect(await response.json()).toMatchObject({status:'ok',database:'connected',payment_simulation:false});
});

test('warm-up HTML, invalid JSON and unavailable databases stay retryable JSON failures',async()=>{
 for(const make of [()=>new Response('<html>Starting</html>',{headers:{'content-type':'text/html'}}),()=>Response.json({status:'ok'}),()=>new Response('broken',{headers:{'content-type':'application/json'}}),()=>Response.json({status:'unavailable'},{status:503})]){
  const response=await searchHealth('https://backend.example.test/api',async()=>make());
  expect(response.status).toBe(503);expect(response.headers.get('retry-after')).toBe('3');
  expect(response.headers.get('cache-control')).toContain('no-store');
  expect(await response.json()).toMatchObject({status:'unavailable'});
 }
 const response=await searchHealth('https://backend.example.test/api',async()=>{throw new Error('Network unavailable')});
 expect(response.status).toBe(503);
});
