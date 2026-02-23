import type { StoreProduct, CategoryProductItem } from '../../services/api';
import type { UseCategoryExplorerReturn } from '../../hooks/useCategoryExplorer';

function StoreProductCard({
  product,
  formatPrice,
  setSelectedProduct,
  setSelectedCatProduct,
}: {
  product: StoreProduct;
  formatPrice: (p: number | null | undefined) => string;
  setSelectedProduct: (p: StoreProduct | null) => void;
  setSelectedCatProduct: (p: CategoryProductItem | null) => void;
}) {
  return (
    <div
      key={product.id}
      className="rounded-xl border border-[#5b4824]/12 overflow-hidden hover:border-[#5b4824]/15 transition-all cursor-pointer group"
      style={{ background: 'linear-gradient(180deg, #fefbf0 0%, #fffbef 100%)' }}
      onClick={() => { setSelectedProduct(product); setSelectedCatProduct(null); }}
    >
      <div className="flex gap-3 p-3">
        <div className="w-20 h-20 rounded-lg bg-[#5b4824]/5 flex items-center justify-center flex-shrink-0 overflow-hidden">
          {product.image_url ? (
            <img src={product.image_url} alt="" className="max-h-full max-w-full object-contain" loading="lazy" />
          ) : (
            <svg className="w-8 h-8 text-[#b5a382]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
              product.platform === 'hepsiburada' ? 'bg-orange-500/20 text-orange-400' :
              product.platform === 'trendyol' ? 'bg-[#9e8b66]/15 text-[#9e8b66]' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              {product.platform === 'hepsiburada' ? 'HB' : product.platform === 'trendyol' ? 'TY' : 'WEB'}
            </span>
            {product.brand && <span className="text-[10px] text-[#5b4824] font-medium uppercase truncate">{product.brand}</span>}
          </div>
          <h3 className="text-sm text-[#3d3427] line-clamp-2 leading-snug mb-1.5">{product.product_name || 'Unnamed'}</h3>
          <div className="flex items-end justify-between">
            <span className="text-base font-bold text-[#0f1419]">{formatPrice(product.price)}</span>
            {product.rating && (
              <div className="flex items-center gap-0.5">
                <svg className="w-3 h-3 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
                <span className="text-xs text-[#9e8b66]">{product.rating}</span>
                {product.review_count != null && <span className="text-[10px] text-[#b5a382]">({product.review_count})</span>}
              </div>
            )}
          </div>
        </div>
      </div>
      {product.category && (
        <div className="px-3 pb-2.5">
          <p className="text-[10px] text-[#b5a382] truncate">{product.category}</p>
        </div>
      )}
    </div>
  );
}

function CatProductCard({
  product,
  selectedForDetail,
  toggleProductSelection,
  handleDeleteProduct,
  setSelectedCatProduct,
  setSelectedProduct,
  formatPrice,
}: {
  product: CategoryProductItem;
  selectedForDetail: Set<number>;
  toggleProductSelection: (id: number) => void;
  handleDeleteProduct: (id: number) => void;
  setSelectedCatProduct: (p: CategoryProductItem | null) => void;
  setSelectedProduct: (p: StoreProduct | null) => void;
  formatPrice: (p: number | null | undefined) => string;
}) {
  const isSelected = selectedForDetail.has(product.id);
  return (
    <div
      key={product.id}
      className={`rounded-xl border overflow-hidden transition-all cursor-pointer group relative ${
        isSelected ? 'border-[#5b4824]/25 ring-1 ring-[#5b4824]/15' : 'border-[#5b4824]/12 hover:border-[#5b4824]/15'
      }`}
      style={{ background: 'linear-gradient(180deg, #fefbf0 0%, #fffbef 100%)' }}
    >
      <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
        <button
          onClick={(e) => { e.stopPropagation(); toggleProductSelection(product.id); }}
          className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
            isSelected ? 'bg-[#5b4824] border-[#5b4824] text-[#0f1419]' : 'border-[#5b4824]/15 hover:border-[#5b4824]/30'
          }`}
        >
          {isSelected && (
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
          )}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); handleDeleteProduct(product.id); }}
          className="w-5 h-5 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:bg-red-500/20"
          title="Delete product"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
        </button>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#5b4824]/8 text-[#9e8b66] font-mono">
          #{product.position}
        </span>
        {product.is_sponsored && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium">
            AD
          </span>
        )}
        {product.detail_fetched && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-600 font-medium">
            Detailed
          </span>
        )}
      </div>
      <div
        className="flex gap-3 p-3"
        onClick={() => { setSelectedCatProduct(product); setSelectedProduct(null); }}
      >
        <div className="w-20 h-20 rounded-lg bg-[#5b4824]/5 flex items-center justify-center flex-shrink-0 overflow-hidden">
          {product.image_url ? (
            <img src={product.image_url} alt="" className="max-h-full max-w-full object-contain" loading="lazy" />
          ) : (
            <svg className="w-8 h-8 text-[#b5a382]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            {product.brand && <span className="text-[10px] text-[#5b4824] font-medium uppercase truncate">{product.brand}</span>}
          </div>
          <h3 className="text-sm text-[#3d3427] line-clamp-2 leading-snug mb-1.5">{product.name || 'Unnamed'}</h3>
          <div className="flex items-end justify-between">
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-[#0f1419]">{formatPrice(product.price)}</span>
              {product.original_price && product.original_price > (product.price || 0) && (
                <span className="text-xs text-neutral-500 line-through">{formatPrice(product.original_price)}</span>
              )}
            </div>
            {product.rating && (
              <div className="flex items-center gap-0.5">
                <svg className="w-3 h-3 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
                <span className="text-xs text-[#9e8b66]">{product.rating}</span>
                {product.review_count != null && <span className="text-[10px] text-[#b5a382]">({product.review_count})</span>}
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="px-3 pb-2.5 flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] text-[#b5a382]">Page {product.page_number}</span>
          {product.seller_name && <span className="text-[10px] text-[#b5a382] truncate">| {product.seller_name}</span>}
          {product.sku && <span className="text-[10px] text-[#b5a382] font-mono truncate">SKU: {product.sku}</span>}
        </div>
        {product.campaign_text && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-600 truncate max-w-[120px]">{product.campaign_text}</span>
        )}
      </div>
    </div>
  );
}

export default function ProductCards(ce: UseCategoryExplorerReturn) {
  const {
    viewMode,
    loading,
    currentProducts,
    currentCatProducts,
    currentTotal,
    currentTotalPages,
    page,
    setPage,
    selectedCategory,
    selectedBrand,
    search,
    selectedForDetail,
    catData,
    selectAllProducts,
    handleBulkDelete,
    formatPrice,
    setSelectedProduct,
    setSelectedCatProduct,
    toggleProductSelection,
    handleDeleteProduct,
  } = ce;

  const Pagination = () => {
    if (currentTotalPages <= 1) return null;
    return (
      <div className="flex items-center justify-center gap-2 pt-4">
        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
          className="px-3 py-2 text-sm rounded-lg border border-[#5b4824]/12 text-[#5f471d] hover:bg-[#5b4824]/5 disabled:opacity-30">Previous</button>
        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(5, currentTotalPages) }, (_, i) => {
            let p: number;
            if (currentTotalPages <= 5) p = i + 1;
            else if (page <= 3) p = i + 1;
            else if (page >= currentTotalPages - 2) p = currentTotalPages - 4 + i;
            else p = page - 2 + i;
            return (
              <button key={p} onClick={() => setPage(p)}
                className={`w-9 h-9 text-sm rounded-lg ${p === page ? 'bg-[#5b4824]/10 text-[#5b4824] border border-[#5b4824]/20' : 'text-[#9e8b66] hover:bg-[#5b4824]/5'}`}
              >{p}</button>
            );
          })}
        </div>
        <button onClick={() => setPage(p => Math.min(currentTotalPages, p + 1))} disabled={page >= currentTotalPages}
          className="px-3 py-2 text-sm rounded-lg border border-[#5b4824]/12 text-[#5f471d] hover:bg-[#5b4824]/5 disabled:opacity-30">Next</button>
        <span className="text-xs text-[#b5a382] ml-2">{currentTotal.toLocaleString()} products</span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-[#5b4824] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (viewMode === 'my_products') {
    if (currentProducts.length > 0) {
      return (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {currentProducts.map(product => (
              <StoreProductCard
                key={product.id}
                product={product}
                formatPrice={formatPrice}
                setSelectedProduct={setSelectedProduct}
                setSelectedCatProduct={setSelectedCatProduct}
              />
            ))}
          </div>
          <Pagination />
        </>
      );
    }
    return <EmptyState viewMode={viewMode} hasFilters={!!(selectedCategory || selectedBrand || search)} />;
  }

  // category_page view
  if (currentCatProducts.length > 0) {
    return (
      <>
        <div className="flex items-center justify-between mb-3 px-1">
          <div className="flex items-center gap-3">
            <button
              onClick={selectAllProducts}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                selectedForDetail.size === (catData?.products?.length || 0) && selectedForDetail.size > 0
                  ? 'border-[#5b4824]/25 bg-[#5b4824]/8 text-[#5b4824]'
                  : 'border-[#5b4824]/12 text-[#5f471d] hover:bg-[#5b4824]/8'
              }`}
            >
              <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                selectedForDetail.size === (catData?.products?.length || 0) && selectedForDetail.size > 0
                  ? 'bg-[#5b4824] border-[#5b4824]'
                  : selectedForDetail.size > 0
                  ? 'bg-cyan-500/50 border-[#5b4824]/30'
                  : 'border-[#5b4824]/20'
              }`}>
                {selectedForDetail.size > 0 && (
                  <svg className="w-3 h-3 text-[#0f1419]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3}
                      d={selectedForDetail.size === (catData?.products?.length || 0) ? "M5 13l4 4L19 7" : "M20 12H4"} />
                  </svg>
                )}
              </div>
              {selectedForDetail.size === (catData?.products?.length || 0) && selectedForDetail.size > 0
                ? 'Deselect All'
                : `Select All (${catData?.total || 0})`}
            </button>
            {selectedForDetail.size > 0 && (
              <span className="text-xs text-[#5b4824]">
                {selectedForDetail.size} selected
              </span>
            )}
          </div>
          {selectedForDetail.size > 0 && (
            <button
              onClick={handleBulkDelete}
              className="flex items-center gap-2 px-4 py-1.5 text-xs rounded-lg bg-red-500/10 border border-red-500/30 text-red-600 hover:bg-red-500/20 transition-colors font-medium"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              Delete Selected ({selectedForDetail.size})
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {currentCatProducts.map(product => (
            <CatProductCard
              key={product.id}
              product={product}
              selectedForDetail={selectedForDetail}
              toggleProductSelection={toggleProductSelection}
              handleDeleteProduct={handleDeleteProduct}
              setSelectedCatProduct={setSelectedCatProduct}
              setSelectedProduct={setSelectedProduct}
              formatPrice={formatPrice}
            />
          ))}
        </div>
        <Pagination />
      </>
    );
  }

  return <EmptyState viewMode={viewMode} hasFilters={!!(selectedCategory || search)} />;
}

function EmptyState({ viewMode, hasFilters }: { viewMode: string; hasFilters: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[#5b4824]/5 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-[#b5a382]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-[#5f471d] mb-2">
        {viewMode === 'category_page' ? 'No Scraped Products' : 'No Products Found'}
      </h3>
      <p className="text-sm text-neutral-500 max-w-md">
        {viewMode === 'category_page'
          ? hasFilters
            ? 'No scraped products match this category. Use "Scrape New" to scrape a category page first.'
            : 'Use "Scrape New" to scrape a marketplace category page. Products will appear here in their marketplace order.'
          : hasFilters
            ? 'Try adjusting your filters or search to find products.'
            : 'Use the "Scrape New" button to import products from marketplace category pages.'}
      </p>
    </div>
  );
}
