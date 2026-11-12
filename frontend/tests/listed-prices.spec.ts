import {test,expect} from '@playwright/test';

test('listed prices retain paise, original date, context and source link',async({page})=>{
 const restaurant={id:990,name:'Synthetic price venue',area:'Bandra',address:'Browser fixture only',latitude:19.0596,longitude:72.8295,cuisine:'Indian',sample:false,source:'Synthetic fixture',phone_source:{source_url:'https://indiarestros.com/api/v1/restaurants/IRR-0000000001',source_observed_at:'2026-10-18T00:00:00Z',status:'Public source listing; not independently verified'},updated_at:'2026-11-12T00:00:00Z',rating:null,review_count:null,phone:'',website:'',opening_hours:'Unknown',image_url:'',image_attribution:'',ordering_url:'',ownership_verified:false,pin_code:''};
 const dish={id:991,name:'Synthetic paneer dish',price_paise:19950,source:'IndiaRestros public menu listing',available:true,cuisine:'Indian',category:'Main',description:'',price_status:'Third-party listing price · source date 2026-10-18 · delivery listing · confirm current price',price_is_reference:true,source_observed_at:'2026-10-18T00:00:00Z',source_url:'https://indiarestros.com/r/synthetic-price-venue/menu'};
 await page.route('**/api/search',route=>route.fulfill({json:{results:[{restaurant,dish,distance_km:0,reason:'Synthetic listed-price fixture',offers:[]}],trace:[],parser:'fixture',attribution:'',nearby_unpriced:[],external_discovery:[]}}));
 await page.route('**/api/restaurants/990',route=>route.fulfill({json:{restaurant,menu:[dish]}}));
 await page.route('**/api/restaurants/990/click',route=>route.fulfill({json:{recorded:true}}));
 await page.route('**/api/catalog/coverage',route=>route.fulfill({json:{real_restaurants:10404,source_priced_restaurants:2,sample_restaurants:0,fresh_source_menu_items:123,last_successful_collection:'2026-11-12T00:00:00Z',coverage:'Third-party listing fixture; not real-time restaurant quotes',attribution:'Synthetic fixture'}}));
 await page.goto('/');
 await expect(page.getByRole('button',{name:'Synthetic price venue',exact:true})).toBeVisible();
 await expect(page.locator('.dish-row strong')).toHaveText('₹199.50');
 await expect(page.getByText('Listed price within budget',{exact:true})).toBeVisible();
 await expect(page.locator('.catalog-numbers')).toContainText('123 source-listed dish prices');
 await expect(page.locator('.catalog-numbers')).toContainText('2 restaurants with listed prices');
 await page.getByRole('button',{name:'Synthetic price venue',exact:true}).click();
 const modal=page.getByRole('dialog');
 await expect(modal).toContainText('₹199.50');await expect(modal).toContainText('2026-10-18');
 await expect(modal.getByRole('link',{name:'Contact source'})).toHaveAttribute('href','https://indiarestros.com/api/v1/restaurants/IRR-0000000001');await expect(modal).toContainText('Source listing');await expect(modal).toContainText('delivery listing');
 await expect(modal.getByRole('link',{name:'Price source'})).toHaveAttribute('href',dish.source_url);
});
