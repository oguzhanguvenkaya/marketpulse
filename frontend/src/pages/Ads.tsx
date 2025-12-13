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
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Reklamlar</h1>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-64">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Arama Kelimesi
            </label>
            <select
              value={selectedTaskId}
              onChange={(e) => handleTaskChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">Kelime Seçin</option>
              {tasks.map((task) => (
                <option key={task.id} value={task.id}>
                  {task.keyword} ({new Date(task.created_at).toLocaleDateString('tr-TR')})
                </option>
              ))}
            </select>
          </div>

          {selectedKeyword && (
            <div className="text-sm text-gray-600">
              <span className="font-medium">Seçili:</span> "{selectedKeyword}"
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex">
            <button
              onClick={() => setActiveTab('sponsored')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'sponsored'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Sponsorlu Ürünler ({sponsoredProducts.length})
            </button>
            <button
              onClick={() => setActiveTab('brands')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'brands'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Marka Reklamları ({sponsoredBrands.length})
            </button>
          </nav>
        </div>

        <div className="p-4">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : !selectedTaskId ? (
            <div className="text-center py-12 text-gray-500">
              Lütfen bir arama kelimesi seçin
            </div>
          ) : activeTab === 'sponsored' ? (
            <SponsoredProductsTab products={sponsoredProducts} formatPrice={formatPrice} />
          ) : (
            <BrandAdsTab 
              brands={sponsoredBrands} 
              expandedBrand={expandedBrand}
              setExpandedBrand={setExpandedBrand}
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
      <div className="text-center py-12 text-gray-500">
        Bu arama için sponsorlu ürün bulunamadı
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {products.map((product, index) => (
        <div key={index} className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow">
          <div className="relative">
            {product.image_url ? (
              <img 
                src={product.image_url} 
                alt={product.product_name || 'Ürün'} 
                className="w-full h-48 object-contain bg-gray-50"
              />
            ) : (
              <div className="w-full h-48 bg-gray-100 flex items-center justify-center">
                <span className="text-gray-400">Resim Yok</span>
              </div>
            )}
            <div className="absolute top-2 left-2 bg-orange-500 text-white text-xs px-2 py-1 rounded">
              #{product.order_index + 1} Pozisyon
            </div>
            <div className="absolute top-2 right-2 bg-red-500 text-white text-xs px-2 py-1 rounded">
              Reklam
            </div>
          </div>
          <div className="p-3">
            <h3 className="font-medium text-sm text-gray-900 line-clamp-2 mb-2">
              {product.product_name || 'İsimsiz Ürün'}
            </h3>
            {product.seller_name && (
              <p className="text-xs text-gray-500 mb-2">
                Satıcı: {product.seller_name}
              </p>
            )}
            <div className="flex items-center gap-2">
              {product.discounted_price ? (
                <>
                  <span className="text-lg font-bold text-green-600">
                    {formatPrice(product.discounted_price)}
                  </span>
                  <span className="text-sm text-gray-400 line-through">
                    {formatPrice(product.price)}
                  </span>
                </>
              ) : (
                <span className="text-lg font-bold text-gray-900">
                  {formatPrice(product.price)}
                </span>
              )}
            </div>
            <a 
              href={product.product_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="mt-3 block text-center text-sm text-indigo-600 hover:text-indigo-800"
            >
              Ürüne Git →
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
}

function BrandAdsTab({ brands, expandedBrand, setExpandedBrand }: BrandAdsTabProps) {
  if (brands.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Bu arama için marka reklamı bulunamadı</p>
        <p className="text-sm mt-2">Not: Marka reklamları dinamik olarak yüklenir ve henüz yakalanamamaktadır</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {brands.map((brand, index) => (
        <div key={index} className="border rounded-lg overflow-hidden">
          <button
            onClick={() => setExpandedBrand(expandedBrand === brand.seller_name ? null : brand.seller_name)}
            className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="bg-purple-100 text-purple-700 text-xs px-2 py-1 rounded">
                #{brand.position || index + 1}
              </span>
              <span className="font-medium text-gray-900">{brand.seller_name}</span>
              <span className="text-sm text-gray-500">
                ({brand.products?.length || 0} ürün)
              </span>
            </div>
            <svg 
              className={`w-5 h-5 text-gray-400 transition-transform ${expandedBrand === brand.seller_name ? 'rotate-180' : ''}`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {expandedBrand === brand.seller_name && brand.products && brand.products.length > 0 && (
            <div className="p-4 border-t bg-white">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {brand.products.map((product, pIndex) => (
                  <a
                    key={pIndex}
                    href={product.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {product.name || 'Ürün'}
                      </p>
                      <p className="text-xs text-indigo-600">
                        Ürüne Git →
                      </p>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
