var CACHE = 'adulam-v3';

// Solo cacheamos los assets estáticos seguros
var ASSETS = [
  '/static/style.css',
  '/static/manifest.json'
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(cache) {
      // addAll falla si algún recurso no existe, usamos add individual
      return Promise.allSettled(
        ASSETS.map(function(url) { return cache.add(url); })
      );
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE; })
            .map(function(k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

// Network first siempre — la app es local y siempre hay red
// Cache como fallback solo para assets estáticos
self.addEventListener('fetch', function(e) {
  var url = new URL(e.request.url);

  if (e.request.method !== 'GET') { return; }

  if (url.pathname.startsWith('/static/')) {
    // Cache first para assets
    e.respondWith(
      caches.match(e.request).then(function(cached) {
        var networkFetch = fetch(e.request).then(function(resp) {
          if (resp && resp.status === 200) {
            var clone = resp.clone();
            caches.open(CACHE).then(function(cache) { cache.put(e.request, clone); });
          }
          return resp;
        });
        return cached || networkFetch;
      })
    );
  } else {
    // Network first para rutas Flask
    e.respondWith(
      fetch(e.request).catch(function() {
        return caches.match(e.request);
      })
    );
  }
});