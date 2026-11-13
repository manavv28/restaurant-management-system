import {test,expect} from '@playwright/test';

test('total budget stays unconfirmed and results precede optional discovery content',async({page})=>{
 await page.goto('/');
 await page.getByLabel('Your food craving').fill('Hakka noodles for two people under 500 total delivery');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 const verdict=page.getByRole('region',{name:'Your food verdict'});
 await expect(verdict).toContainText('Listed subtotal ₹480; final total unconfirmed.');
 await expect(verdict).toContainText('not walking routes');
 await page.getByText('Final total unconfirmed · price breakdown',{exact:true}).first().click();
 await expect(page.getByText('Listed subtotal (2 items): ₹480')).toBeVisible();
 const order=await page.evaluate(()=>{
  const verdict=document.querySelector('[aria-label="Your food verdict"]');
  const coverage=[...document.querySelectorAll('strong')].find(el=>el.textContent==='Our Mumbai data collection');
  return !!verdict&&!!coverage&&!!(verdict.compareDocumentPosition(coverage)&Node.DOCUMENT_POSITION_FOLLOWING);
 });
 expect(order).toBeTruthy();
 await page.getByRole('button',{name:/Check Zomato and Swiggy/}).click();
 await expect(page.getByText('Public links · current platform prices are checked on their websites')).toBeVisible();
 await expect(page.getByText(/BiteAI has not compared live platform quotes/)).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});

test('excluded noodles return other Chinese food and area follow-up keeps the budget',async({page})=>{
 await page.goto('/');await page.getByLabel('Your food craving').fill('Chinese no noodles under 300 within 2 km');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 const verdict=page.getByRole('region',{name:'Your food verdict'});
 await expect(verdict).toContainText('Vegetable fried rice');
 await expect(page.locator('.restaurant-grid')).not.toContainText('Hakka noodles');
 await page.getByLabel('Your food craving').fill('same budget, Andheri mein');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(verdict).toContainText('Andheri · Up to ₹300 · 2 km');
});
