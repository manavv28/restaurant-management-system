import {test,expect} from '@playwright/test';

test('Hinglish streaming verdict preserves context and exposes honest confidence',async({page})=>{
 await page.goto('/');await page.getByLabel('Your food craving').fill('Chinese khane ka mann hai, Hakka noodles 300 mein 2 km ke andar Bandra mein?');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 const verdict=page.getByRole('region',{name:'Your food verdict'});await expect(verdict).toContainText('₹240');await expect(verdict).toContainText('Confirm current price');
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
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await expect(page.getByRole('link',{name:'Coverage & list view'})).toHaveAttribute('href','/');await page.getByRole('link',{name:'Coverage & list view'}).click();await expect(page.getByText('Our Mumbai data collection',{exact:true})).toBeVisible();
});
