import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    optimizeDeps: {
        exclude: ['lucide-react'],
    },
    server: {
        proxy: {
            // Backend Express server (server/index.js listens on PORT=5000 from .env)
            '/api': 'http://localhost:5000'
        }
    }
});