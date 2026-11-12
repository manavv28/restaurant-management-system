import {test,expect} from '@playwright/test';

test('external links preserve the craving and never claim a live provider comparison',async({page})=>{
 await page.route('**/api/platforms/status',route=>route.fulfill({json:{swiggy:{available:false,connected:false},zomato:{available:false,mode:'external_link'}}}));
 await page.goto('/');await page.getByLabel('Your food craving').fill('Hakka noodles under 300');
 await page.getByRole('button',{name:'Check Zomato and Swiggy',exact:true}).click();
 const panel=page.getByRole('region',{name:'Delivery platforms'});
 await expect(panel).toContainText('Swiggy live search is not available on BiteAI yet');
 await expect(panel.getByRole('link',{name:'Browse on Zomato'})).toHaveAttribute('href','https://www.zomato.com/mumbai/restaurants?q=Hakka%20noodles%20under%20300');
 await expect(panel.getByRole('link',{name:'Browse on Swiggy'})).toHaveAttribute('href','https://www.swiggy.com/search?query=Hakka%20noodles%20under%20300');
 await expect(panel.getByRole('button',{name:'Connect Swiggy',exact:true})).toHaveCount(0);
});

test('connected provider requires restaurant selection and distinguishes unknown option prices',async({page})=>{
 await page.route(/\/api\/me(?:\/|\?|$)/,route=>route.fulfill({json:new URL(route.request().url()).pathname==='/api/me'?{id:991,name:'Synthetic user',email:'synthetic@example.test',role:'customer',consent:false,email_verified:true,query_count:0,verified_spend_paise:0}:[]}));
 await page.route('**/api/platforms/status',route=>route.fulfill({json:{swiggy:{available:true,connected:true},zomato:{available:false,mode:'external_link'}}}));
 let menus=0;
 await page.route('**/api/platforms/swiggy/search',route=>route.fulfill({json:{restaurants:[{id:'100',name:'Synthetic Swiggy venue',area:'Bandra',distance_km:1.5,selection:'synthetic-selection'}],notice:'Synthetic provider-reported distance'}}));
 await page.route('**/api/platforms/swiggy/menu',route=>{menus++;expect(route.request().postDataJSON().selection).toBe('synthetic-selection');return route.fulfill({json:{items:[{name:'Synthetic noodles',price_paise:19950,within_budget:true,available:true,price_status:'Synthetic live-price fixture'},{name:'Synthetic variant dish',price_paise:null,within_budget:null,available:true,price_status:'Confirm price and options on Swiggy'}],notice:'Synthetic response; no actual provider contacted'}})});
 await page.goto('/');await page.getByLabel('Your food craving').fill('Hakka noodles under 300');
 await page.getByRole('button',{name:'Check Zomato and Swiggy',exact:true}).click();
 await page.getByRole('button',{name:'Check Swiggy restaurants',exact:true}).click();
 await expect(page.getByRole('button',{name:'Check menu at Synthetic Swiggy venue'})).toBeVisible();expect(menus).toBe(0);
 await page.getByRole('button',{name:'Check menu at Synthetic Swiggy venue'}).click();
 const menu=page.getByRole('region',{name:'Swiggy menu at Synthetic Swiggy venue'});
 await expect(menu).toContainText('₹199.50');await expect(menu).toContainText('Price needs confirmation');expect(menus).toBe(1);
 await page.getByLabel('Mumbai area').selectOption('Andheri');await expect(menu).toHaveCount(0);
});

test('platform availability failure has a read-only retry and leaves catalog usable',async({page})=>{
 let loads=0;
 await page.route('**/api/platforms/status',route=>++loads===1?route.fulfill({status:503,json:{detail:'Synthetic platform unavailable'}}):route.fulfill({json:{swiggy:{available:false,connected:false},zomato:{available:false,mode:'external_link'}}}));
 await page.goto('/');await page.getByRole('button',{name:'Check Zomato and Swiggy',exact:true}).click();
 await page.getByRole('button',{name:'Retry platform availability'}).click();
 await expect(page.getByText('Swiggy live search is not available on BiteAI yet.',{exact:false})).toBeVisible();
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible();expect(loads).toBe(2);
});

test('Zomato linking stays separate from unverified live menu availability',async({page})=>{
 await page.route(/\/api\/me(?:\/|\?|$)/,route=>route.fulfill({json:new URL(route.request().url()).pathname==='/api/me'?{id:991,name:'Synthetic user',email:'synthetic@example.test',role:'customer',consent:false,email_verified:true,query_count:0,verified_spend_paise:0}:[]}));
 await page.route('**/api/platforms/status',route=>route.fulfill({json:{swiggy:{available:false,connected:false},zomato:{available:false,can_connect:true,connected:true,mode:'schema_verification_pending'}}}));
 await page.route('**/api/platforms/zomato',route=>route.fulfill({json:{disconnected:true,message:'Synthetic disconnect fixture'}}));
 await page.goto('/?zomato=connected');
 const connection=page.getByRole('region',{name:'Zomato connection'});
 await expect(connection).toContainText('Live menu search is still being verified');
 await connection.getByRole('button',{name:'Disconnect Zomato'}).click();
 await expect(connection.getByRole('button',{name:'Connect Zomato'})).toBeVisible();
 expect(new URL(page.url()).searchParams.has('zomato')).toBe(false);
});

test('mobile provider controls are keyboard accessible and remain usable during connection',async({page})=>{
 await page.setViewportSize({width:360,height:800});
 await page.route(/\/api\/me(?:\/|\?|$)/,route=>route.fulfill({json:new URL(route.request().url()).pathname==='/api/me'?{id:991,name:'Synthetic user',email:'synthetic@example.test',role:'customer',consent:false,email_verified:true,query_count:0,verified_spend_paise:0}:[]}));
 await page.route('**/api/platforms/status',route=>route.fulfill({json:{swiggy:{available:true,connected:false},zomato:{available:false,can_connect:true,connected:false,mode:'schema_verification_pending'}}}));
 let release:()=>void=()=>{};const gate=new Promise<void>(resolve=>{release=resolve});let connections=0;
 await page.route('**/api/platforms/swiggy/connect',async route=>{connections++;await gate;await route.fulfill({status:503,json:{detail:'Synthetic provider connection unavailable. Please retry.'}})});
 await page.goto('/');
 const toggle=page.getByRole('button',{name:'Check Zomato and Swiggy',exact:true});await toggle.focus();await page.keyboard.press('Enter');await expect(toggle).toHaveAttribute('aria-expanded','true');
 const connect=page.getByRole('button',{name:'Connect Swiggy',exact:true});await expect(connect).toBeVisible();await expect.poll(async()=>(await connect.boundingBox())?.height??0).toBeGreaterThanOrEqual(44);
 await connect.click();await expect(connect).toBeDisabled();await expect(page.getByRole('button',{name:'Connect Zomato',exact:true})).toBeDisabled();await expect.poll(()=>connections).toBe(1);release();
 await expect(page.getByRole('status').filter({hasText:'Synthetic provider connection unavailable'})).toBeVisible();await expect(connect).toBeEnabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await toggle.focus();await page.keyboard.press('Enter');await expect(toggle).toHaveAttribute('aria-expanded','false');
});
