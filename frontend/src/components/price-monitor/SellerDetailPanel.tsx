import type { UsePriceMonitorReturn } from '../../hooks/usePriceMonitor';

export default function SellerDetailPanel({
  selectedProduct,
  sellers,
  sellersLoading,
  formatPrice,
}: UsePriceMonitorReturn) {
  return (
    <div className="card-dark p-4 md:p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
          <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold text-[#0f1419]">
          {selectedProduct ? `Sellers - ${selectedProduct.product_name || selectedProduct.sku}` : 'Seller Details'}
        </h2>
      </div>

      {selectedProduct && (
        <div className="flex flex-wrap gap-2 mb-4">
          {selectedProduct.threshold_price && (
            <span className="badge badge-warning">
              Threshold: {selectedProduct.threshold_price.toLocaleString('tr-TR')} TL
            </span>
          )}
          {selectedProduct.seller_stock_code && (
            <span className="badge badge-neutral">
              Stock Code: {selectedProduct.seller_stock_code}
            </span>
          )}
          {selectedProduct.brand && (
            <span className="badge badge-info">
              Brand: {selectedProduct.brand}
            </span>
          )}
        </div>
      )}

      {!selectedProduct ? (
        <div className="text-center py-12">
          <div className="w-12 h-12 rounded-full bg-[#f0e8d8] flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
            </svg>
          </div>
          <p className="text-[#9e8b66]">Select a product to view sellers</p>
        </div>
      ) : sellersLoading ? (
        <div className="text-center py-12">
          <div className="w-8 h-8 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin mx-auto" />
          <p className="text-neutral-500 mt-3">Loading sellers...</p>
        </div>
      ) : sellers.length === 0 ? (
        <div className="text-center py-12">
          <div className="w-12 h-12 rounded-full bg-[#f0e8d8] flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
          </div>
          <p className="text-[#9e8b66]">No seller data yet</p>
          <p className="text-sm text-neutral-500 mt-1">Click "Refresh" to fetch prices</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
          {sellers.map((seller, idx) => {
            const lowestPrice = Math.min(...sellers.map(s => s.price));
            const isLowestPrice = seller.price === lowestPrice;
            return (
            <div
              key={`${seller.merchant_id}-${idx}`}
              className={`p-3 md:p-4 rounded-lg border transition-all cursor-pointer hover:bg-[#f0e8d8]/35 ${
                seller.price_alert
                  ? 'bg-danger/20 border-danger/35'
                  : seller.buybox_order === 1
                    ? 'bg-success/15 border-success/30'
                    : 'bg-[#f7eede]/45 border-[#5b4824]/12'
              }`}
            >
              <div className="flex items-start gap-3">
                {seller.merchant_logo && (
                  <img
                    src={seller.merchant_logo}
                    alt={seller.merchant_name}
                    className="w-9 h-9 md:w-10 md:h-10 rounded-lg object-contain bg-white border border-[#5b4824]/12"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
                    <div>
                      <div className="font-medium text-sm flex items-center gap-2 flex-wrap">
                        {seller.merchant_url ? (
                          <a
                            href={seller.merchant_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#0f1419] hover:text-accent-primary transition-colors font-semibold"
                          >
                            {seller.merchant_name}
                          </a>
                        ) : (
                          <span className="text-[#0f1419] font-semibold">{seller.merchant_name}</span>
                        )}
                        {seller.buybox_order === 1 && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-success/20 text-success">Buybox</span>
                        )}
                        {isLowestPrice && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-primary/20 text-accent-primary">Lowest Price</span>
                        )}
                        {seller.price_alert && (
                          <span className="badge badge-danger text-[10px]">Price Alert</span>
                        )}
                        {seller.campaign_alert && (
                          <span className="badge badge-warning text-[10px]">Campaign Alert</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-[#5f471d]">
                        {seller.merchant_rating && (
                          <span className="px-1.5 py-0.5 rounded bg-warning/20 text-warning font-medium">
                            {seller.merchant_rating.toFixed(1)}
                          </span>
                        )}
                        {seller.merchant_city && <span>{seller.merchant_city}</span>}
                        {seller.stock_quantity !== undefined && (
                          <span>Stock: {seller.stock_quantity}</span>
                        )}
                      </div>
                    </div>
                    <div className="text-left sm:text-right">
                      <div className="font-bold text-lg text-[#0f1419] flex items-center gap-2 justify-start sm:justify-end">
                        {formatPrice(seller.list_price || seller.price)}
                        {seller.campaign_price && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 border border-orange-500/30 animate-pulse">
                            Sepete Özel
                          </span>
                        )}
                      </div>
                      {seller.list_price && seller.price && seller.list_price !== seller.price && (
                        <div className="text-xs text-success font-medium">
                          Satış: {formatPrice(seller.price)}
                        </div>
                      )}
                      {seller.discount_rate && seller.discount_rate > 0 && (
                        <div className="text-xs text-success font-medium">
                          %{seller.discount_rate.toFixed(0)} off
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {seller.free_shipping && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-primary/10 text-accent-primary border border-accent-primary/20">
                        Free Shipping
                      </span>
                    )}
                    {seller.fast_shipping && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
                        Fast Delivery
                      </span>
                    )}
                    {seller.is_fulfilled_by_hb && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-warning/10 text-warning border border-warning/20">
                        HB Logistics
                      </span>
                    )}
                  </div>
                  {seller.campaigns && seller.campaigns.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {seller.campaigns.map((campaign, idx) => (
                        <span
                          key={idx}
                          className="text-[10px] px-2 py-0.5 rounded-full bg-warning/15 text-warning border border-warning/30"
                        >
                          {campaign}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
          })}
        </div>
      )}
    </div>
  );
}
