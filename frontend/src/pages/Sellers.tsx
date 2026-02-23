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
  const [showBulkExportMenu, setShowBulkExportMenu] = useState(false);

  useEffect(() => {
    setSearchParams({ platform });
  }, [platform, setSearchParams]);

  useEffect(() => {
    fetchSellers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      return 'bg-gradient-to-br from-red-50 to-orange-50 border border-red-300/40';
    } else if (seller.price_alert_count > 0) {
      return 'bg-red-50 border border-red-300/40';
    } else if (seller.campaign_alert_count > 0) {
      return 'bg-orange-50 border border-orange-300/40';
    }
    return 'bg-[#f7eede] dark:bg-[#162420]';
  };

  const exportProgressPercent = exportProgress.total > 0
    ? Math.min(100, Math.round((exportProgress.current / exportProgress.total) * 100))
    : 0;

  const handleBulkExport = async (exportType: 'price' | 'campaign') => {
    setShowBulkExportMenu(false);
    
    const targetSellers = exportType === 'price' 
      ? filteredSellers.filter(s => s.price_alert_count > 0)
      : filteredSellers.filter(s => s.campaign_alert_count > 0);
    
    if (targetSellers.length === 0) return;

    setBulkExporting(true);
    setExportProgress({ current: 0, total: targetSellers.length, sellerName: '' });

    const priceAlertOnly = exportType === 'price';
    const campaignAlertOnly = exportType === 'campaign';

    for (let i = 0; i < targetSellers.length; i++) {
      const seller = targetSellers[i];
      setExportProgress({ current: i + 1, total: targetSellers.length, sellerName: seller.merchant_name });

      try {
        const response = await fetch(`${API_BASE}/sellers/${seller.merchant_id}/export?platform=${platform}&price_alert_only=${priceAlertOnly}&campaign_alert_only=${campaignAlertOnly}`);
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          const suffix = exportType === 'price' ? '_price_alerts' : '_campaign_alerts';
          a.download = `${seller.merchant_name.replace(/[^a-z0-9]/gi, '_')}${suffix}.csv`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
        }
      } catch (error) {
        console.error(`Error exporting ${seller.merchant_name}:`, error);
      }

      if (i < targetSellers.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }

    setBulkExporting(false);
    setExportProgress({ current: 0, total: 0, sellerName: '' });
  };

  return (
    <div className="space-y-5 md:space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-[#0f1419] dark:text-[#F0FDF4]">Sellers</h1>
          <p className="text-sm md:text-base text-[#9e8b66] dark:text-[#6B8F80] mt-1">View all sellers and their alert products</p>
        </div>
        {sellersWithAlerts.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowBulkExportMenu(!showBulkExportMenu)}
              disabled={bulkExporting}
              className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {bulkExporting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-dark-900 dark:border-[#022c22]"></div>
                  <span>Exporting {exportProgress.current}/{exportProgress.total}</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span>Bulk Export</span>
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </>
              )}
            </button>
            {showBulkExportMenu && (
              <div className="absolute right-0 mt-2 w-64 max-w-[calc(100vw-2rem)] bg-[#f7eede] dark:bg-[#162420] rounded-lg shadow-lg border border-dark-500 dark:border-[#2A4039] z-10">
                <button
                  onClick={() => handleBulkExport('price')}
                  disabled={filteredSellers.filter(s => s.price_alert_count > 0).length === 0}
                  className="w-full px-4 py-3 text-left text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#f0e8d8] dark:hover:bg-[#1C2E28] rounded-t-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <span className="w-2 h-2 bg-danger rounded-full"></span>
                  <span>Export Price Alerts</span>
                  <span className="ml-auto text-xs text-neutral-500">
                    ({filteredSellers.filter(s => s.price_alert_count > 0).length} sellers)
                  </span>
                </button>
                <button
                  onClick={() => handleBulkExport('campaign')}
                  disabled={filteredSellers.filter(s => s.campaign_alert_count > 0).length === 0}
                  className="w-full px-4 py-3 text-left text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#f0e8d8] dark:hover:bg-[#1C2E28] rounded-b-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <span className="w-2 h-2 bg-warning rounded-full"></span>
                  <span>Export Campaign Alerts</span>
                  <span className="ml-auto text-xs text-neutral-500">
                    ({filteredSellers.filter(s => s.campaign_alert_count > 0).length} sellers)
                  </span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {bulkExporting && (
        <div className="card-dark p-4 border border-accent-primary/30">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-accent-primary"></div>
            <div>
              <div className="text-[#0f1419] dark:text-[#F0FDF4] font-medium">Exporting: {exportProgress.sellerName}</div>
              <div className="text-[#9e8b66] dark:text-[#6B8F80] text-sm">{exportProgress.current} of {exportProgress.total} sellers</div>
            </div>
          </div>
          <div className="mt-3 bg-[#f7eede] dark:bg-[#162420] rounded-full h-2 overflow-hidden">
            <div 
              className="bg-accent-primary h-full transition-all duration-300"
              style={{ width: `${exportProgressPercent}%` }}
            ></div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-2">
        <button
          onClick={() => setPlatform('hepsiburada')}
          className={`px-4 py-2 rounded-lg transition-all ${
            platform === 'hepsiburada'
              ? 'bg-accent-primary text-dark-900 dark:text-[#022c22] font-medium'
              : 'bg-[#f7eede] dark:bg-[#162420] text-[#9e8b66] dark:text-[#A7C4B8] hover:bg-[#f0e8d8] dark:hover:bg-[#1C2E28]'
          }`}
        >
          Hepsiburada
        </button>
        <button
          onClick={() => setPlatform('trendyol')}
          className={`px-4 py-2 rounded-lg transition-all ${
            platform === 'trendyol'
              ? 'bg-accent-primary text-dark-900 dark:text-[#022c22] font-medium'
              : 'bg-[#f7eede] dark:bg-[#162420] text-[#9e8b66] dark:text-[#A7C4B8] hover:bg-[#f0e8d8] dark:hover:bg-[#1C2E28]'
          }`}
        >
          Trendyol
        </button>
      </div>

      <div className="card-dark p-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 mb-4">
          <input
            type="text"
            placeholder="Search seller name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-dark flex-1"
          />
          <div className="text-[#9e8b66] dark:text-[#6B8F80] text-xs md:text-sm">
            {filteredSellers.length} sellers
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary"></div>
            <span className="ml-3 text-[#9e8b66] dark:text-[#6B8F80]">Loading sellers...</span>
          </div>
        ) : filteredSellers.length === 0 ? (
          <div className="text-center py-12 text-[#9e8b66] dark:text-[#6B8F80]">
            No sellers found
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 md:gap-4">
            {filteredSellers.map((seller) => (
              <div
                key={seller.merchant_id}
                onClick={() => navigate(`/sellers/${seller.merchant_id}?platform=${platform}`)}
                className={`p-3 md:p-4 rounded-lg cursor-pointer transition-all hover:bg-[#f0e8d8]/45 dark:hover:bg-[#1C2E28]/45 ${getCardBackground(seller)}`}
              >
                <div className="flex items-start gap-3">
                  {seller.merchant_logo && (
                    <img
                      src={seller.merchant_logo}
                      alt={seller.merchant_name}
                    className="w-10 h-10 md:w-12 md:h-12 rounded-lg object-contain bg-white dark:bg-[#162420] p-1"
                  />
                )}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-[#0f1419] dark:text-[#F0FDF4] truncate">{seller.merchant_name}</h3>
                    {seller.merchant_rating && (
                      <div className="flex items-center gap-1 mt-1">
                        <span className="text-warning text-sm">★</span>
                        <span className="text-[#5f471d] dark:text-[#A7C4B8] text-sm">{formatRating(seller.merchant_rating)}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-[#e5e0d2] dark:border-[#2A4039]">
                  <div className="text-center">
                    <div className="text-xl md:text-2xl font-bold text-[#0f1419] dark:text-[#F0FDF4]">{seller.product_count}</div>
                    <div className="text-xs text-[#9e8b66] dark:text-[#6B8F80]">Products</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-xl md:text-2xl font-bold ${seller.price_alert_count > 0 ? 'text-danger' : 'text-neutral-500'}`}>
                      {seller.price_alert_count}
                    </div>
                    <div className="text-xs text-[#9e8b66] dark:text-[#6B8F80]">Price</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-xl md:text-2xl font-bold ${seller.campaign_alert_count > 0 ? 'text-warning' : 'text-neutral-500'}`}>
                      {seller.campaign_alert_count}
                    </div>
                    <div className="text-xs text-[#9e8b66] dark:text-[#6B8F80]">Campaign</div>
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
