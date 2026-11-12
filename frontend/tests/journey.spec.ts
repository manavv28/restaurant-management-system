import {test,expect} from '@playwright/test';
test('search, menu, account, favourites and consent',async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Good food, close to you'})).toBeVisible();
 await page.getByRole('textbox',{name:'Your food craving'}).fill('Chinese Hakka noodles under ₹300 within 2 km');
 await page.getByRole('button',{name:'Find my food'}).click();
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Wok & Wonder',exact:true}).click();
 await expect(page.getByRole('dialog')).toContainText('Fictional demonstration location');
 await expect(page.getByRole('dialog')).toContainText('₹240');
 await page.getByRole('button',{name:'Close',exact:true}).click();
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('button',{name:'New here? Create an account'}).click();
 await page.getByLabel('Your name').fill('Browser Foodie');
 await page.getByLabel('Email',{exact:true}).fill('browser'+Date.now()+'@example.test');
 await page.getByLabel('Password',{exact:true}).fill('a-test-password-123');
 await page.getByRole('button',{name:'Create account',exact:true}).click();
 await expect(page.getByRole('dialog')).not.toBeVisible();
 await page.getByRole('button',{name:'Save Sample · Wok & Wonder',exact:true}).click();
 await page.getByRole('button',{name:'Your space'}).click();
 await expect(page.getByRole('heading',{name:'Saved for your next craving'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Sample · Wok & Wonder'})).toBeVisible();
 await page.getByLabel('I consent to payment-data processing').check();
 await expect(page.getByRole('button',{name:'Simulate transaction'})).toBeEnabled();
 await page.getByRole('button',{name:'Simulate transaction'}).click();
 await expect(page.getByText('SIMULATED · not verified',{exact:true})).toBeVisible();
 await page.getByLabel('I consent to payment-data processing').uncheck();
 await expect(page.getByRole('button',{name:'Simulate transaction'})).toBeDisabled();
});
test('mobile layout and map interaction',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/');
 await expect(page.getByRole('textbox',{name:'Your food craving'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.screenshot({path:'/tmp/biteai-mobile.png',fullPage:true});
 await page.getByRole('button',{name:'Map view'}).click();
 await expect(page.getByLabel('Interactive restaurant map')).toBeVisible();
 await expect(page.locator('.leaflet-interactive').first()).toBeVisible();
 await page.locator('.leaflet-interactive').last().click();
 await expect(page.locator('.leaflet-popup-content button')).toBeVisible();
 await page.getByRole('textbox',{name:'Your food craving'}).fill('Chinese');
 await expect(page.locator('.leaflet-popup-content button')).toBeVisible();
 await page.locator('.leaflet-popup-content button').click();
 await expect(page.getByRole('dialog')).toBeVisible();
});
test('owner onboards restaurant, manages menu and creates campaign',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('button',{name:'New here? Create an account'}).click();
 await page.getByLabel('Your name').fill('Browser Owner');
 await page.getByLabel('Email',{exact:true}).fill('owner'+Date.now()+'@example.test');
 await page.getByLabel('Password',{exact:true}).fill('a-test-password-123');
 await page.getByLabel('Account type').selectOption('owner');
 await page.getByRole('button',{name:'Create account',exact:true}).click();
 await expect(page.getByRole('dialog')).not.toBeVisible();
 await page.getByRole('button',{name:'For restaurants'}).click();
 await page.getByLabel('Restaurant name').fill('Browser Test Kitchen');
 await page.getByLabel('Address',{exact:true}).fill('Test address in Bandra Mumbai');
 await page.getByRole('button',{name:'Create listing'}).click();
 await page.getByLabel('Manage listing').selectOption({label:'Browser Test Kitchen'});
 await page.getByLabel('Dish name').fill('Hakka noodles');
 await page.getByRole('button',{name:'Save dish'}).click();
 await expect(page.getByRole('button',{name:'Hakka noodles ₹240 · Edit'})).toBeVisible();
 await page.getByLabel('Campaign title').fill('Browser reward');
 await page.getByLabel('Valid until').fill('2027-12-31T23:00');
 await page.getByRole('button',{name:'Create campaign',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('Campaign created');
});
test('coverage reports real collection honestly and unknown source is rejected',async({page})=>{
 await page.goto('/');
 await expect(page.getByText('Our Mumbai data collection',{exact:true})).toBeVisible();
 await expect(page.getByText('No successful automated collection yet. Sample data is not real coverage.')).toBeVisible();
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('button',{name:'New here? Create an account'}).click();
 await page.getByLabel('Your name').fill('Source Owner');
 await page.getByLabel('Email',{exact:true}).fill('source'+Date.now()+'@example.test');
 await page.getByLabel('Password',{exact:true}).fill('a-test-password-123');
 await page.getByLabel('Account type').selectOption('owner');
 await page.getByRole('button',{name:'Create account',exact:true}).click();
 await expect(page.getByRole('dialog')).not.toBeVisible();
 await page.getByRole('button',{name:'For restaurants'}).click();
 await page.getByLabel('Restaurant name').fill('Source Fixture Kitchen');
 await page.getByLabel('Address',{exact:true}).fill('Test fixture in Bandra Mumbai');
 await page.getByRole('button',{name:'Create listing'}).click();
 await page.getByLabel('Manage listing').selectOption({label:'Source Fixture Kitchen'});
 await page.getByLabel('Menu page (HTTPS)').fill('https://unapproved.example.test/menu');
 await page.getByLabel('Permission to collect this page').fill('I own this test fixture website');
 await page.getByRole('button',{name:'Register source & queue collection'}).click();
 await expect(page.getByText('Menu host must be explicitly listed in APPROVED_MENU_HOSTS',{exact:true})).toBeVisible();
});

test('cookie session survives reload, stays out of JavaScript, and logout revokes it',async({page,context})=>{
 const result=await page.request.post('/api/auth/register',{headers:{'X-BiteAI-Client':'browser'},data:{name:'Session Browser',email:'session'+Date.now()+'@example.test',password:'a-test-password-123'}});
 expect(result.ok()).toBeTruthy();expect(await result.json()).not.toHaveProperty('token');
 const cookie=(await context.cookies()).find(c=>c.name==='biteai-session');
 expect(cookie?.httpOnly).toBeTruthy();expect(cookie?.sameSite).toBe('Lax');
 await page.goto('/');await page.getByRole('button',{name:'Your space'}).click();
 await expect(page.getByRole('button',{name:'Sign out'})).toBeVisible();
 expect(await page.evaluate(()=>sessionStorage.getItem('biteai-token'))).toBeNull();
 expect(await page.evaluate(()=>document.cookie)).not.toContain('biteai-session');
 await page.reload();await page.getByRole('button',{name:'Your space'}).click();
 await expect(page.getByRole('button',{name:'Sign out'})).toBeVisible();
 await page.getByRole('button',{name:'Sign out'}).click();
 await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeVisible();
 const replay=await page.request.get('/api/me',{headers:{Authorization:'Bearer '+cookie!.value}});
 expect(replay.status()).toBe(401);
});

test('hosted checkout callback waits for verified server status',async({page})=>{
 const headers={'X-BiteAI-Client':'browser'};
 const suffix=Date.now();
 await page.request.post('/api/auth/register',{headers,data:{name:'Checkout Owner',role:'owner',email:`checkout${suffix}@example.test`,password:'a-test-password-123'}});
 const response=await page.request.post('/api/portal/restaurants',{headers,data:{name:`Checkout Kitchen ${suffix}`,address:'Test fixture Bandra Mumbai',area:'Bandra',latitude:19.0596,longitude:72.8295,cuisine:'Chinese'}});
 expect(response.ok()).toBeTruthy();const restaurant=await response.json();
 await page.request.post(`/api/portal/restaurants/${restaurant.id}/menu`,{headers,data:{name:'Hakka noodles',cuisine:'Chinese',price_paise:25000}});
 await page.request.put('/api/me/consent',{headers,data:{consent:true}});
 await page.route(`**/api/payments/availability/${restaurant.id}`,route=>route.fulfill({json:{enabled:true}}));
 await page.route('https://checkout.razorpay.com/v1/checkout.js',route=>route.fulfill({contentType:'application/javascript',body:'window.Razorpay=class{constructor(options){this.options=options}open(){this.options.handler()}}'}));
 await page.route('**/api/payments/orders',route=>route.fulfill({json:{order_id:'order_BrowserFixture',key_id:'rzp_test_fixture',amount_paise:25000,currency:'INR'}}));
 let captured=false;
 await page.route('**/api/payments/orders/order_BrowserFixture',route=>route.fulfill({json:{state:captured?'captured':'created'}}));
 await page.goto('/');
 await page.getByRole('button',{name:`Checkout Kitchen ${suffix}`,exact:true}).click();
 await page.getByLabel('Bill amount (₹)').fill('250');
 await page.getByRole('button',{name:'Open secure checkout'}).click();
 await expect(page.getByRole('status')).toContainText('Awaiting the signed provider webhook');
 captured=true;
 await page.getByRole('button',{name:'Check payment status'}).click();
 await expect(page.getByRole('status')).toContainText('Payment verified by the provider webhook');
});

test('location permission sets coordinates and denial keeps text search available',async({page,context})=>{
 await context.grantPermissions(['geolocation']);await context.setGeolocation({latitude:19.0596,longitude:72.8295});
 await page.goto('/');
 // Hydration can briefly enable the form before the initial search starts.
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Find my food',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Use my location',exact:true}).click();
 await expect(page.getByRole('button',{name:'GPS location set'})).toBeVisible();
 const request=page.waitForRequest(r=>r.url().endsWith('/api/search')&&r.method()==='POST');
 await page.getByRole('button',{name:'Find my food'}).click();
 const coordinates=(await request).postDataJSON();expect(coordinates.latitude).toBe(19.0596);expect(coordinates.longitude).toBe(72.8295);
 await page.addInitScript(()=>{Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition:(_success:unknown,failure:(error:{code:number})=>void)=>failure({code:1})}})});
 await page.reload();await page.getByRole('button',{name:'Use my location',exact:true}).click();
 await expect(page.getByRole('alert').filter({hasText:'Location access was declined'})).toContainText('Location access was declined');
 await expect(page.getByRole('textbox',{name:'Your food craving'})).toBeEnabled();
});

