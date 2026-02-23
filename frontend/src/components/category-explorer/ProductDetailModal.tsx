import { createPortal } from 'react-dom';
import type { StoreProduct, CategoryProductItem } from '../../services/api';
import type { UseCategoryExplorerReturn } from '../../hooks/useCategoryExplorer';
import CategoryFilters from './CategoryFilters';

function ProductDetailPanel({ product, onClose, formatPrice, selectCategory }: {
  product: StoreProduct;
  onClose: () => void;
  formatPrice: (p: number | null | undefined) => string;
  selectCategory: (cat: string) => void;
}) {
  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-[9998]" onClick={onClose} />
      <div className="fixed top-0 right-0 h-full w-full max-w-lg z-[9999] overflow-y-auto border-l border-[#5b4824]/12 dark:border-[#4ADE80]/12 shadow-2xl bg-gradient-to-b from-[#fefbf0] to-[#fffbef] dark:from-[#162420] dark:to-[#0F1A17]">
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-[#5b4824]/12 dark:border-[#4ADE80]/12 bg-[#fefbf0]/98 dark:bg-[#162420]/98 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              product.platform === 'hepsiburada' ? 'bg-orange-500/20 text-orange-400' :
              product.platform === 'trendyol' ? 'bg-[#9e8b66]/15 text-[#9e8b66] dark:text-[#6B8F80]' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              {product.platform === 'hepsiburada' ? 'HB' : product.platform === 'trendyol' ? 'TY' : 'WEB'}
            </span>
            <h3 className="text-base font-semibold text-[#0f1419] dark:text-[#F0FDF4] truncate">Product Details</h3>
          </div>
          <div className="flex items-center gap-2">
            <a href={product.source_url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-[#5b4824]/8 dark:hover:bg-[#4ADE80]/8 text-[#9e8b66] dark:text-[#6B8F80]">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </a>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#5b4824]/8 dark:hover:bg-[#4ADE80]/8 text-[#9e8b66] dark:text-[#6B8F80]">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {product.image_url && (
            <div className="rounded-lg bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 p-4 flex items-center justify-center">
              <img src={product.image_url} alt="" className="max-h-64 object-contain" />
            </div>
          )}
          <div>
            {product.brand && <div className="text-xs text-[#5b4824] dark:text-[#4ADE80] font-medium uppercase mb-1">{product.brand}</div>}
            <h4 className="text-base font-medium text-[#0f1419] dark:text-[#F0FDF4] leading-snug">{product.product_name}</h4>
          </div>
          {product.category && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">Category</div>
              <div className="flex items-center gap-1 flex-wrap">
                {product.category.split(' > ').map((part, i, arr) => (
                  <span key={i} className="flex items-center gap-1">
                    {i > 0 && <svg className="w-2.5 h-2.5 text-[#b5a382] dark:text-[#6B8F80]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>}
                    <button onClick={() => selectCategory(arr.slice(0, i + 1).join(' > '))} className="text-xs text-[#9e8b66] dark:text-[#6B8F80] hover:text-[#5b4824] dark:hover:text-[#4ADE80] transition-colors">{part.trim()}</button>
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 p-3">
              <div className="text-xs text-neutral-500 mb-1">Price</div>
              <div className="text-lg font-bold text-[#0f1419] dark:text-[#F0FDF4]">{formatPrice(product.price)}</div>
            </div>
            <div className="rounded-lg bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 p-3">
              <div className="text-xs text-neutral-500 mb-1">Rating</div>
              <div className="text-lg font-bold text-[#0f1419] dark:text-[#F0FDF4] flex items-center gap-1">
                {product.rating || '-'}
                {product.rating && <svg className="w-4 h-4 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>}
              </div>
              <div className="text-xs text-neutral-500">{product.review_count ?? 0} reviews</div>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            {product.sku && <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8"><span className="text-neutral-500">SKU</span><span className="text-[#0f1419] dark:text-[#F0FDF4] font-mono text-xs">{product.sku}</span></div>}
            {product.barcode && <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8"><span className="text-neutral-500">Barcode</span><span className="text-[#0f1419] dark:text-[#F0FDF4] font-mono text-xs">{product.barcode}</span></div>}
            {product.seller_name && <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8"><span className="text-neutral-500">Seller</span><span className="text-[#0f1419] dark:text-[#F0FDF4]">{product.seller_name}</span></div>}
            {product.availability && <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8"><span className="text-neutral-500">Availability</span><span className={product.availability.toLowerCase().includes('instock') || product.availability.toLowerCase().includes('in stock') ? 'text-emerald-600' : 'text-red-600'}>{product.availability}</span></div>}
            {product.shipping_info && <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8"><span className="text-neutral-500">Shipping</span><span className="text-[#0f1419] dark:text-[#F0FDF4]">{product.shipping_info.cost} {product.shipping_info.currency}</span></div>}
            {product.return_policy && <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8"><span className="text-neutral-500">Return Policy</span><span className="text-[#0f1419] dark:text-[#F0FDF4]">{product.return_policy.days} days {product.return_policy.free_return ? '(Free)' : ''}</span></div>}
          </div>
          {product.description && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">Description</div>
              <p className="text-xs text-[#5f471d] dark:text-[#A7C4B8] leading-relaxed max-h-32 overflow-y-auto">{product.description}</p>
            </div>
          )}
          {product.product_specs && Object.keys(product.product_specs).length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">Specifications</div>
              <div className="space-y-1">
                {Object.entries(product.product_specs).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs py-0.5"><span className="text-neutral-500">{k}</span><span className="text-[#5f471d] dark:text-[#A7C4B8]">{v}</span></div>
                ))}
              </div>
            </div>
          )}
          {product.reviews && product.reviews.length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">Reviews ({product.reviews.length})</div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {product.reviews.slice(0, 5).map((r, i) => (
                  <div key={i} className="rounded-lg bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 p-2 text-xs">
                    <div className="flex items-center gap-1 mb-1">
                      {r.rating && <span className="text-amber-400">{r.rating}★</span>}
                      {r.author && <span className="text-[#9e8b66] dark:text-[#6B8F80]">{r.author}</span>}
                    </div>
                    <p className="text-[#5f471d] dark:text-[#A7C4B8] line-clamp-3">{r.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}


function CatProductDetailPanel({ product, onClose, onDelete, formatPrice }: {
  product: CategoryProductItem;
  onClose: () => void;
  onDelete: (id: number) => void;
  formatPrice: (p: number | null | undefined) => string;
}) {
  const detail = product.detail_data || {};
  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-[9998]" onClick={onClose} />
      <div className="fixed top-0 right-0 h-full w-full max-w-lg z-[9999] overflow-y-auto border-l border-[#5b4824]/12 dark:border-[#4ADE80]/12 shadow-2xl bg-gradient-to-b from-[#fefbf0] to-[#fffbef] dark:from-[#162420] dark:to-[#0F1A17]">
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-[#5b4824]/12 dark:border-[#4ADE80]/12 bg-[#fefbf0]/98 dark:bg-[#162420]/98 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-[#5b4824]/8 dark:bg-[#4ADE80]/8 text-[#5f471d] dark:text-[#A7C4B8] font-mono">#{product.position}</span>
            <h3 className="text-base font-semibold text-[#0f1419] dark:text-[#F0FDF4] truncate">Category Product</h3>
            {product.detail_fetched && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-600">Detailed</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {product.url && (
              <a href={product.url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-[#5b4824]/8 dark:hover:bg-[#4ADE80]/8 text-[#9e8b66] dark:text-[#6B8F80]">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
            )}
            <button onClick={() => onDelete(product.id)} className="p-1.5 rounded-lg hover:bg-red-500/20 text-red-600" title="Delete product">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
            </button>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#5b4824]/8 dark:hover:bg-[#4ADE80]/8 text-[#9e8b66] dark:text-[#6B8F80]">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {product.image_url && (
            <div className="rounded-lg bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 p-4 flex items-center justify-center">
              <img src={product.image_url} alt="" className="max-h-64 object-contain" />
            </div>
          )}
          <div>
            {product.brand && <div className="text-xs text-[#5b4824] dark:text-[#4ADE80] font-medium uppercase mb-1">{product.brand}</div>}
            <h4 className="text-base font-medium text-[#0f1419] dark:text-[#F0FDF4] leading-snug">{product.name}</h4>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-lg bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 p-3 text-center">
              <div className="text-xs text-neutral-500 mb-1">Price</div>
              <div className="text-base font-bold text-[#0f1419] dark:text-[#F0FDF4]">{formatPrice(product.price)}</div>
              {product.original_price && product.original_price > (product.price || 0) && (
                <div className="text-xs text-neutral-500 line-through">{formatPrice(product.original_price)}</div>
              )}
            </div>
            <div className="rounded-lg bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 p-3 text-center">
              <div className="text-xs text-neutral-500 mb-1">Position</div>
              <div className="text-base font-bold text-[#0f1419] dark:text-[#F0FDF4]">#{product.position}</div>
              <div className="text-xs text-neutral-500">Page {product.page_number}</div>
            </div>
            <div className="rounded-lg bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 p-3 text-center">
              <div className="text-xs text-neutral-500 mb-1">Rating</div>
              <div className="text-base font-bold text-[#0f1419] dark:text-[#F0FDF4] flex items-center justify-center gap-1">
                {product.rating || '-'}
                {product.rating && <svg className="w-3 h-3 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>}
              </div>
              <div className="text-xs text-neutral-500">{product.review_count ?? 0}</div>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            {product.is_sponsored && (
              <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8">
                <span className="text-neutral-500">Type</span>
                <span className="text-amber-400 font-medium">Sponsored Ad</span>
              </div>
            )}
            {product.seller_name && (
              <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8">
                <span className="text-neutral-500">Seller</span>
                <span className="text-[#0f1419] dark:text-[#F0FDF4]">{product.seller_name}</span>
              </div>
            )}
            {product.sku && (
              <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8">
                <span className="text-neutral-500">SKU</span>
                <span className="text-[#0f1419] dark:text-[#F0FDF4] font-mono text-xs">{product.sku}</span>
              </div>
            )}
            {product.barcode && (
              <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8">
                <span className="text-neutral-500">Barcode</span>
                <span className="text-[#0f1419] dark:text-[#F0FDF4] font-mono text-xs">{product.barcode}</span>
              </div>
            )}
            {product.stock_status && (
              <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8">
                <span className="text-neutral-500">Stock</span>
                <span className={product.stock_status === 'inStock' ? 'text-emerald-600' : 'text-orange-400'}>{product.stock_status}</span>
              </div>
            )}
            {product.shipping_type && (
              <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8">
                <span className="text-neutral-500">Shipping</span>
                <span className="text-[#0f1419] dark:text-[#F0FDF4]">{product.shipping_type}</span>
              </div>
            )}
            {product.campaign_text && (
              <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8">
                <span className="text-neutral-500">Campaign</span>
                <span className="text-emerald-600">{product.campaign_text}</span>
              </div>
            )}
            {product.discount_percentage && (
              <div className="flex justify-between py-1.5 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8">
                <span className="text-neutral-500">Discount</span>
                <span className="text-emerald-600">-{product.discount_percentage}%</span>
              </div>
            )}
          </div>
          {product.category_path && (
            <div>
              <div className="text-xs text-neutral-500 mb-1 font-medium">Category Path</div>
              <p className="text-xs text-[#5f471d] dark:text-[#A7C4B8]">{product.category_path}</p>
            </div>
          )}
          {product.seller_list && product.seller_list.length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-2 font-medium">All Sellers ({product.seller_list.length})</div>
              <div className="space-y-1">
                {product.seller_list.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1 px-2 rounded bg-[#5b4824]/5 dark:bg-[#4ADE80]/5">
                    <span className="text-[#0f1419] dark:text-[#F0FDF4]">{s.name}</span>
                    {s.id && <span className="text-neutral-500 font-mono text-[10px]">ID: {s.id}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {product.description && (
            <div>
              <div className="text-xs text-neutral-500 mb-1 font-medium">Description</div>
              <p className="text-xs text-[#5f471d] dark:text-[#A7C4B8] leading-relaxed max-h-40 overflow-y-auto whitespace-pre-line">{product.description}</p>
            </div>
          )}
          {product.specs && Object.keys(product.specs).length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-2 font-medium">Specifications</div>
              <div className="space-y-1">
                {Object.entries(product.specs).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs py-1 px-2 rounded bg-[#5b4824]/5 dark:bg-[#4ADE80]/5">
                    <span className="text-[#9e8b66] dark:text-[#6B8F80]">{k}</span>
                    <span className="text-[#0f1419] dark:text-[#F0FDF4] text-right max-w-[60%]">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {detail && Object.keys(detail).length > 0 && !product.specs && (
            <div>
              <div className="text-xs text-neutral-500 mb-2 font-medium">Additional Details</div>
              {detail.description && !product.description && (
                <div className="mb-2">
                  <div className="text-xs text-neutral-500 mb-1">Description</div>
                  <p className="text-xs text-[#5f471d] dark:text-[#A7C4B8] leading-relaxed max-h-32 overflow-y-auto">{detail.description}</p>
                </div>
              )}
              {detail.category && !product.category_path && (
                <div className="mb-2">
                  <div className="text-xs text-neutral-500 mb-1">Category</div>
                  <p className="text-xs text-[#5f471d] dark:text-[#A7C4B8]">{detail.category}</p>
                </div>
              )}
              {detail.product_specs && Object.keys(detail.product_specs).length > 0 && (
                <div className="mb-2">
                  <div className="text-xs text-neutral-500 mb-1">Specifications</div>
                  <div className="space-y-1">
                    {Object.entries(detail.product_specs).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-xs py-0.5"><span className="text-neutral-500">{k}</span><span className="text-[#5f471d] dark:text-[#A7C4B8]">{String(v)}</span></div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}


export default function ProductDetailModals(ce: UseCategoryExplorerReturn) {
  const {
    selectedProduct,
    selectedCatProduct,
    showMobileFilters,
    setSelectedProduct,
    setSelectedCatProduct,
    setShowMobileFilters,
    selectCategory,
    handleDeleteProduct,
    formatPrice,
  } = ce;

  return (
    <>
      {selectedProduct && createPortal(
        <ProductDetailPanel
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
          formatPrice={formatPrice}
          selectCategory={(cat) => { selectCategory(cat); setSelectedProduct(null); }}
        />,
        document.body
      )}

      {selectedCatProduct && createPortal(
        <CatProductDetailPanel
          product={selectedCatProduct}
          onClose={() => setSelectedCatProduct(null)}
          onDelete={handleDeleteProduct}
          formatPrice={formatPrice}
        />,
        document.body
      )}

      {showMobileFilters && createPortal(
        <>
          <div className="fixed inset-0 bg-black/60 z-[9996]" onClick={() => setShowMobileFilters(false)} />
          <div className="fixed top-0 left-0 h-full w-80 z-[9997] overflow-y-auto border-r border-[#5b4824]/12 dark:border-[#4ADE80]/12 shadow-2xl p-4 bg-gradient-to-b from-[#fefbf0] to-[#fffbef] dark:from-[#162420] dark:to-[#0F1A17]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-[#0f1419] dark:text-[#F0FDF4]">Filters</h3>
              <button onClick={() => setShowMobileFilters(false)} className="p-1.5 rounded-lg hover:bg-[#5b4824]/8 dark:hover:bg-[#4ADE80]/8 text-[#9e8b66] dark:text-[#6B8F80]">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <CategoryFilters {...ce} />
          </div>
        </>,
        document.body
      )}
    </>
  );
}
