// Never cache CRM data, API responses, authenticated HTML or exports.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
 if(event.request.mode==='navigate') event.respondWith(fetch(event.request).catch(()=>new Response('<!doctype html><html lang="pl"><meta name="viewport" content="width=device-width"><title>Ai Focus — offline</title><body style="font-family:system-ui;padding:40px;background:#f5f6f2;color:#122b27"><h1>Jesteś offline</h1><p>Połącz się z internetem, aby bezpiecznie otworzyć CRM.</p><a href="/">Spróbuj ponownie</a></body></html>',{headers:{'Content-Type':'text/html; charset=utf-8'}})));
});
