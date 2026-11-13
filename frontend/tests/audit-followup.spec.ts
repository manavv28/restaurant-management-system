import {test,expect} from '@playwright/test';

test('Hindi voice wording updates the actual budget and preserves a matched dish in its menu',async({page})=>{
 await page.goto('/');
 await page.getByLabel('Your food craving').fill('Mujhe Bandra mein 2 km ke andar 300 rupaye mein hakka noodles chahiye');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(page.getByLabel('Maximum budget')).toHaveValue('300');
 const verdict=page.getByRole('region',{name:'Your food verdict'});
 await expect(verdict).toContainText('₹240');
 await page.setViewportSize({width:390,height:844});await verdict.scrollIntoViewIfNeeded();
 await page.screenshot({path:'test-results/audit-fixed-mobile-search.png'});
 await verdict.getByRole('button',{name:'View menu for Sample · Wok & Wonder',exact:true}).click();
 const first=page.getByRole('dialog').locator('.menu-row').first();
 await expect(first).toHaveClass(/matched-menu-row/);
 await expect(first).toContainText('Your search match');
 await expect(first).toContainText('Hakka noodles');
});

test('unsupported location gets a visible clarification instead of Bandra matches',async({page})=>{
 await page.goto('/');await page.getByLabel('Your food craving').fill('Hakka noodles under 300 within 2 km in Thane');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 const verdict=page.getByRole('region',{name:'Your food verdict'});
 await expect(verdict).toContainText('Confirm your search location');
 await expect(page.getByLabel('Interpreted search constraints')).toContainText('Confirm search location');
 await expect(page.locator('.restaurant-card')).toHaveCount(0);
 await page.getByRole('button',{name:'Edit search',exact:true}).click();
 await page.locator('#constraint-editor').getByLabel('Search location').selectOption('Bandra');
 await page.getByRole('button',{name:'Apply search filters'}).click();
 await expect(verdict).toContainText('₹240');
});

test('multiple dietary labels remain visible without claiming an unverified match',async({page})=>{
 await page.goto('/');await page.getByLabel('Your food craving').fill('vegan gluten free hakka noodles under 300 in Bandra');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 const constraints=page.getByLabel('Interpreted search constraints');
 await expect(constraints).toContainText('vegan');await expect(constraints).toContainText('gluten-free');
 const verdict=page.getByRole('region',{name:'Your food verdict'});
 await expect(verdict).toContainText('No priced match with the requested dietary labels');
 await expect(verdict).toContainText('Only explicitly declared');
 await expect(page.locator('.restaurant-card')).toHaveCount(0);
});

test('restaurant CTA selects owner and retains that intent across sign-in toggle',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'For restaurants',exact:true}).click();
 await page.getByRole('button',{name:'Register your restaurant',exact:true}).click();
 await expect(page.getByLabel('Account type')).toHaveValue('owner');
 await page.getByRole('button',{name:'Already have an account? Sign in'}).click();
 await page.getByRole('button',{name:'New here? Create an account'}).click();
 await expect(page.getByLabel('Account type')).toHaveValue('owner');
});

test('budget scope is a user control and a total remains explicitly unconfirmed',async({page})=>{
 let release:()=>void=()=>{};const initial=new Promise<void>(resolve=>{release=resolve});
 await page.route('**/api/search',async route=>{if(!route.request().postDataJSON().query)await initial;await route.continue()});
 await page.goto('/');await page.getByLabel('Budget scope').selectOption('total');release();
 await expect(page.getByRole('button',{name:'Find my food',exact:true})).toBeEnabled();
 await expect(page.getByLabel('Budget scope')).toHaveValue('total');
 await page.getByLabel('Your food craving').fill('Hakka noodles under 300 for 2 people');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(page.getByLabel('Interpreted search constraints')).toContainText('₹300 total');
 await expect(page.getByRole('region',{name:'Your food verdict'})).toContainText('₹480');
 await expect(page.getByRole('region',{name:'Your food verdict'})).toContainText('Final payable total is unconfirmed');
});

test('phone navigation, filter sheet and voice targets stay usable at 320–430px',async({page})=>{
 for(const width of [320,390,430]){
  await page.setViewportSize({width,height:844});await page.goto('/concierge');
  await expect(page.getByRole('region',{name:'Your food verdict'})).toBeVisible();
  await page.getByLabel('More navigation').click();
  await expect(page.getByRole('link',{name:'Agent activity',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:'Map discovery',exact:true})).toBeVisible();
  await page.getByLabel('More navigation').press('Escape');
  const voice=await page.getByRole('button',{name:'Search by voice',exact:true}).boundingBox();
  expect(voice!.width).toBeGreaterThanOrEqual(44);expect(voice!.height).toBeGreaterThanOrEqual(44);
  await page.getByRole('button',{name:'Search filters',exact:true}).click();
  await expect(page.getByLabel('Budget scope')).toBeVisible();
  await page.getByRole('button',{name:'Done',exact:true}).click();
  await expect(page.getByLabel('Budget scope')).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
 }
 await page.screenshot({path:'test-results/audit-fixed-mobile-map.png'});
});
