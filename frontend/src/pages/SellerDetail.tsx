import { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { getSellerProducts, exportSellerProducts } from '../services/api';
import type { SellerProduct } from '../services/api';

export default function SellerDetail() {
  const { merchantId } = useParams<{ merchantId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const platform = (searchParams.get('platform') || 'hepsiburada') as 'hepsiburada' | 'trendyol';
  
  const [products, setProducts] = useState<SellerProduct[]>([]);
  const [merchantName, setMerchantName] = useState('');
  const [loading, setLoading] = useState(true);
  const [priceAlertOnly, setPriceAlertOnly] = useState(false);
  const [campaignAlertOnly, setCampaignAlertOnly] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [priceAlertCount, setPriceAlertCount] = useState(0);
  const [campaignAlertCount, setCampaignAlertCount] = useState(0);

  useEffect(() => {
    if (merchantId) {
      fetchProducts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [merchantId, platform, priceAlertOnly, campaignAlertOnly]);

  const fetchProducts = async () => {
    if (!merchantId) return;
    setLoading(true);
    try {
      const data = await getSellerProducts(merchantId, platform, priceAlertOnly, campaignAlertOnly);
      setProducts(data.products);
      setMerchantName(data.merchant_name);
      setPriceAlertCount(data.price_alert_count);
      setCampaignAlertCount(data.campaign_alert_count);
    } catch (error) {
      console.error('Error fetching seller products:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (exportType: 'all' | 'price' | 'campaign') => {
    if (!merchantId) return;
    setExporting(true);
    setShowExportMenu(false);
    try {
      const priceOnly = exportType === 'price';
      const campaignOnly = exportType === 'campaign';
      await exportSellerProducts(merchantId, platform, priceOnly, campaignOnly);
    } catch (error) {
      console.error('Error exporting:', error);
    } finally {
      setExporting(false);
    }
  };

  const formatPrice = (price?: number) => {
    if (!price) return '-';
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY',
      minimumFractionDigits: 2
    }).format(price);
  };

  const filteredProducts = products.filter(product => {
    const searchLower = searchTerm.toLowerCase();
    return (
      (product.product_name?.toLowerCase().includes(searchLower)) ||
      (product.sku?.toLowerCase().includes(searchLower)) ||
      (product.barcode?.toLowerCase().includes(searchLower)) ||
      (product.brand?.toLowerCase().includes(searchLower))
    );
  });

  return (
    <div className="space-y-5 md:space-y-6">
      <div className="flex items-start gap-3 md:gap-4">
        <button
          onClick={() => navigate(`/sellers?platform=${platform}`)}
          className="p-2 rounded-lg bg-[#f7eede] dark:bg-[#162420] hover:bg-[#f0e8d8] dark:hover:bg-[#1C2E28] transition-colors shrink-0"
        >
          <svg className="w-5 h-5 text-[#9e8b66] dark:text-[#6B8F80]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="min-w-0">
          <h1 className="text-xl md:text-2xl font-bold text-[#0f1419] dark:text-[#F0FDF4] truncate">{merchantName || 'Seller'}</h1>
          <p className="text-sm md:text-base text-[#9e8b66] dark:text-[#6B8F80] mt-1">
            {products.length} products • {priceAlertCount} price alerts • {campaignAlertCount} campaign alerts
          </p>
        </div>
      </div>

      <div className="card-dark p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3 md:gap-4 mb-4">
          <input
            type="text"
            placeholder="Search by name, SKU, barcode, brand..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-dark w-full xl:col-span-2"
          />
          
          <button
            onClick={() => setPriceAlertOnly(!priceAlertOnly)}
            className={`px-3 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap ${
              priceAlertOnly
                ? 'bg-danger/20 text-danger border border-danger/30'
                : 'bg-[#f0e8d8] dark:bg-[#1C2E28] text-[#9e8b66] dark:text-[#6B8F80] hover:bg-[#e8dfcf] dark:hover:bg-[#1C2E28]'
            }`}
          >
            Price Alerts
            {priceAlertCount > 0 && (
              <span className="ml-2 px-1.5 py-0.5 text-xs rounded bg-danger/30">{priceAlertCount}</span>
            )}
          </button>

          <button
            onClick={() => setCampaignAlertOnly(!campaignAlertOnly)}
            className={`px-3 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap ${
              campaignAlertOnly
                ? 'bg-warning/20 text-warning border border-warning/30'
                : 'bg-[#f0e8d8] dark:bg-[#1C2E28] text-[#9e8b66] dark:text-[#6B8F80] hover:bg-[#e8dfcf] dark:hover:bg-[#1C2E28]'
            }`}
          >
            Campaign Alerts
            {campaignAlertCount > 0 && (
              <span className="ml-2 px-1.5 py-0.5 text-xs rounded bg-warning/30">{campaignAlertCount}</span>
            )}
          </button>

          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={exporting || filteredProducts.length === 0}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {exporting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-dark-900 dark:border-[#022c22]"></div>
                  Exporting...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Export CSV
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </>
              )}
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-48 max-w-[calc(100vw-2rem)] bg-[#f7eede] dark:bg-[#162420] rounded-lg shadow-lg border border-dark-500 dark:border-[#2A4039] z-10">
                <button
                  onClick={() => handleExport('all')}
                  className="w-full px-4 py-2 text-left text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#f0e8d8] dark:hover:bg-[#1C2E28] rounded-t-lg"
                >
                  Export All
                </button>
                <button
                  onClick={() => handleExport('price')}
                  disabled={priceAlertCount === 0}
                  className="w-full px-4 py-2 text-left text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#f0e8d8] dark:hover:bg-[#1C2E28] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <span className="w-2 h-2 bg-danger rounded-full"></span>
                  Price Alerts Only ({priceAlertCount})
                </button>
                <button
                  onClick={() => handleExport('campaign')}
                  disabled={campaignAlertCount === 0}
                  className="w-full px-4 py-2 text-left text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#f0e8d8] dark:hover:bg-[#1C2E28] rounded-b-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <span className="w-2 h-2 bg-warning rounded-full"></span>
                  Campaign Alerts Only ({campaignAlertCount})
                </button>
              </div>
            )}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary"></div>
            <span className="ml-3 text-[#9e8b66] dark:text-[#6B8F80]">Loading products...</span>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="text-center py-12 text-[#9e8b66] dark:text-[#6B8F80]">
            {priceAlertOnly || campaignAlertOnly ? 'No products with selected alerts' : 'No products found'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-dark w-full min-w-[980px]">
              <thead>
                <tr>
                  <th className="text-left" rowSpan={2}>Product</th>
                  <th className="text-left" rowSpan={2}>SKU / Barcode</th>
                  <th className="text-left" rowSpan={2}>Brand</th>
                  <th className="text-center border-l border-[#e5e0d2] dark:border-[#2A4039]" colSpan={3}>
                    <span className="text-danger">Price Alert</span>
                  </th>
                  <th className="text-center border-l border-[#e5e0d2] dark:border-[#2A4039]" colSpan={3}>
                    <span className="text-warning">Campaign Alert</span>
                  </th>
                </tr>
                <tr>
                  <th className="text-right border-l border-[#e5e0d2] dark:border-[#2A4039] text-xs font-normal text-neutral-500">Threshold</th>
                  <th className="text-right text-xs font-normal text-neutral-500">Seller Price</th>
                  <th className="text-center text-xs font-normal text-neutral-500">Status</th>
                  <th className="text-right border-l border-[#e5e0d2] dark:border-[#2A4039] text-xs font-normal text-neutral-500">Threshold</th>
                  <th className="text-right text-xs font-normal text-neutral-500">Campaign</th>
                  <th className="text-center text-xs font-normal text-neutral-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((product) => {
                  const resolvedProductUrl = product.seller_url || product.product_url || '';
                  const hasValidProductUrl = /^https?:\/\//i.test(resolvedProductUrl);
                  return (
                  <tr 
                    key={product.product_id}
                    className={`${product.price_alert || product.campaign_alert ? (product.price_alert ? 'bg-red-50 dark:bg-red-500/10' : 'bg-orange-50 dark:bg-orange-500/10') : ''} hover:bg-[#f7eede] dark:hover:bg-[#1C2E28] transition-colors`}
                  >
                    <td>
                      <div className="flex items-center gap-3">
                        {product.image_url && (
                          <img
                            src={product.image_url}
                            alt={product.product_name}
                            className="w-10 h-10 rounded object-cover bg-white dark:bg-[#162420]"
                          />
                        )}
                        <div className="max-w-[250px]">
                          <div className="text-[#0f1419] dark:text-[#F0FDF4] font-medium truncate" title={product.product_name}>
                            {product.product_name || 'Unnamed Product'}
                          </div>
                          {hasValidProductUrl && (
                            <a
                              href={resolvedProductUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-accent-primary hover:underline"
                            >
                              View on {platform === 'hepsiburada' ? 'HB' : 'Trendyol'}
                            </a>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="text-[#5f471d] dark:text-[#A7C4B8] text-sm">{product.sku || '-'}</div>
                      <div className="text-neutral-500 text-xs">{product.barcode || '-'}</div>
                    </td>
                    <td className="text-[#5f471d] dark:text-[#A7C4B8]">{product.brand || '-'}</td>
                    
                    {/* Price Alert columns */}
                    <td className="text-right text-[#9e8b66] dark:text-[#6B8F80] border-l border-[#e5e0d2] dark:border-[#2A4039]">
                      {formatPrice(product.threshold_price)}
                    </td>
                    <td className="text-right">
                      <span className={`font-semibold ${product.price_alert ? 'text-danger' : 'text-[#0f1419] dark:text-[#F0FDF4]'}`}>
                        {formatPrice(product.seller_price)}
                      </span>
                      {product.price_difference !== null && product.price_difference !== undefined && (
                        <div className={`text-xs ${product.price_difference > 0 ? 'text-danger' : 'text-success'}`}>
                          {product.price_difference > 0 ? '-' : '+'}{Math.abs(product.price_difference).toFixed(2)} TL
                        </div>
                      )}
                    </td>
                    <td className="text-center">
                      {product.price_alert ? (
                        <span className="badge badge-danger text-xs">Below</span>
                      ) : product.threshold_price ? (
                        <span className="badge badge-success text-xs">OK</span>
                      ) : (
                        <span className="text-neutral-500 text-xs">-</span>
                      )}
                    </td>
                    
                    {/* Campaign Alert columns */}
                    <td className="text-right text-[#9e8b66] dark:text-[#6B8F80] border-l border-[#e5e0d2] dark:border-[#2A4039]">
                      {formatPrice(product.alert_campaign_price)}
                    </td>
                    <td className="text-right">
                      {product.campaign_price ? (
                        <>
                          <span className={`font-semibold ${product.campaign_alert ? 'text-warning' : 'text-[#0f1419] dark:text-[#F0FDF4]'}`}>
                            {formatPrice(product.campaign_price)}
                          </span>
                          {product.campaign_difference !== null && product.campaign_difference !== undefined && (
                            <div className={`text-xs ${product.campaign_difference > 0 ? 'text-warning' : 'text-success'}`}>
                              {product.campaign_difference > 0 ? '-' : '+'}{Math.abs(product.campaign_difference).toFixed(2)} TL
                            </div>
                          )}
                        </>
                      ) : (
                        <span className="text-neutral-500">-</span>
                      )}
                    </td>
                    <td className="text-center">
                      {product.campaign_alert ? (
                        <span className="badge badge-warning text-xs">Below</span>
                      ) : product.alert_campaign_price && product.campaign_price ? (
                        <span className="badge badge-success text-xs">OK</span>
                      ) : (
                        <span className="text-neutral-500 text-xs">-</span>
                      )}
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
