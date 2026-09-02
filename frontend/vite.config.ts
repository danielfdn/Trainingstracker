import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dev server runs on 5173, which app/core/config.py already lists in
// BACKEND_CORS_ORIGINS. The API base URL itself comes from VITE_API_BASE_URL
// (see .env.example) so a deployed build can point somewhere else.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
})
