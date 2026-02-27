import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { Toaster } from 'sonner'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import ChatPanel from './components/ChatPanel'
import PageSkeleton from './components/Skeleton'
import './App.css'

// Auth sayfalar (public)
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const Landing = lazy(() => import('./pages/Landing'))

// Uygulama sayfalar (protected)
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Products = lazy(() => import('./pages/Products'))
const ProductDetail = lazy(() => import('./pages/ProductDetail'))
const Ads = lazy(() => import('./pages/Ads'))
const PriceMonitor = lazy(() => import('./pages/PriceMonitor'))
const Sellers = lazy(() => import('./pages/Sellers'))
const SellerDetail = lazy(() => import('./pages/SellerDetail'))
const HepsiburadaProducts = lazy(() => import('./pages/HepsiburadaProducts'))
const TrendyolProducts = lazy(() => import('./pages/TrendyolProducts'))
const WebProducts = lazy(() => import('./pages/WebProducts'))
const UrlScraper = lazy(() => import('./pages/UrlScraper'))
const VideoTranscripts = lazy(() => import('./pages/VideoTranscripts'))
const JsonEditor = lazy(() => import('./pages/JsonEditor'))
const CategoryExplorer = lazy(() => import('./pages/CategoryExplorer'))
const Settings = lazy(() => import('./pages/Settings'))
const Onboarding = lazy(() => import('./pages/Onboarding'))

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/landing" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Onboarding (protected, no layout) */}
      <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />

      {/* Protected routes */}
      <Route path="/" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
      <Route path="/products" element={<ProtectedRoute><Layout><Products /></Layout></ProtectedRoute>} />
      <Route path="/products/:id" element={<ProtectedRoute><Layout><ProductDetail /></Layout></ProtectedRoute>} />
      <Route path="/ads" element={<ProtectedRoute><Layout><Ads /></Layout></ProtectedRoute>} />
      <Route path="/price-monitor" element={<ProtectedRoute><Layout><PriceMonitor /></Layout></ProtectedRoute>} />
      <Route path="/sellers" element={<ProtectedRoute><Layout><Sellers /></Layout></ProtectedRoute>} />
      <Route path="/sellers/:merchantId" element={<ProtectedRoute><Layout><SellerDetail /></Layout></ProtectedRoute>} />
      <Route path="/hepsiburada" element={<ProtectedRoute><Layout><HepsiburadaProducts /></Layout></ProtectedRoute>} />
      <Route path="/trendyol" element={<ProtectedRoute><Layout><TrendyolProducts /></Layout></ProtectedRoute>} />
      <Route path="/web-products" element={<ProtectedRoute><Layout><WebProducts /></Layout></ProtectedRoute>} />
      <Route path="/url-scraper" element={<ProtectedRoute><Layout><UrlScraper /></Layout></ProtectedRoute>} />
      <Route path="/video-transcripts" element={<ProtectedRoute><Layout><VideoTranscripts /></Layout></ProtectedRoute>} />
      <Route path="/json-editor" element={<ProtectedRoute><Layout><JsonEditor /></Layout></ProtectedRoute>} />
      <Route path="/category-explorer" element={<ProtectedRoute><Layout><CategoryExplorer /></Layout></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Layout><Settings /></Layout></ProtectedRoute>} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <ErrorBoundary>
          <Suspense fallback={<PageSkeleton />}>
            <AppRoutes />
          </Suspense>
        </ErrorBoundary>
        <ChatPanel />
        <Toaster
          position="top-right"
          toastOptions={{
            className: 'bg-[var(--surface-raised)] text-[var(--color-dark-300)] border border-[var(--surface-border)] shadow-lg',
            style: {
              fontFamily: 'Inter, sans-serif',
            },
          }}
          richColors
        />
      </Router>
    </AuthProvider>
  )
}

export default App
