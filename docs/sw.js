/* Service Worker for The Daily PWA */
const CACHE = 'the-daily-v2';
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

/*
 * Navigation is network-first so the current paper wins, with the cached paper
 * as the offline fallback. Same-origin static assets are cache-first. Remote
 * provider imagery is deliberately left to normal HTTP/browser caching: do not
 * retain opaque third-party logo responses indefinitely in the PWA shell cache.
 */
self.addEventListener('fetch', function (e) {
  var request = e.request;
  var isDocument = request.mode === 'navigate';
  var requestUrl = new URL(request.url);
  var sameOrigin = requestUrl.origin === self.location.origin;

  if (isDocument) {
    e.respondWith(
      fetch(request).then(function (res) {
        if (res && res.ok) {
          var clone = res.clone();
          caches.open(CACHE).then(function (c) { c.put(request, clone); });
        }
        return res;
      }).catch(function () {
        return caches.match(request).then(function (cached) {
          return cached || caches.match('/Hermes/index.html');
        });
      })
    );
    return;
  }

  if (!sameOrigin) {
    e.respondWith(fetch(request));
    return;
  }

  e.respondWith(
    caches.match(request).then(function (cached) {
      return cached || fetch(request).then(function (res) {
        if (res && res.ok) {
          var clone = res.clone();
          caches.open(CACHE).then(function (c) { c.put(request, clone); });
        }
        return res;
      });
    })
  );
});
