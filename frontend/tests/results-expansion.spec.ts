import {test,expect} from '@playwright/test';

test('restaurant cards start at three and expand only on request, resetting for a new search',async({page})=>{
 await page.route('**/api/search',route=>{
  const {query}=route.request().postDataJSON();
  const count=query==='few'?2:6;
  return route.fulfill({json:{results:Array.from({length:count},(_,i)=>({restaurant:{id:8000+i,name:'Synthetic result '+(i+1),area:'Bandra',address:'Synthetic fixture',latitude:19.0596,longitude:72.8295,cuisine:'Chinese',sample:false},dish:{id:9000+i,name:'Hakka noodles',price_paise:10000+i*100,source:'Synthetic fixture'},distance_km:1,offers:[],reason:'Synthetic expansion fixture'})),trace:[],parser:'Synthetic fixture',follow_up:'',attribution:'',external_discovery:[]}});
 });
 await page.goto('/');
 const cards=page.locator('.restaurant-card');
 await expect(cards).toHaveCount(3);
 await page.getByRole('button',{name:'Show more (3)',exact:true}).click();
 await expect(cards).toHaveCount(6);
 await expect(page.getByRole('button',{name:'Show less',exact:true})).toHaveAttribute('aria-expanded','true');
 await page.getByRole('button',{name:'Show less',exact:true}).click();await expect(cards).toHaveCount(3);
 await page.getByRole('button',{name:'Show more (3)',exact:true}).click();
 await page.getByLabel('Your food craving').fill('another search');await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(cards).toHaveCount(3);await expect(page.getByRole('button',{name:'Show more (3)',exact:true})).toHaveAttribute('aria-expanded','false');
 await page.getByLabel('Your food craving').fill('few');await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(cards).toHaveCount(2);await expect(page.getByRole('button',{name:/Show more|Show less/})).toHaveCount(0);
});
