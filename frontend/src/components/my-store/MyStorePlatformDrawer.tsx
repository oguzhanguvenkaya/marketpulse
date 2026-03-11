import { createPortal } from 'react-dom';
import type { UseMyStoreReturn } from '../../hooks/useMyStore';
import type { SellerSnapshot } from '../../services/types';

function SellerCard({ seller, formatPrice }: { seller: SellerSnapshot; formatPrice: (p?: number | null) => string }) {
  const isBuybox = seller.buybox_order === 1 || seller.buybox_order === 0;
  return (
    <div className={`rounded-lg border p-3 text-sm ${isBuybox ? 'border-success/40 bg-success/5' : 'border-border-primary'}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 min-w-0">
          {seller.merchant_logo && (
            <img src={seller.merchant_logo} alt="" className="w-6 h-6 rounded object-contain bg-white" />
          )}
          <div className="min-w-0">
            <span className="font-medium text-text-primary text-xs block truncate">{seller.merchant_name}</span>
            <div className="flex items-center gap-2 mt-0.5">
              {isBuybox && <span className="text-[9px] px-1 py-0.5 rounded bg-success/15 text-success font-bold">Buybox</span>}
              {seller.merchant_rating && (
                <span className="text-[10px] text-warning">{seller.merchant_rating.toFixed(1)} ★</span>
              )}
              {seller.merchant_city && <span className="text-[10px] text-text-muted">{seller.merchant_city}</span>}
            </div>
          </div>
        </div>
        <div className="text-right flex-shrink-0 ml-2">
          <span className="font-bold text-text-primary">{formatPrice(seller.price)}</span>
          {seller.campaign_price && (
            <span className="block text-[10px] text-success font-medium">{formatPrice(seller.campaign_price)} kampanya</span>
          )}
          {seller.original_price && seller.original_price !== seller.price && (
            <span className="block text-[10px] text-text-muted line-through">{formatPrice(seller.original_price)}</span>
          )}
        </div>
      </div>
      {/* Badges */}
      <div className="flex flex-wrap gap-1 mt-2">
        {seller.free_shipping && <span className="text-[9px] px-1.5 py-0.5 rounded bg-success/10 text-success">Ücretsiz Kargo</span>}
        {seller.fast_shipping && <span className="text-[9px] px-1.5 py-0.5 rounded bg-warning/10 text-warning">Hızlı</span>}
        {seller.is_fulfilled_by_hb && <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#ff6000]/10 text-[#ff6000]">HB Lojistik</span>}
        {seller.stock_quantity != null && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-hover text-text-muted">Stok: {seller.stock_quantity}</span>
        )}
        {seller.campaigns?.map((c, i) => (
          <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-accent-primary/10 text-accent-primary">{c}</span>
        ))}
      </div>
    </div>
  );
}

export default function MyStorePlatformDrawer(props: UseMyStoreReturn) {
  const { selectedPlatformCard, handleClosePlatformDrawer, productDetail, selectedProduct, formatPrice } = props;

  if (!selectedPlatformCard || !productDetail) return null;

  const platformLabel: Record<string, string> = { web: 'Web Sitesi', hepsiburada: 'Hepsiburada', trendyol: 'Trendyol' };
  const platformColor: Record<string, string> = { web: 'text-blue-400', hepsiburada: 'text-[#ff6000]', trendyol: 'text-[#f27a1a]' };

  const renderWebDetail = () => {
    const web = productDetail.web;
    if (!web) return <p className="text-sm text-text-muted">Web verisi bulunamadı</p>;

    const images = web.image_list?.length ? web.image_list : [web.image_url, web.image_url_2].filter(Boolean) as string[];

    return (
      <div className="space-y-4">
        {/* Images */}
        {images.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-2">
            {images.map((url, i) => (
              <img key={i} src={url} alt="" className="w-24 h-24 rounded-lg object-cover bg-white flex-shrink-0" />
            ))}
          </div>
        )}

        {/* Brand & Title */}
        {web.brand && <p className="text-xs font-bold text-accent-primary uppercase">{web.brand}</p>}
        <p className="text-sm font-medium text-text-primary leading-snug">{web.title}</p>
        {web.subtitle && <p className="text-xs text-text-muted">{web.subtitle}</p>}

        {/* Info Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="p-2 rounded-lg bg-surface-hover/50">
            <span className="text-text-muted block">Fiyat</span>
            <span className="font-bold text-lg text-text-primary">{formatPrice(web.price)}</span>
          </div>
          <div className="p-2 rounded-lg bg-surface-hover/50">
            <span className="text-text-muted block">Görseller</span>
            <span className="font-semibold text-text-primary">{images.length}</span>
          </div>
        </div>

        {/* Details */}
        <div className="space-y-2 text-xs">
          {web.barcode && <div className="flex justify-between"><span className="text-text-muted">Barkod</span><span className="font-mono text-text-body">{web.barcode}</span></div>}
          {web.stock_code && <div className="flex justify-between"><span className="text-text-muted">Stok Kodu</span><span className="font-mono text-text-body">{web.stock_code}</span></div>}
          {web.supplier && <div className="flex justify-between"><span className="text-text-muted">Tedarikçi</span><span className="text-text-body">{web.supplier}</span></div>}
          {web.category_path && (
            <div>
              <span className="text-text-muted block mb-1">Kategori</span>
              <span className="text-text-body">{web.category_path}</span>
            </div>
          )}
          {web.meta_title && (
            <div>
              <span className="text-text-muted block mb-1">Meta Title</span>
              <span className="text-text-body">{web.meta_title}</span>
            </div>
          )}
          {web.meta_description && (
            <div>
              <span className="text-text-muted block mb-1">Meta Description</span>
              <span className="text-text-body">{web.meta_description}</span>
            </div>
          )}
          {web.web_url && (
            <a href={web.web_url} target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline block mt-2">
              Web sayfasında görüntüle →
            </a>
          )}
        </div>

        {/* Description */}
        {web.detail_html && (
          <div>
            <span className="text-xs text-text-muted block mb-1">Açıklama</span>
            <div
              className="text-xs text-text-body max-h-48 overflow-y-auto rounded-lg bg-surface-hover/30 p-3 prose prose-sm prose-invert"
              dangerouslySetInnerHTML={{ __html: web.detail_html }}
            />
          </div>
        )}
      </div>
    );
  };

  const renderMarketplaceDetail = (platform: 'hepsiburada' | 'trendyol') => {
    const data = productDetail[platform];
    if (!data) return <p className="text-sm text-text-muted">{platformLabel[platform]} verisi bulunamadı</p>;

    const { product, sellers } = data;

    return (
      <div className="space-y-4">
        {/* Product Info */}
        {product.image_url && (
          <img src={product.image_url} alt="" className="w-full max-h-48 object-contain rounded-lg bg-white" />
        )}
        {product.brand && <p className="text-xs font-bold text-accent-primary uppercase">{product.brand}</p>}
        <p className="text-sm font-medium text-text-primary leading-snug">{product.product_name || selectedProduct?.title}</p>

        {/* Info Grid */}
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="p-2 rounded-lg bg-surface-hover/50 text-center">
            <span className="text-text-muted block">Fiyat</span>
            <span className="font-bold text-base text-text-primary">
              {sellers[0] ? formatPrice(sellers[0].price) : formatPrice(product.threshold_price)}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-surface-hover/50 text-center">
            <span className="text-text-muted block">Satıcı</span>
            <span className="font-semibold text-text-primary">{sellers.length}</span>
          </div>
          <div className="p-2 rounded-lg bg-surface-hover/50 text-center">
            <span className="text-text-muted block">Durum</span>
            <span className={`font-semibold ${product.is_active ? 'text-success' : 'text-danger'}`}>
              {product.is_active ? 'Aktif' : 'Pasif'}
            </span>
          </div>
        </div>

        {/* Details */}
        <div className="space-y-1.5 text-xs">
          <div className="flex justify-between"><span className="text-text-muted">SKU</span><span className="font-mono text-text-body">{product.sku}</span></div>
          {product.barcode && <div className="flex justify-between"><span className="text-text-muted">Barkod</span><span className="font-mono text-text-body">{product.barcode}</span></div>}
          {product.last_fetched_at && (
            <div className="flex justify-between">
              <span className="text-text-muted">Son Güncelleme</span>
              <span className="text-text-body">
                {new Date(product.last_fetched_at).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          )}
          {product.product_url && (
            <a href={product.product_url} target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline block mt-2">
              {platformLabel[platform]}'da görüntüle →
            </a>
          )}
        </div>

        {/* Sellers */}
        {sellers.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-text-primary mb-2">Satıcılar ({sellers.length})</h4>
            <div className="space-y-2">
              {sellers.map((s, i) => <SellerCard key={`${s.merchant_id}-${i}`} seller={s} formatPrice={formatPrice} />)}
            </div>
          </div>
        )}
      </div>
    );
  };

  return createPortal(
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-[9998]" onClick={handleClosePlatformDrawer} />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-full max-w-lg z-[9999] bg-surface-primary border-l border-border-primary shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border-primary flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className={`font-bold ${platformColor[selectedPlatformCard]}`}>{platformLabel[selectedPlatformCard]}</span>
            <span className="text-xs text-text-muted">Detay</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleClosePlatformDrawer} className="p-1 hover:bg-surface-hover rounded-lg">
              <svg className="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {selectedPlatformCard === 'web'
            ? renderWebDetail()
            : renderMarketplaceDetail(selectedPlatformCard)
          }
        </div>
      </div>
    </>,
    document.body,
  );
}
