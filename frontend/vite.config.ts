import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Parent dizinden .env oku (SUPABASE_URL, SUPABASE_ANON_KEY)
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')

  return {
    define: {
      'import.meta.env.VITE_SUPABASE_URL': JSON.stringify(env.SUPABASE_URL || ''),
      'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify(env.SUPABASE_ANON_KEY || ''),
    },
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5000,
      allowedHosts: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-plotly': ['plotly.js', 'react-plotly.js'],
            'vendor-axios': ['axios'],
          },
        },
      },
    },
  }
})
