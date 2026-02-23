import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Layout from './components/Layout'
import ApiKeyModal from './components/ApiKeyModal'
import './App.css'

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

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Layout>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:id" element={<ProductDetail />} />
            <Route path="/ads" element={<Ads />} />
            <Route path="/price-monitor" element={<PriceMonitor />} />
            <Route path="/sellers" element={<Sellers />} />
            <Route path="/sellers/:merchantId" element={<SellerDetail />} />
            <Route path="/hepsiburada" element={<HepsiburadaProducts />} />
            <Route path="/trendyol" element={<TrendyolProducts />} />
            <Route path="/web-products" element={<WebProducts />} />
            <Route path="/url-scraper" element={<UrlScraper />} />
            <Route path="/video-transcripts" element={<VideoTranscripts />} />
            <Route path="/json-editor" element={<JsonEditor />} />
            <Route path="/category-explorer" element={<CategoryExplorer />} />
          </Routes>
        </Suspense>
      </Layout>
      <ApiKeyModal />
    </Router>
  )
}

export default App
