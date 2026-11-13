import {test,expect} from '@playwright/test';

test('mobile and tablet keep search reachable without horizontal overflow',async({page})=>{
 for(const width of [320,360,390,768,1024]){
  await page.setViewportSize({width,height:844});await page.goto('/');
  await expect(page.getByRole('button',{name:'Find my food',exact:true})).toBeEnabled();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  if(width<=390){const box=await page.getByRole('button',{name:'Find my food',exact:true}).boundingBox();expect(box!.y+box!.height).toBeLessThan(844)}
 }
});

test('parsed constraints update controls and can be edited without stale context',async({page})=>{
 await page.goto('/');await expect(page.getByRole('button',{name:'Find my food',exact:true})).toBeEnabled();
 await page.getByLabel('Your food craving').fill('Chinese haka noodles under 300 within 2 km');
 await page.getByRole('button',{name:'Find my food',exact:true}).click();
 await expect(page.getByLabel('Interpreted search constraints')).toContainText('hakka noodles');
 await expect(page.getByLabel('Maximum budget')).toHaveValue('300');await expect(page.getByLabel('Search radius')).toHaveValue('2');
 await expect(page.getByLabel('Interpreted search constraints')).toContainText('Bandra area centre');
 await page.getByRole('button',{name:'Edit search',exact:true}).click();
 const editor=page.locator('#constraint-editor');await editor.getByLabel('Dish',{exact:true}).fill('pizza');await editor.getByLabel('Cuisine',{exact:true}).fill('Italian');
 await editor.getByLabel('Budget (₹)',{exact:true}).fill('200');await editor.getByLabel('Search location').selectOption('Andheri');
 await page.getByRole('button',{name:'Apply search filters'}).click();
 await expect(page.getByLabel('Interpreted search constraints')).toContainText('pizza');await expect(page.getByLabel('Interpreted search constraints')).toContainText('Andheri area centre');
 await expect(page.getByLabel('Maximum budget')).toHaveValue('200');
});

test('voice permission errors explain recovery and preserve text input',async({page})=>{
 await page.addInitScript(()=>{class DeniedSpeech{onerror:((event:{error:string})=>void)|null=null;start(){this.onerror?.({error:'not-allowed'})}}Object.defineProperty(window,'SpeechRecognition',{value:DeniedSpeech})});
 await page.goto('/');await page.getByRole('button',{name:'Search by voice'}).click();
 await expect(page.getByRole('alert').filter({hasText:'Microphone permission'})).toContainText('Microphone permission was denied');await expect(page.getByLabel('Your food craving')).toBeEnabled();
});
