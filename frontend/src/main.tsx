import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const disableStrictMode = import.meta.env.DEV && (import.meta.env.VITE_DISABLE_STRICT_MODE ?? 'true') === 'true'
const rootElement = document.getElementById('root')!

createRoot(rootElement).render(
  disableStrictMode ? (
    <App />
  ) : (
    <StrictMode>
      <App />
    </StrictMode>
  ),
)
