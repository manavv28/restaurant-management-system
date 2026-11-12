import {test,expect} from '@playwright/test';

test('citywide directory loads lazily, filters and paginates',async({page})=>{
 const requests:string[]=[];
 await page.route('**/api/catalog/restaurants?**',async route=>{
  const url=new URL(route.request().url());requests.push(url.search);
  const later=url.searchParams.get('after')==='501';
  await route.fulfill({json:{restaurants:[{id:later?502:501,name:later?'Second fixture café':'First fixture café',area:'Borivali',address:'Synthetic browser fixture',cuisine:'Unspecified'}],next_cursor:later?null:501}});
 });
 await page.goto('/');
 await expect(page.getByRole('button',{name:'Find my food'})).toBeEnabled();
 expect(requests).toHaveLength(0);
 await page.getByRole('button',{name:'Browse Mumbai restaurant directory'}).click();
 const directory=page.getByRole('region',{name:'Mumbai restaurant directory'});
 await expect(directory.getByRole('button',{name:'First fixture café'})).toBeVisible();
 await directory.getByRole('button',{name:'Next page'}).click();
 await expect(directory.getByRole('button',{name:'Second fixture café'})).toBeVisible();
 await expect(directory.getByRole('button',{name:'Next page'})).toBeDisabled();
 await directory.getByLabel('Restaurant name').fill('Fixture');
 await directory.getByLabel('Search area').selectOption('Borivali');
 await directory.getByRole('button',{name:'Search directory'}).click();
 await expect(directory.getByRole('button',{name:'First fixture café'})).toBeVisible();
 expect(requests.at(-1)).toContain('area=Borivali');expect(requests.at(-1)).toContain('after=0');
});

test('catalog source notices are publicly available',async({page})=>{
 await page.goto('/data-sources');
 await expect(page.getByRole('heading',{name:'BiteAI data sources'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Overture Maps'})).toBeVisible();
 await expect(page.getByText('Copyright 2024 Foursquare Labs, Inc.',{exact:false})).toBeVisible();
 await expect(page.getByRole('link',{name:'NOTICE.txt'})).toHaveAttribute('href','https://opensource.foursquare.com/places-notice-txt/');
});
