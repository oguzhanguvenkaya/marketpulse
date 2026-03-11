import type { UseMyStoreReturn } from '../../hooks/useMyStore';

const PLATFORM_BADGE: Record<string, { label: string; bg: string; text: string }> = {
  web: { label: 'WEB', bg: 'bg-blue-500/15', text: 'text-blue-400' },
  hepsiburada: { label: 'HB', bg: 'bg-[#ff6000]/15', text: 'text-[#ff6000]' },
  trendyol: { label: 'TY', bg: 'bg-[#f27a1a]/15', text: 'text-[#f27a1a]' },
};

export default function MyStoreProductList(props: UseMyStoreReturn) {
  const {
    products, loading, selectedProduct, handleProductClick,
    searchInput, setSearchInput, brands, selectedBrand, setSelectedBrand,
    totalProducts, currentOffset, PAGE_SIZE, handlePrevPage, handleNextPage,
    formatPrice, handleDeleteProduct,
  } = props;

  return (
    <div className="card-dark rounded-xl p-4 md:p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
          <h2 className="text-lg font-semibold text-text-primary">Ürünlerim</h2>
        </div>
        <span className="text-xs text-text-muted">{totalProducts} ürün</span>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <input
          type="text"
          placeholder="Ara: isim, barkod, SKU..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="input-dark flex-1 px-3 py-2 rounded-lg text-sm"
        />
        <select
          value={selectedBrand}
          onChange={(e) => setSelectedBrand(e.target.value)}
          className="input-dark px-3 py-2 rounded-lg text-sm min-w-[140px]"
        >
          <option value="">Tüm Markalar</option>
          {brands.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
      </div>

      {/* Product List */}
      <div className="max-h-[600px] overflow-y-auto pr-1 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-12 text-text-muted text-sm">
            {totalProducts === 0 ? 'Henüz ürün yok. CSV import edin.' : 'Aramanızla eşleşen ürün bulunamadı.'}
          </div>
        ) : (
          products.map((product) => {
            const isSelected = selectedProduct?.id === product.id;
            return (
              <button
                key={product.id}
                onClick={() => handleProductClick(product)}
                className={`w-full text-left p-3 rounded-lg border transition-all ${
                  isSelected
                    ? 'border-accent-primary/50 bg-accent-primary/5'
                    : 'border-border-primary hover:border-border-secondary hover:bg-surface-hover/30'
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Image */}
                  {product.image_url ? (
                    <img
                      src={product.image_url}
                      alt=""
                      className="w-12 h-12 rounded-lg object-cover bg-white flex-shrink-0"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-lg bg-surface-hover flex items-center justify-center flex-shrink-0">
                      <svg className="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                  )}

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    {/* Platform badges */}
                    <div className="flex items-center gap-1 mb-1">
                      {['web', 'hepsiburada', 'trendyol'].map((p) => {
                        const badge = PLATFORM_BADGE[p];
                        const exists = product.platforms.includes(p);
                        return (
                          <span
                            key={p}
                            className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                              exists ? `${badge.bg} ${badge.text}` : 'bg-surface-hover/50 text-text-muted/40'
                            }`}
                          >
                            {badge.label}
                          </span>
                        );
                      })}
                      {product.brand && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-hover text-text-muted ml-1">
                          {product.brand}
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <p className="text-sm font-medium text-text-primary truncate">{product.title}</p>

                    {/* Meta */}
                    <div className="flex items-center gap-3 mt-1 text-xs text-text-muted">
                      {product.barcode && <span>Barkod: {product.barcode}</span>}
                      {product.hepsiburada_sku && <span>HB: {product.hepsiburada_sku}</span>}
                    </div>
                  </div>

                  {/* Right: Price + Delete */}
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className="text-sm font-bold text-text-primary">
                      {formatPrice(product.price)}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteProduct(product.id); }}
                      className="text-[11px] text-danger hover:underline"
                    >
                      Sil
                    </button>
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>

      {/* Pagination */}
      {totalProducts > PAGE_SIZE && (
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-border-primary">
          <span className="text-xs text-text-muted">
            {currentOffset + 1}–{Math.min(currentOffset + PAGE_SIZE, totalProducts)} / {totalProducts}
          </span>
          <div className="flex gap-2">
            <button onClick={handlePrevPage} disabled={currentOffset === 0}
              className="px-3 py-1 text-xs rounded-lg bg-surface-hover disabled:opacity-30">Önceki</button>
            <button onClick={handleNextPage} disabled={currentOffset + PAGE_SIZE >= totalProducts}
              className="px-3 py-1 text-xs rounded-lg bg-surface-hover disabled:opacity-30">Sonraki</button>
          </div>
        </div>
      )}
    </div>
  );
}
