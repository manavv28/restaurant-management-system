import {test,expect} from '@playwright/test';

test('Hinglish streaming verdict preserves context and exposes honest confidence',async({page})=>{
 await page.goto('/');await page.getByLabel('Your food craving').fill('Chinese khane ka mann hai, Hakka noodles 300 mein 2 km ke andar Bandra mein?');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 const verdict=page.getByRole('region',{name:'Your food verdict'});await expect(verdict).toContainText('₹240');await expect(verdict).toContainText('Confirm current price');await expect(verdict).toContainText('Bandra · Up to ₹300 · 2 km');
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible();
 await verdict.getByRole('button',{name:'Sabse paas',exact:true}).click();await expect(verdict).toContainText('₹240');
 const last=await page.getByLabel('Your food craving').inputValue();expect(last).toBe('Sabse paas');
 await expect(page.locator('.restaurant-card').filter({has:page.getByRole('button',{name:'Wok & Wonder',exact:true})}).locator('.confidence-chip')).toContainText('Fictional sample');
 await expect(page.getByRole('link',{name:'Check on Swiggy'}).first()).toHaveAttribute('href',/swiggy\.com\/search\?query=/);
});

test('Agent Wall shows actual run summaries and protects administration',async({page})=>{
 await page.goto('/');await expect(page.getByRole('region',{name:'Your food verdict'})).toBeVisible();
 await page.goto('/agents');await expect(page.getByRole('heading',{name:'Meet your food crew.'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Catalogue job queue'})).toBeVisible();await expect(page.getByRole('heading',{name:'Recent query workflow runs'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Administrator quality review'})).toHaveCount(0);
 const response=await page.request.get('/api/admin/quality');expect(response.status()).toBe(401);
});

