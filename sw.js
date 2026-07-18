// Service Worker para Gasteiz Live PWA
// Estrategia: Network First con fallback a cache para HTML/CSS/JS
// Las noticias (news.json) siempre se intentan obtener de la red

const CACHE_NAME = 'gasteiz-live-v1';

// Archivos esenciales para cachear en la instalación
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/style.css',
    '/app.js',
    '/icon-192.png',
    '/icon-512.png'
];

// Instalación: cachear los archivos estáticos esenciales
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    // Activar inmediatamente sin esperar a que se cierren las pestañas anteriores
    self.skipWaiting();
});

// Activación: limpiar caches antiguos
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            );
        })
    );
    // Tomar control de todas las pestañas abiertas inmediatamente
    self.clients.claim();
});

// Fetch: Network First para todo (priorizar contenido fresco)
self.addEventListener('fetch', event => {
    // Solo manejar peticiones GET
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Si la respuesta de red es válida, la cacheamos y la devolvemos
                if (response.ok) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            })
            .catch(() => {
                // Si falla la red, intentar servir desde cache
                return caches.match(event.request);
            })
    );
});
