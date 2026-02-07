import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import Ads from './pages/Ads'
import PriceMonitor from './pages/PriceMonitor'
import Sellers from './pages/Sellers'
import SellerDetail from './pages/SellerDetail'
import UrlScraper from './pages/UrlScraper'
import Layout from './components/Layout'
import './App.css'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:id" element={<ProductDetail />} />
          <Route path="/ads" element={<Ads />} />
          <Route path="/price-monitor" element={<PriceMonitor />} />
          <Route path="/sellers" element={<Sellers />} />
          <Route path="/sellers/:merchantId" element={<SellerDetail />} />
          <Route path="/url-scraper" element={<UrlScraper />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