test('supported voice adapter submits recognised text and unsupported browsers fall back',async({page})=>{
 await page.addInitScript(()=>{
  class SpeechFixture {lang='';onresult:((event:unknown)=>void)|null=null;onend:(()=>void)|null=null;onerror:(()=>void)|null=null;start(){setTimeout(()=>{this.onresult?.({results:[[{transcript:'Chinese Hakka noodles under ₹300 within 2 km'}]]});this.onend?.()},10)}}
  Object.defineProperty(window,'SpeechRecognition',{value:SpeechFixture,configurable:true});
 });
 await page.goto('/');await page.getByRole('button',{name:'Search by voice'}).click();
 await expect(page.getByRole('textbox',{name:'Your food craving'})).toHaveValue('Chinese Hakka noodles under ₹300 within 2 km');
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible();
 await page.evaluate(()=>{Object.defineProperty(window,'SpeechRecognition',{value:undefined,configurable:true});Object.defineProperty(window,'webkitSpeechRecognition',{value:undefined,configurable:true})});
 await page.getByRole('button',{name:'Search by voice'}).click();
 await expect(page.getByRole('status')).toContainText('Voice search isn’t supported');
});

test('discovery extras are honest and recovery reports unavailable email delivery',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:'Popular dishes',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Picked for you',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Forgot your password?'}).click();
 await expect(page.getByText('Email delivery is not available yet. Please try again once the service is configured.')).toBeVisible();
 await expect(page.getByRole('button',{name:'Send reset link'})).toBeDisabled();
});

