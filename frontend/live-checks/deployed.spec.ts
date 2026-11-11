import {test,expect} from '@playwright/test';

test('public release serves the real catalog, source details and a responsive mobile UI',async({page})=>{
 const expected=(process.env.EXPECTED_RELEASE||'').slice(0,12);
 await expect.poll(async()=>{try{const response=await page.request.get('/api/health',{timeout:20000});if(!response.ok())return 'unavailable';const health=await response.json();return expected?health.release:health.status}catch{return 'unavailable'}},{timeout:300000,intervals:[5000]}).toBe(expected||'ok');
 const health=await (await page.request.get('/api/health')).json();
 expect(health.database_provider).toBe('Supabase');expect(health.database_tls).toBe('verify-full');expect(health.payment_simulation).toBe(false);
 const coverage=await (await page.request.get('/api/catalog/coverage')).json();
 expect(coverage.real_restaurants).toBeGreaterThanOrEqual(378);expect(coverage.last_successful_collection).toBeTruthy();
 const search=await (await page.request.post('/api/search',{data:{query:'',area:'Bandra',include_samples:false}})).json();
 expect(search.results.every((row:{restaurant:{sample:boolean}})=>!row.restaurant.sample)).toBeTruthy();
 const restaurant=search.results[0]?.restaurant||search.nearby_unpriced[0]?.restaurant;expect(restaurant).toBeTruthy();
 await page.goto('/',{waitUntil:'domcontentloaded'});
 await expect(page.getByText('Our Mumbai data collection',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Sample listings')).not.toBeChecked();
 await page.locator('.restaurant-card .card-title button, .catalog-panel .history-row button').filter({hasText:restaurant.name}).first().click();
 await expect(page.getByRole('dialog')).toContainText(restaurant.name);
 await expect(page.getByRole('dialog').locator('.source-note')).toContainText('Source:');
 await page.getByRole('button',{name:'Close',exact:true}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/live-mobile.png',fullPage:true});
});
