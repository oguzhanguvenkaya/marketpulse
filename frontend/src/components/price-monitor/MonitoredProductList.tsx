import { PAGE_SIZE, type UsePriceMonitorReturn } from '../../hooks/usePriceMonitor';

export default function MonitoredProductList({
  showInactive,
  setShowInactive,
  activeTotalCount,
  inactiveTotalCount,
  totalProducts,
  searchInput,
  setSearchInput,
  selectedBrand,
  setSelectedBrand,
  brands,
  priceAlertOnly,
  setPriceAlertOnly,
  campaignAlertOnly,
  setCampaignAlertOnly,
  loading,
  activeProducts,
  inactiveProducts,
  selectedProduct,
  handleProductClick,
  handleFetchSingle,
  handleDeleteRequest,
  getProductUrl,
  formatDate,
  currentOffset,
  setCurrentOffset,
  currentOffsetRef,
  loadProducts,
}: UsePriceMonitorReturn) {
  return (
    <div className="card-dark p-4 md:p-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <h2 className="text-base md:text-lg font-semibold text-text-primary">Monitored Products</h2>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <button
            onClick={() => setShowInactive(false)}
            aria-pressed={!showInactive}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
              !showInactive ? 'bg-success/20 text-success border border-success/30' : 'bg-surface-hover text-text-muted hover:bg-surface-hover-active'
            }`}
          >
            Active ({activeTotalCount}{totalProducts > 0 ? `/${totalProducts}` : ''})
          </button>
          <button
            onClick={() => setShowInactive(true)}
            aria-pressed={showInactive}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
              showInactive ? 'bg-neutral-500/20 text-text-body border border-neutral-500/30' : 'bg-surface-hover text-text-muted hover:bg-surface-hover-active'
            }`}
          >
            Inactive ({inactiveTotalCount})
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2 mb-4">
        <input
          type="text"
          placeholder="Search by SKU, barcode, stock code or name..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="input-dark text-sm w-full xl:col-span-2"
        />
        <select
          value={selectedBrand}
          onChange={(e) => setSelectedBrand(e.target.value)}
          className="input-dark text-sm w-full"
        >
          <option value="">All Brands</option>
          {brands.map(brand => (
            <option key={brand} value={brand}>{brand}</option>
          ))}
        </select>
        <button
          onClick={() => setPriceAlertOnly(!priceAlertOnly)}
          aria-pressed={priceAlertOnly}
          className={`px-3 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap ${
            priceAlertOnly
              ? 'bg-danger/20 text-danger border border-danger/30'
              : 'bg-surface-hover text-text-muted hover:bg-surface-hover-active'
          }`}
        >
          Price Alerts
        </button>
        <button
          onClick={() => setCampaignAlertOnly(!campaignAlertOnly)}
          aria-pressed={campaignAlertOnly}
          className={`px-3 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap ${
            campaignAlertOnly
              ? 'bg-warning/20 text-warning border border-warning/30'
              : 'bg-surface-hover text-text-muted hover:bg-surface-hover-active'
          }`}
        >
          Campaign Alerts
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="w-8 h-8 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin mx-auto" />
          <p className="text-text-muted mt-3">Loading products...</p>
        </div>
      ) : (showInactive ? inactiveProducts : activeProducts).length === 0 ? (
        <div className="text-center py-12">
          <div className="w-12 h-12 rounded-full bg-surface-hover flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <p className="text-text-muted">{showInactive ? 'No inactive products' : 'No monitored products yet'}</p>
          <p className="text-sm text-text-muted mt-1">{showInactive ? '' : 'Click "Add SKU" to start monitoring'}</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
          {(showInactive ? inactiveProducts : activeProducts).map((product) => (
            <button
              type="button"
              key={product.id}
              onClick={() => handleProductClick(product)}
              className={`p-3 md:p-4 rounded-lg border cursor-pointer transition-all text-left w-full ${
                selectedProduct?.id === product.id
                  ? 'border-accent-primary/50 bg-accent-primary/5'
                  : showInactive
                    ? 'border-accent-primary/8 bg-dark-800/50 hover:bg-surface-hover/50'
                    : 'border-accent-primary/8 bg-dark-800/30 hover:border-accent-primary/12 hover:bg-surface-hover/30'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex gap-1.5 mb-2 flex-wrap">
                    {showInactive && (
                      <span className="badge badge-neutral">Inactive</span>
                    )}
                    {product.has_price_alert && (
                      <span className="badge badge-danger">
                        Price ({product.price_alert_count})
                      </span>
                    )}
                    {product.has_campaign_alert && (
                      <span className="badge badge-warning">
                        Campaign ({product.campaign_alert_count})
                      </span>
                    )}
                    {product.brand && (
                      <span className="badge badge-info">{product.brand}</span>
                    )}
                  </div>
                  {product.product_name ? (
                    <a
                      href={getProductUrl(product)}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className={`font-medium text-sm truncate block ${
                        showInactive
                          ? 'text-text-muted hover:text-text-body'
                          : 'text-accent-primary hover:text-accent-primary dark:hover:text-[#86EFAC]'
                      }`}
                    >
                      {product.product_name}
                    </a>
                  ) : (
                    <a
                      href={getProductUrl(product)}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className={`font-medium text-sm ${
                        showInactive
                          ? 'text-text-muted hover:text-text-body'
                          : 'text-accent-primary hover:text-accent-primary dark:hover:text-[#86EFAC]'
                      }`}
                    >
                      {product.sku}
                    </a>
                  )}
                  {product.product_name && (
                    <div className="text-xs text-text-muted mt-1">
                      {product.barcode ? `Barcode: ${product.barcode}` : `SKU: ${product.sku}`}
                    </div>
                  )}
                  <div className="text-xs text-text-muted mt-1 flex items-center gap-2">
                    <span>{product.seller_count} sellers</span>
                    {product.last_fetched_at && (
                      <>
                        <span className="text-text-faded">•</span>
                        <span>Last: {formatDate(product.last_fetched_at)}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex gap-1 flex-shrink-0 self-start sm:self-auto">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleFetchSingle(product.id); }}
                    className="text-accent-primary hover:text-accent-primary/80 text-xs px-2 py-1 rounded hover:bg-accent-primary/10 transition-colors cursor-pointer"
                  >
                    Refresh
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteRequest(product.id); }}
                    className="text-danger hover:text-danger/80 text-xs px-2 py-1 rounded hover:bg-danger/10 transition-colors cursor-pointer"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalProducts > PAGE_SIZE && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-4 pt-3 border-t border-accent-primary/8">
          <span className="text-xs text-text-muted">
            {currentOffset + 1}–{Math.min(currentOffset + PAGE_SIZE, totalProducts)} of {totalProducts}
          </span>
          <div className="flex gap-2">
            <button
              disabled={currentOffset === 0 || loading}
              onClick={() => {
                const newOff = Math.max(0, currentOffset - PAGE_SIZE);
                setCurrentOffset(newOff);
                currentOffsetRef.current = newOff;
                void loadProducts(newOff);
              }}
              className="px-3 py-1.5 text-xs rounded-lg font-medium bg-surface-hover text-text-muted hover:bg-surface-hover-active disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <button
              disabled={currentOffset + PAGE_SIZE >= totalProducts || loading}
              onClick={() => {
                const newOff = currentOffset + PAGE_SIZE;
                setCurrentOffset(newOff);
                currentOffsetRef.current = newOff;
                void loadProducts(newOff);
              }}
              className="px-3 py-1.5 text-xs rounded-lg font-medium bg-surface-hover text-text-muted hover:bg-surface-hover-active disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