test('dark theme can be changed and retained with mobile controls accessible',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await expect(page.locator('html')).toHaveAttribute('data-theme','night');
 await page.getByRole('button',{name:'Switch to light theme'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.getByRole('button',{name:'Switch to dark theme'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','night');
 await expect(page.getByRole('button',{name:'Enable interface sounds'})).toHaveAttribute('aria-pressed','false');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 const manifest=await(await page.request.get('/manifest.webmanifest')).json();expect(manifest.display).toBe('standalone');
});

test('immersive PWA experience keeps the map, voice orb and verdict usable on a phone',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/concierge');
 await expect(page.getByLabel('Interactive restaurant map')).toBeVisible();await expect(page.getByRole('button',{name:'Speak your craving'})).toBeVisible();
 await expect(page.getByRole('region',{name:'Your food verdict'})).toBeVisible();
 await page.getByLabel('Your food craving').fill('Hakka noodles under 300 in Bandra');await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(page.getByRole('region',{name:'Your food verdict'})).toContainText('₹240');
 await expect(page.locator('.leaflet-interactive').first()).toBeVisible();
 await page.getByRole('button',{name:'Show results',exact:true}).click();
 const shortlist=page.getByRole('list',{name:'Top restaurant matches'});await expect(shortlist).toContainText('Wok & Wonder');await expect(shortlist).toContainText('Hakka noodles');
 await shortlist.getByRole('button',{name:'View menu for Sample · Wok & Wonder',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('button',{name:'Close',exact:true}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await expect(page.getByRole('link',{name:'Coverage & list view'})).toHaveAttribute('href','/');await page.getByRole('link',{name:'Coverage & list view'}).click();await expect(page.getByText('Our Mumbai data collection',{exact:true})).toBeVisible();
});

test('a successful source refresh updates the verdict while other research jobs are pending',async({page})=>{
 const venue={id:7001,name:'Synthetic research venue',area:'Bandra',address:'Synthetic fixture',latitude:19.0596,longitude:72.8295,cuisine:'Chinese',sample:false,source:'Synthetic fixture',phone:'',website:'',opening_hours:'Unknown',updated_at:'2026-11-13T00:00:00Z',rating:null};
 const base={results:[],trace:[],parser:'Synthetic fixture',follow_up:'',nearby_unpriced:[],attribution:'',external_discovery:[],intent:{dish:'hakka noodles',max_budget:300,radius_km:2,location:'Bandra'}};
 await page.route('**/api/search',route=>{const body=route.request().postDataJSON();return route.fulfill({json:body.research===false?{...base,results:[{restaurant:venue,dish:{id:7002,name:'Hakka noodles',price_paise:19950,source:'Synthetic publisher fixture',available:true,cuisine:'Chinese',category:'Main',description:''},distance_km:0,reason:'Synthetic source refresh',offers:[]}],verdict:{headline:'Synthetic refreshed verdict ₹199.50',match_count:1,explanation:'Synthetic test data',party_notice:null,mode_notice:'Confirm ordering mode',follow_ups:[]}}:{...base,research:body.query?{state:'queued',token:'synthetic-status-token',message:'Synthetic research queued'}:{state:'idle',message:''}}})});
 await page.route('**/api/research/synthetic-status-token',route=>route.fulfill({json:{state:'running',succeeded:1,failed:0,message:'One source finished; another is pending'}}));
 await page.goto('/');await page.getByLabel('Your food craving').fill('Hakka noodles under 300');await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(page.getByText('Synthetic research queued',{exact:true})).toBeVisible();
 await expect(page.getByRole('region',{name:'Your food verdict'})).toContainText('₹199.50',{timeout:15000});
 await expect(page.getByRole('button',{name:'Synthetic research venue',exact:true})).toBeVisible();
});

test('immersive map remains visible while a search is waiting on the backend',async({page})=>{
 let release:()=>void=()=>{};
 const waiting=new Promise<void>(resolve=>{release=resolve});
 await page.route('**/api/search',async route=>{await waiting;await route.fulfill({json:{results:[],trace:[],parser:'Synthetic delayed backend',follow_up:'',attribution:'',external_discovery:[]}})});
 try {
  await page.goto('/concierge');
  await expect(page.getByLabel('Interactive restaurant map')).toBeVisible();
  await expect(page.getByRole('button',{name:'Speak your craving'})).toBeVisible();
  await expect(page.getByRole('status').filter({hasText:'Finding your next favourite'})).toBeVisible();
 } finally {release();}
});


test('phone map stays exposed with filters and results collapsed, while desktop retains its full panels',async({page})=>{
 await page.goto('/concierge');await expect(page.getByRole('region',{name:'Your food verdict'})).toBeVisible();
 for(const size of [{width:320,height:568},{width:390,height:844},{width:430,height:932}]){
  await page.setViewportSize(size);
  await expect(page.getByRole('button',{name:'Show results',exact:true})).toBeVisible();
  await expect(page.getByLabel('Maximum budget')).toBeHidden();
  const search=await page.getByRole('region',{name:'Food search'}).boundingBox();
  const sheet=await page.getByRole('region',{name:'Your food verdict'}).boundingBox();
  expect(search).toBeTruthy();expect(sheet).toBeTruthy();
  expect(sheet!.y-search!.y-search!.height).toBeGreaterThan(size.height*.4);
  const mapReceivesTouches=await page.evaluate(({x,y})=>!!document.elementFromPoint(x,y)?.closest('.map-wrapper'),{x:size.width/2,y:(search!.y+search!.height+sheet!.y)/2});expect(mapReceivesTouches).toBeTruthy();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 }
 await page.getByRole('button',{name:'Search filters',exact:true}).click();await expect(page.getByLabel('Maximum budget')).toBeVisible();
 await page.getByRole('button',{name:'Search filters',exact:true}).click();await expect(page.getByLabel('Maximum budget')).toBeHidden();
 await page.getByRole('button',{name:'Show results',exact:true}).click();await expect(page.getByRole('list',{name:'Top restaurant matches'})).toBeVisible();
 await page.getByRole('button',{name:'Hide results',exact:true}).click();await expect(page.getByRole('list',{name:'Top restaurant matches'})).toBeHidden();
 await page.screenshot({path:'test-results/phone-map-space.png'});
 await page.setViewportSize({width:1440,height:1000});await expect(page.getByLabel('Maximum budget')).toBeVisible();await expect(page.getByRole('list',{name:'Top restaurant matches'})).toBeVisible();await expect(page.getByRole('button',{name:'Show results',exact:true})).toBeHidden();
});
