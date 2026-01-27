import { useState, useEffect } from 'react';
import { getTasks, getSponsoredProducts, getSponsoredBrands } from '../services/api';
import type { SearchTask, SponsoredProduct, SponsoredBrand } from '../services/api';

type TabType = 'sponsored' | 'brands';

export default function Ads() {
  const [tasks, setTasks] = useState<SearchTask[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<TabType>('sponsored');
  const [sponsoredProducts, setSponsoredProducts] = useState<SponsoredProduct[]>([]);
  const [sponsoredBrands, setSponsoredBrands] = useState<SponsoredBrand[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedBrand, setExpandedBrand] = useState<string | null>(null);
  const [selectedKeyword, setSelectedKeyword] = useState<string>('');

  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    if (selectedTaskId) {
      loadAdsData();
    }
  }, [selectedTaskId]);

  const loadTasks = async () => {
    try {
      const data = await getTasks(50);
      const completedTasks = data.filter(t => t.status === 'completed');
      setTasks(completedTasks);
      if (completedTasks.length > 0) {
        setSelectedTaskId(completedTasks[0].id);
        setSelectedKeyword(completedTasks[0].keyword);
      }
    } catch (error) {
      console.error('Failed to load tasks:', error);
    }
  };

  const loadAdsData = async () => {
    if (!selectedTaskId) return;
    setLoading(true);
    try {
      const [sponsoredData, brandsData] = await Promise.all([
        getSponsoredProducts(selectedTaskId),
        getSponsoredBrands(selectedTaskId)
      ]);
      setSponsoredProducts(sponsoredData.sponsored_products || []);
      setSponsoredBrands(brandsData.sponsored_brands || []);
    } catch (error) {
      console.error('Failed to load ads data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTaskChange = (taskId: string) => {
    setSelectedTaskId(taskId);
    const task = tasks.find(t => t.id === taskId);
    if (task) {
      setSelectedKeyword(task.keyword);
    }
    setExpandedBrand(null);
  };

  const formatPrice = (price?: number) => {
    if (!price) return '-';
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY'
    }).format(price);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Ads</h1>
          <p className="text-neutral-400 mt-1">Analyze sponsored products and brand advertisements</p>
        </div>
      </div>

      <div className="card-dark p-5">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-64">
            <label className="block text-sm font-medium text-neutral-400 mb-2">
              Search Keyword
            </label>
            <select
              value={selectedTaskId}
              onChange={(e) => handleTaskChange(e.target.value)}
              className="input-dark w-full"
            >
              <option value="">Select a keyword</option>
              {tasks.map((task) => (
                <option key={task.id} value={task.id}>
                  {task.keyword} ({new Date(task.created_at).toLocaleDateString('en-US')})
                </option>
              ))}
            </select>
          </div>

          {selectedKeyword && (
            <div className="px-4 py-2 rounded-lg bg-accent-primary/10 border border-accent-primary/20">
              <span className="text-sm text-neutral-400">Selected:</span>
              <span className="ml-2 text-accent-primary font-medium">"{selectedKeyword}"</span>
            </div>
          )}
        </div>
      </div>

      <div className="card-dark overflow-hidden">
        <div className="border-b border-white/5">
          <nav className="flex">
            <button
              onClick={() => setActiveTab('sponsored')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-all ${
                activeTab === 'sponsored'
                  ? 'border-accent-primary text-accent-primary'
                  : 'border-transparent text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
                </svg>
                Sponsored Products ({sponsoredProducts.length})
              </span>
            </button>
            <button
              onClick={() => setActiveTab('brands')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-all ${
                activeTab === 'brands'
                  ? 'border-accent-primary text-accent-primary'
                  : 'border-transparent text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                Brand Ads ({sponsoredBrands.length})
              </span>
            </button>
          </nav>
        </div>

        <div className="p-5">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="w-8 h-8 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin" />
            </div>
          ) : !selectedTaskId ? (
            <div className="text-center py-12">
              <div className="w-12 h-12 rounded-full bg-dark-600 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-neutral-400">Please select a search keyword</p>
            </div>
          ) : activeTab === 'sponsored' ? (
            <SponsoredProductsTab products={sponsoredProducts} formatPrice={formatPrice} />
          ) : (
            <BrandAdsTab 
              brands={sponsoredBrands} 
              expandedBrand={expandedBrand}
              setExpandedBrand={setExpandedBrand}
              formatPrice={formatPrice}
            />
          )}
        </div>
      </div>
    </div>
  );
}

interface SponsoredProductsTabProps {
  products: SponsoredProduct[];
  formatPrice: (price?: number) => string;
}

function SponsoredProductsTab({ products, formatPrice }: SponsoredProductsTabProps) {
  if (products.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-12 h-12 rounded-full bg-dark-600 flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-neutral-400">No sponsored products found for this search</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {products.map((product, index) => (
        <div key={index} className="card-dark border border-white/5 overflow-hidden hover:border-accent-primary/30 transition-all group">
          <div className="relative">
            {product.image_url ? (
              <img 
                src={product.image_url} 
                alt={product.product_name || 'Product'} 
                className="w-full h-48 object-contain bg-dark-900 p-2"
              />
            ) : (
              <div className="w-full h-48 bg-dark-700 flex items-center justify-center">
                <svg className="w-12 h-12 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            )}
            <div className="absolute top-2 left-2 badge badge-warning text-[10px]">
              #{product.order_index + 1} Position
            </div>
            <div className="absolute top-2 right-2 badge badge-danger text-[10px]">
              Ad
            </div>
          </div>
          <div className="p-4">
            <h3 className="font-medium text-sm text-neutral-200 line-clamp-2 mb-2 min-h-[2.5rem]">
              {product.product_name || 'Unnamed Product'}
            </h3>
            {product.seller_name && (
              <p className="text-xs text-neutral-500 mb-3">
                Seller: {product.seller_name}
              </p>
            )}
            <div className="flex items-center gap-2 mb-3">
              {product.discounted_price ? (
                <>
                  <span className="text-lg font-bold text-success">
                    {formatPrice(product.discounted_price)}
                  </span>
                  <span className="text-sm text-neutral-500 line-through">
                    {formatPrice(product.price)}
                  </span>
                </>
              ) : (
                <span className="text-lg font-bold text-neutral-200">
                  {formatPrice(product.price)}
                </span>
              )}
            </div>
            <a 
              href={product.product_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="block text-center text-sm text-accent-primary hover:text-accent-primary/80 transition-colors"
            >
              View Product →
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}

interface BrandAdsTabProps {
  brands: SponsoredBrand[];
  expandedBrand: string | null;
  setExpandedBrand: (brand: string | null) => void;
  formatPrice: (price?: number) => string;
}

function BrandAdsTab({ brands, expandedBrand, setExpandedBrand, formatPrice }: BrandAdsTabProps) {
  if (brands.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-12 h-12 rounded-full bg-dark-600 flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
        </div>
        <p className="text-neutral-400">No brand ads found for this search</p>
        <p className="text-sm text-neutral-500 mt-1">Brand ads are loaded dynamically and may not be captured</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {brands.map((brand, index) => (
        <div key={index} className="rounded-lg border border-white/5 overflow-hidden">
          <button
            onClick={() => setExpandedBrand(expandedBrand === brand.seller_name ? null : brand.seller_name)}
            className="w-full px-4 py-4 flex items-center justify-between bg-dark-700/50 hover:bg-dark-600/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="badge badge-info text-[10px]">
                #{brand.position || index + 1}
              </span>
              <span className="font-medium text-neutral-200">{brand.seller_name}</span>
              <span className="text-sm text-neutral-500">
                ({brand.products?.length || 0} products)
              </span>
            </div>
            <svg 
              className={`w-5 h-5 text-neutral-400 transition-transform ${expandedBrand === brand.seller_name ? 'rotate-180' : ''}`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {expandedBrand === brand.seller_name && brand.products && brand.products.length > 0 && (
            <div className="p-4 border-t border-white/5 bg-dark-800/50">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {brand.products.map((product, pIndex) => (
                  <div key={pIndex} className="rounded-lg border border-white/5 overflow-hidden hover:border-accent-primary/20 transition-all bg-dark-700/30">
                    <div className="relative bg-dark-900 h-28">
                      {product.image_url ? (
                        <img 
                          src={product.image_url} 
                          alt={product.name || 'Product'} 
                          className="w-full h-full object-contain p-2"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <svg className="w-8 h-8 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <div className="p-3">
                      <p className="text-xs font-medium text-neutral-300 line-clamp-2 mb-2 min-h-[2rem]">
                        {product.name || 'Product'}
                      </p>
                      <div className="flex items-center gap-2 mb-2">
                        {product.discounted_price ? (
                          <>
                            <span className="text-sm font-bold text-success">
                              {formatPrice(product.discounted_price)}
                            </span>
                            <span className="text-xs text-neutral-500 line-through">
                              {formatPrice(product.price)}
                            </span>
                          </>
                        ) : product.price ? (
                          <span className="text-sm font-bold text-neutral-200">
                            {formatPrice(product.price)}
                          </span>
                        ) : (
                          <span className="text-xs text-neutral-500">No price</span>
                        )}
                      </div>
                      {product.url && (
                        <a 
                          href={product.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-accent-primary hover:text-accent-primary/80 transition-colors"
                        >
                          View →
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
