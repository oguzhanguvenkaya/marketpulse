import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getSellers } from '../services/api';
import type { SellerInfo } from '../services/api';

const API_BASE = '/api';

export default function Sellers() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPlatform = (searchParams.get('platform') as 'hepsiburada' | 'trendyol') || 'hepsiburada';
  const [platform, setPlatform] = useState<'hepsiburada' | 'trendyol'>(initialPlatform);
  const [sellers, setSellers] = useState<SellerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [bulkExporting, setBulkExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState({ current: 0, total: 0, sellerName: '' });

  useEffect(() => {
    setSearchParams({ platform });
  }, [platform, setSearchParams]);

  useEffect(() => {
    fetchSellers();
  }, [platform]);

  const fetchSellers = async () => {
    setLoading(true);
    try {
      const data = await getSellers(platform);
      setSellers(data.sellers);
    } catch (error) {
      console.error('Error fetching sellers:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredSellers = sellers.filter(seller => 
    seller.merchant_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sellersWithAlerts = filteredSellers.filter(s => s.price_alert_count > 0 || s.campaign_alert_count > 0);

  const formatRating = (rating?: number) => {
    if (!rating) return '-';
    return rating.toFixed(1);
  };

  const getCardBackground = (seller: SellerInfo) => {
    if (seller.price_alert_count > 0 && seller.campaign_alert_count > 0) {
      return 'bg-gradient-to-br from-red-900/30 to-orange-900/30 border border-red-500/30';
    } else if (seller.price_alert_count > 0) {
      return 'bg-red-900/30 border border-red-500/30';
    } else if (seller.campaign_alert_count > 0) {
      return 'bg-orange-900/30 border border-orange-500/30';
    }
    return 'bg-[#3a3a3a]';
  };

  const handleBulkExport = async () => {
    if (sellersWithAlerts.length === 0) return;

    setBulkExporting(true);
    setExportProgress({ current: 0, total: sellersWithAlerts.length, sellerName: '' });

    for (let i = 0; i < sellersWithAlerts.length; i++) {
      const seller = sellersWithAlerts[i];
      setExportProgress({ current: i + 1, total: sellersWithAlerts.length, sellerName: seller.merchant_name });

      try {
        const response = await fetch(`${API_BASE}/sellers/${seller.merchant_id}/export?platform=${platform}`);
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${seller.merchant_name.replace(/[^a-z0-9]/gi, '_')}_products.csv`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
        }
      } catch (error) {
        console.error(`Error exporting ${seller.merchant_name}:`, error);
      }

      if (i < sellersWithAlerts.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }

    setBulkExporting(false);
    setExportProgress({ current: 0, total: 0, sellerName: '' });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sellers</h1>
          <p className="text-neutral-400 mt-1">View all sellers and their alert products</p>
        </div>
        {sellersWithAlerts.length > 0 && (
          <button
            onClick={handleBulkExport}
            disabled={bulkExporting}
            className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {bulkExporting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-dark-900"></div>
                <span>Exporting {exportProgress.current}/{exportProgress.total}</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>Bulk Export ({sellersWithAlerts.length})</span>
              </>
            )}
          </button>
        )}
      </div>

      {bulkExporting && (
        <div className="card-dark p-4 border border-accent-primary/30">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-accent-primary"></div>
            <div>
              <div className="text-white font-medium">Exporting: {exportProgress.sellerName}</div>
              <div className="text-neutral-400 text-sm">{exportProgress.current} of {exportProgress.total} sellers</div>
            </div>
          </div>
          <div className="mt-3 bg-dark-700 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-accent-primary h-full transition-all duration-300"
              style={{ width: `${(exportProgress.current / exportProgress.total) * 100}%` }}
            ></div>
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setPlatform('hepsiburada')}
          className={`px-4 py-2 rounded-lg transition-all ${
            platform === 'hepsiburada'
              ? 'bg-accent-primary text-dark-900 font-medium'
              : 'bg-dark-700 text-neutral-400 hover:bg-dark-600'
          }`}
        >
          Hepsiburada
        </button>
        <button
          onClick={() => setPlatform('trendyol')}
          className={`px-4 py-2 rounded-lg transition-all ${
            platform === 'trendyol'
              ? 'bg-accent-primary text-dark-900 font-medium'
              : 'bg-dark-700 text-neutral-400 hover:bg-dark-600'
          }`}
        >
          Trendyol
        </button>
      </div>

      <div className="card-dark p-4">
        <div className="flex items-center gap-4 mb-4">
          <input
            type="text"
            placeholder="Search seller name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-dark flex-1"
          />
          <div className="text-neutral-400 text-sm">
            {filteredSellers.length} sellers
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary"></div>
            <span className="ml-3 text-neutral-400">Loading sellers...</span>
          </div>
        ) : filteredSellers.length === 0 ? (
          <div className="text-center py-12 text-neutral-400">
            No sellers found
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSellers.map((seller) => (
              <div
                key={seller.merchant_id}
                onClick={() => navigate(`/sellers/${seller.merchant_id}?platform=${platform}`)}
                className={`p-4 rounded-lg cursor-pointer transition-all hover:bg-[#555555] ${getCardBackground(seller)}`}
              >
                <div className="flex items-start gap-3">
                  {seller.merchant_logo && (
                    <img
                      src={seller.merchant_logo}
                      alt={seller.merchant_name}
                      className="w-12 h-12 rounded-lg object-contain bg-white p-1"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-white truncate">{seller.merchant_name}</h3>
                    {seller.merchant_rating && (
                      <div className="flex items-center gap-1 mt-1">
                        <span className="text-warning text-sm">★</span>
                        <span className="text-neutral-300 text-sm">{formatRating(seller.merchant_rating)}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between mt-4 pt-3 border-t border-dark-600">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white">{seller.product_count}</div>
                    <div className="text-xs text-neutral-400">Products</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-2xl font-bold ${seller.price_alert_count > 0 ? 'text-danger' : 'text-neutral-500'}`}>
                      {seller.price_alert_count}
                    </div>
                    <div className="text-xs text-neutral-400">Price</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-2xl font-bold ${seller.campaign_alert_count > 0 ? 'text-warning' : 'text-neutral-500'}`}>
                      {seller.campaign_alert_count}
                    </div>
                    <div className="text-xs text-neutral-400">Campaign</div>
                  </div>
                </div>

                {(seller.price_alert_count > 0 || seller.campaign_alert_count > 0) && (
                  <div className="mt-3 flex items-center justify-center gap-2 flex-wrap">
                    {seller.price_alert_count > 0 && (
                      <span className="badge badge-danger text-xs">
                        {seller.price_alert_count} Price
                      </span>
                    )}
                    {seller.campaign_alert_count > 0 && (
                      <span className="badge badge-warning text-xs">
                        {seller.campaign_alert_count} Campaign
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
