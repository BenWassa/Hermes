/* Service Worker for The Daily PWA */
const CACHE = 'the-daily-v1';
const SHELL = [
  '/Hermes/',
  '/Hermes/index.html',
  '/Hermes/manifest.json',
  '/Hermes/icons/icon-192.svg',
  '/Hermes/icons/icon-512.svg',
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

/* Network-first for the main document (always get fresh edition), cache-first for assets. */
self.addEventListener('fetch', function (e) {
  var url = e.request.url;
  var isDocument = e.request.mode === 'navigate';

  if (isDocument) {
    e.respondWith(
      fetch(e.request).then(function (res) {
        var clone = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, clone); });
        return res;
      }).catch(function () {
        return caches.match(e.request);
      })
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(function (cached) {
      return cached || fetch(e.request).then(function (res) {
        var clone = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, clone); });
        return res;
      });
    })
  );
});
