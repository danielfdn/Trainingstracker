import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// In development the app runs on 5173 and talks to the backend on 8000, which
// app/core/config.py allows via CORS. A production build is served by the
// backend itself, so it calls its own origin and CORS never comes up.
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      // The app updates itself on the next launch. Safe here because the
      // live workout keeps its draft in localStorage, which survives the
      // reload — an in-memory workout screen would make this a data-loss bug.
      registerType: 'autoUpdate',
      includeAssets: ['apple-touch-icon.png', 'favicon.png'],
      manifest: {
        name: 'Trainingstracker',
        short_name: 'Training',
        description: 'Workout plans, live set logging and monthly progress.',
        start_url: '/',
        scope: '/',
        // No browser chrome: the point of installing it.
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#0b0d10',
        theme_color: '#0b0d10',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'pwa-maskable-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            // Android crops icons to its own shape; the mark stays inside
            // the middle 80% so nothing important is cut off.
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,png,svg,woff2}'],
        // Any in-app route resolves to index.html — React Router does the rest.
        navigateFallback: 'index.html',
        // ...except the API, which must never be answered with the app shell.
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            // Reads only. Online you always get fresh data; offline you get
            // the last thing you saw, which is enough to run a workout from
            // your plan. Writes are deliberately absent: they go straight to
            // the network and fail honestly, because the only write that
            // must survive offline — logging sets — is already handled by
            // the local draft and the one-shot sync on finish.
            urlPattern: ({ url, request }) =>
              request.method === 'GET' && url.pathname.startsWith('/api/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'trainingstracker-api',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 * 14 },
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
      devOptions: {
        // Off in dev: a service worker caching a hot-reloading app is a
        // reliable way to debug something that is not happening.
        enabled: false,
      },
    }),
  ],
  server: { port: 5173 },
})
