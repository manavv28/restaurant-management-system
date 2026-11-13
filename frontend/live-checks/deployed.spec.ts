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
 if(search.results.length>3){
  await expect(page.locator('.restaurant-card')).toHaveCount(3);
  await page.getByRole('button',{name:/^Show more \(/}).click();
  await expect(page.locator('.restaurant-card')).toHaveCount(search.results.length);
  await page.getByRole('button',{name:'Show less',exact:true}).click();
  await expect(page.locator('.restaurant-card')).toHaveCount(3);
 }
 await page.locator('.restaurant-card .card-title button, .catalog-panel .history-row button').filter({hasText:restaurant.name}).first().click();
 await expect(page.getByRole('dialog')).toContainText(restaurant.name);
 await expect(page.getByRole('dialog').locator('.source-note')).toContainText('Source:');
 await page.getByRole('button',{name:'Close',exact:true}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/live-mobile.png',fullPage:true});
});

test('the original noodles request respects price, radius and real-source constraints',async({request})=>{
 const response=await request.post('/api/search',{data:{query:'Chinese Haka noodles for 300 within 2 km in Bandra',area:'Bandra',include_samples:false}});
 expect(response.ok()).toBeTruthy();const data=await response.json();
 expect(data.intent).toMatchObject({dish:'hakka noodles',max_budget:300,radius_km:2,location:'Bandra'});
 // Missing catalogue dishes must remain an honest empty result; never substitute a fictional match.
 for(const row of data.results){
  expect(row.restaurant.sample).toBe(false);expect(row.distance_km).toBeLessThanOrEqual(2);
  expect(row.dish.price_paise).toBeGreaterThan(0);expect(row.dish.price_paise).toBeLessThanOrEqual(30000);
  expect(row.dish.name.toLowerCase()).toContain('hakka noodles');expect(row.dish.source).toBeTruthy();
 }
 expect(data.trace.length).toBeGreaterThan(0);
});

test('public PRD concierge serves a streamed verdict, phone map and actual Agent Wall',async({page})=>{
 await expect.poll(async()=>{try{const response=await page.request.get('/manifest.webmanifest');return response.ok()?(await response.json()).start_url:'pending'}catch{return 'pending'}},{timeout:240000,intervals:[5000]}).toBe('/concierge');
 await page.goto('/concierge',{waitUntil:'domcontentloaded'});
 await expect(page.getByLabel('Interactive restaurant map')).toBeVisible();await expect(page.getByRole('button',{name:'Speak your craving'})).toBeVisible();
 await page.getByLabel('Your food craving').fill('Chinese khane ka mann hai, Hakka noodles 300 mein 2 km ke andar Bandra mein?');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(page.getByRole('region',{name:'Your food verdict'})).toContainText('listed option');
 await page.getByRole('button',{name:'Show results',exact:true}).click();
 const shortlist=page.getByRole('list',{name:'Top restaurant matches'});
 await expect(shortlist.getByRole('button')).toHaveCount(3);
 await expect(page.getByRole('region',{name:'Your food verdict'})).toContainText('Up to ₹300 · 2 km');
 await shortlist.getByRole('button').first().click();
 await expect(page.getByRole('dialog')).toBeVisible();
 await page.getByRole('button',{name:'Close',exact:true}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.getByRole('button',{name:'Hide results',exact:true}).click();
 await expect(page.getByRole('list',{name:'Top restaurant matches'})).toBeHidden();
 const searchBox=await page.getByRole('region',{name:'Food search'}).boundingBox();const resultsSheet=await page.getByRole('region',{name:'Your food verdict'}).boundingBox();
 expect(resultsSheet!.y-searchBox!.y-searchBox!.height).toBeGreaterThan(844*.4);
 await page.screenshot({path:'test-results/live-prd-concierge.png'});
 await page.getByRole('link',{name:'Coverage & list view'}).click();await expect(page.getByText('Our Mumbai data collection',{exact:true})).toBeVisible();
 await page.goto('/agents');await expect(page.getByRole('heading',{name:'Meet your food crew.'})).toBeVisible();await expect(page.getByRole('heading',{name:'Catalogue job queue'})).toBeVisible();
 const response=await page.request.get('/api/agents/activity');expect(response.ok()).toBeTruthy();const data=await response.json();expect(data.agents.length).toBeGreaterThan(0);
 expect(data.agents.every((run:{agent:string;latency_ms:number})=>typeof run.agent==='string'&&run.latency_ms>=0)).toBeTruthy();
 await expect(page.getByRole('heading',{name:'Administrator quality review'})).toHaveCount(0);
});
