import {test,expect} from '@playwright/test';

test('cold backend waits visibly and sends search only after JSON readiness succeeds',async({page})=>{
 let warm=false;let posts=0;let earlyAccountReads=0;
 await page.route('**/api/health',route=>warm?route.continue():route.fulfill({status:503,contentType:'text/html',body:'<!DOCTYPE html><title>Starting</title>'}));
 await page.route('**/api/catalog/coverage',route=>warm?route.continue():route.fulfill({status:503,json:{status:'unavailable'}}));
 await page.route('**/api/search',route=>{posts++;return route.continue()});
 await page.route('**/api/me',route=>{if(!warm)earlyAccountReads++;return route.continue()});
 await page.goto('/');
 await expect(page.getByText('Starting the search service. This may take up to a minute.',{exact:true})).toBeVisible();
 expect(posts).toBe(0);expect(earlyAccountReads).toBe(0);warm=true;
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible({timeout:15000});
 expect(posts).toBe(1);
 await expect(page.getByText(/Unexpected token/)).toHaveCount(0);
});

test('HTML search failures show a useful message and do not replay the POST',async({page})=>{
 let posts=0;
 await page.route('**/api/search',route=>{posts++;return route.fulfill({status:502,contentType:'text/html',body:'<!DOCTYPE html><title>Gateway error</title>'})});
 await page.goto('/');
 await expect(page.getByText('The service is temporarily unavailable or still starting. Please try again shortly.',{exact:true})).toBeVisible();
 expect(posts).toBe(1);
 await expect(page.getByText(/Unexpected token/)).toHaveCount(0);
});

test('coverage refreshes after search and focus instead of keeping an old zero',async({page})=>{
 let loads=0;let latest=91;
 await page.route('**/api/catalog/coverage',route=>route.fulfill({json:{real_restaurants:378,sample_restaurants:0,fresh_source_menu_items:loads++===0?0:latest,last_successful_collection:'2026-11-12T09:16:05+00:00',coverage:'Isolated coverage fixture',attribution:'Fixture only'}}));
 await page.goto('/');
 const priceCount=page.locator('aside.catalog-panel .catalog-numbers span').filter({hasText:'source-listed dish prices'}).locator('b');
 await expect(priceCount).toHaveText('91');
 latest=92;await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await expect(priceCount).toHaveText('92');
});

test('expired readiness shows retry instead of no matches, then recovers once',async({page})=>{
 await page.clock.install();let warm=false;let posts=0;
 await page.route('**/api/health',route=>warm?route.continue():route.fulfill({status:503,json:{status:'unavailable'}}));
 await page.route('**/api/catalog/coverage',route=>warm?route.continue():route.fulfill({status:503,json:{status:'unavailable'}}));
 await page.route('**/api/search',route=>{posts++;return route.continue()});
 await page.goto('/');
 await expect(page.getByText('Starting the search service. This may take up to a minute.',{exact:true})).toBeVisible();
 await page.clock.fastForward(91000);
 await expect(page.getByRole('heading',{name:'Search could not connect'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'No priced menu matches'})).toHaveCount(0);
 await expect(page.getByText('No matches just yet',{exact:true})).toHaveCount(0);
 expect(posts).toBe(0);warm=true;
 await page.getByRole('button',{name:'Retry search',exact:true}).click();
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible({timeout:15000});
 expect(posts).toBe(1);
 await expect(page.getByRole('heading',{name:'Search could not connect'})).toHaveCount(0);
});


test('healthy catalog permits one search when the health probe is unavailable',async({page})=>{
 let posts=0;
 await page.route('**/api/health',route=>route.fulfill({status:503,json:{status:'unavailable'}}));
 await page.route('**/api/search',route=>{posts++;return route.continue()});
 await page.goto('/');
 await expect(page.getByRole('button',{name:'Wok & Wonder',exact:true})).toBeVisible({timeout:15000});
 expect(posts).toBe(1);
 await expect(page.getByRole('heading',{name:'Search could not connect'})).toHaveCount(0);
});
