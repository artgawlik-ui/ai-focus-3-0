// Cache only this public offline document. Never cache CRM, authenticated HTML or exports.
const PUBLIC_CACHE='focus3-public-offline-v2';
self.addEventListener('install',event=>event.waitUntil(caches.open(PUBLIC_CACHE).then(cache=>cache.add('/offline.html')).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(Promise.all([self.clients.claim(),caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('focus3-public-')&&key!==PUBLIC_CACHE).map(key=>caches.delete(key))))])));
self.addEventListener('fetch',event=>{
 if(event.request.mode==='navigate') event.respondWith(fetch(event.request).catch(async()=>{
  const fallback=await caches.match('/offline.html');
  return fallback||new Response('<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><h1>Jesteś offline</h1><p>Połącz się z internetem, aby otworzyć CRM.</p></html>',{status:200,headers:{'Content-Type':'text/html; charset=utf-8'}});
 }));
});
