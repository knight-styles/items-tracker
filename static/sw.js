const CACHE_NAME = 'safety-tracker-v2';
const PRECACHE_ASSETS = [
  '/',
  '/static/css/base.css',
  '/static/manifest.json',
  '/static/offline.html',
  '/static/images/pwa/icon-192.png',
  '/static/images/pwa/icon-512.png'
];

// Install Event: Pre-cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: Cleanup old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Intelligent caching strategy
self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Ignore non-GET requests (e.g. POST log submissions)
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Static assets & uploaded item images: Cache-First strategy
  if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/')) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) return cachedResponse;
        return fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseToCache);
            });
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // HTML navigation & API requests: Network-First strategy with fallback
  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache);
          });
        }
        return networkResponse;
      })
      .catch(async () => {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) return cachedResponse;
        if (request.headers.get('accept') && request.headers.get('accept').includes('text/html')) {
          return caches.match('/static/offline.html');
        }
      })
  );
});

// Allow clients to trigger skipWaiting
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