test('a delayed account refresh cannot overwrite a consent change',async({page})=>{
 const headers={'X-BiteAI-Client':'browser'};
 await page.request.post('/api/auth/register',{headers,data:{name:'Consent Race',email:`consent${Date.now()}@example.test`,password:'a-test-password-123'}});
 await page.goto('/');await page.getByRole('button',{name:'Your space'}).click();
 await expect(page.getByLabel('I consent to payment-data processing')).toBeVisible();
 await page.getByRole('button',{name:'Discover',exact:true}).click();
 let release:()=>void=()=>{};
 const gate=new Promise<void>(resolve=>{release=resolve});
 let seen:()=>void=()=>{};const requested=new Promise<void>(resolve=>{seen=resolve});
 let settled:()=>void=()=>{};const finished=new Promise<void>(resolve=>{settled=resolve});
 await page.route('**/api/me',async route=>{
  const response=await route.fetch();const body=await response.json();
  if(body.consent===false){seen();await gate;await route.fulfill({response,json:body})}else await route.fulfill({response});
  settled();
 },{times:1});
 await page.getByRole('button',{name:'Your space'}).click();await requested;
 try{
  const update=page.waitForResponse(response=>response.url().endsWith('/api/me/consent')&&response.request().method()==='PUT');
  await page.getByLabel('I consent to payment-data processing').check();
  expect((await update).ok()).toBeTruthy();
 }finally{release()}
 await finished;
 await expect(page.getByLabel('I consent to payment-data processing')).toBeChecked();
});
