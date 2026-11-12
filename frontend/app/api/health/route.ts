import {searchHealth} from '../../../shared/search-health';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function GET(){
 return searchHealth(process.env.API_INTERNAL_URL||'http://127.0.0.1:8000');
}
