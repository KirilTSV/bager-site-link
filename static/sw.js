// Cache only public, versioned static assets. Never cache authenticated HTML or API data.
const CACHE='bager-site-link-static-v2';
const STATIC=['/static/app.css','/static/app.js','/static/bager-site-link-logo.jpg'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(STATIC)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const req=event.request;
 if(req.method!=='GET')return;
 const path=new URL(req.url).pathname;
 if(!STATIC.includes(path))return; // No session, API, dashboard or GPS caching.
 event.respondWith(fetch(req).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(req,copy));}return response;}).catch(()=>caches.match(req)));
});
