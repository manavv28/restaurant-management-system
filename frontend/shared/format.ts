export const indianDate=(value:string)=>new Date(value).toLocaleDateString('en-IN',{timeZone:'Asia/Kolkata',day:'numeric',month:'short',year:'numeric'});
export const indianTime=(value:string)=>new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})+' IST';
