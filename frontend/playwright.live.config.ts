import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./live-checks',workers:1,timeout:360000,expect:{timeout:20000},use:{baseURL:process.env.LIVE_BASE_URL||'https://restaurant-management-system-qxtx.vercel.app',headless:true,viewport:{width:390,height:844},launchOptions:{executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']}},reporter:'list'});
