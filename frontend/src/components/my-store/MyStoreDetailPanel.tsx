import type { UseMyStoreReturn } from '../../hooks/useMyStore';

const PLATFORMS = [
  { key: 'web' as const, label: 'Web Sitesi', color: 'border-blue-500/40', accent: 'text-blue-400', bg: 'bg-blue-500/5' },
  { key: 'hepsiburada' as const, label: 'Hepsiburada', color: 'border-[#ff6000]/40', accent: 'text-[#ff6000]', bg: 'bg-[#ff6000]/5' },
  { key: 'trendyol' as const, label: 'Trendyol', color: 'border-[#f27a1a]/40', accent: 'text-[#f27a1a]', bg: 'bg-[#f27a1a]/5' },
];

export default function MyStoreDetailPanel(props: UseMyStoreReturn) {
  const { selectedProduct, productDetail, detailLoading, handlePlatformCardClick, formatPrice } = props;

  if (!selectedProduct) {
    return (
      <div className="card-dark rounded-xl p-4 md:p-5 flex flex-col items-center justify-center min-h-[400px]">
        <svg className="w-12 h-12 text-text-muted/30 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <p className="text-sm text-text-muted">Detayları görmek için bir ürün seçin</p>
      </div>
    );
  }

  if (detailLoading) {
    return (
      <div className="card-dark rounded-xl p-4 md:p-5 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
      </div>
    );
  }

  return (
    <div className="card-dark rounded-xl p-4 md:p-5">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-text-primary mb-1">Platform Detayları</h2>
        <p className="text-sm text-text-muted truncate">{selectedProduct.title}</p>
      </div>

      {/* Platform Cards */}
      <div className="space-y-3 max-h-[550px] overflow-y-auto pr-1">
        {PLATFORMS.map(({ key, label, color, accent, bg }) => {
          const exists = selectedProduct.platforms.includes(key);
          const summary = selectedProduct.platform_summary[key];

          if (!exists) {
            return (
              <div key={key} className={`rounded-xl border-2 border-dashed border-border-primary/30 p-4 opacity-40`}>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold text-text-muted`}>{label}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-hover text-text-muted">Eşleşme yok</span>
                </div>
              </div>
            );
          }

          // Get platform-specific data
          let price: number | null = null;
          let sellerCount: number | null = null;
          let sku = '';
          let isActive = true;
          let lastFetched = '';
          let imageCount = 0;

          if (key === 'web' && summary && 'url' in summary) {
            price = summary.price ?? null;
            imageCount = summary.image_count ?? 0;
          } else if (key === 'hepsiburada' && productDetail?.hepsiburada) {
            const hb = productDetail.hepsiburada;
            price = hb.sellers?.[0]?.price ?? hb.product.threshold_price ?? null;
            sellerCount = hb.seller_count;
            sku = hb.product.sku;
            isActive = hb.product.is_active;
            lastFetched = hb.product.last_fetched_at || '';
          } else if (key === 'trendyol' && productDetail?.trendyol) {
            const ty = productDetail.trendyol;
            price = ty.sellers?.[0]?.price ?? ty.product.threshold_price ?? null;
            sellerCount = ty.seller_count;
            sku = ty.product.sku;
            isActive = ty.product.is_active;
            lastFetched = ty.product.last_fetched_at || '';
          }

          return (
            <button
              key={key}
              onClick={() => handlePlatformCardClick(key)}
              className={`w-full text-left rounded-xl border-2 ${color} ${bg} p-4 hover:shadow-md transition-all cursor-pointer`}
            >
              {/* Card Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-bold ${accent}`}>{label}</span>
                  {!isActive && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-danger/15 text-danger font-medium">Inactive</span>
                  )}
                </div>
                <svg className="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>

              {/* Card Body — Grid of Info */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-text-muted block">Fiyat</span>
                  <span className="font-bold text-text-primary text-base">{formatPrice(price)}</span>
                </div>
                {sellerCount !== null && (
                  <div>
                    <span className="text-text-muted block">Satıcı</span>
                    <span className="font-semibold text-text-primary">{sellerCount}</span>
                  </div>
                )}
                {key === 'web' && (
                  <div>
                    <span className="text-text-muted block">Görsel</span>
                    <span className="font-semibold text-text-primary">{imageCount}</span>
                  </div>
                )}
                {sku && (
                  <div>
                    <span className="text-text-muted block">SKU</span>
                    <span className="font-mono text-text-body text-[11px]">{sku}</span>
                  </div>
                )}
                {lastFetched && (
                  <div className="col-span-2">
                    <span className="text-text-muted block">Son Güncelleme</span>
                    <span className="text-text-body">
                      {new Date(lastFetched).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
