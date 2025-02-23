self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('recipe-ai-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/static/js/main.js',
        '/static/css/styles.css',
        '/templates/index.html'
      ]);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
