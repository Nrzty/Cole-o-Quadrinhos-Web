// Service Worker simples apenas para liberar a função de Instalação (PWA) no celular
self.addEventListener('install', (e) => {
    console.log('[Service Worker] Install');
});

self.addEventListener('fetch', (e) => {
    // Pass-through
    return;
});
