export interface SearchTask {
  id: string;
  keyword: string;
  platform: string;
  status: string;
  total_products: number;
  created_at: string;
}

export interface Coupon {
  amount?: number;
  min_order?: number;
}

export interface Campaign {
  name: string;
  url?: string;
}

export interface Seller {
  seller_name: string;
  seller_rating?: number;
  price?: number;
  is_authorized: boolean;
}

export interface Review {
  author?: string;
  rating?: number;
  review_text?: string;
  review_date?: string;
  seller_name?: string;
}

export interface Product {
  id: string;
  platform: string;
  external_id: string;
  sku?: string;
  barcode?: string;
  name: string;
  url: string;
  brand?: string;
  seller_name?: string;
  seller_rating?: number;
  category_path?: string;
  category_hierarchy?: string;
  image_url?: string;
  description?: string;
  origin_country?: string;
  latest_price?: number;
  discounted_price?: number;
  discount_percentage?: number;
  latest_rating?: number;
  reviews_count?: number;
  stock_count?: number;
  in_stock?: boolean;
  is_sponsored?: boolean;
  coupons?: Coupon[];
  campaigns?: Campaign[];
}

export interface ProductDetail extends Product {
  other_sellers: Seller[];
  reviews: Review[];
}

export interface Snapshot {
  id: number;
  price?: number;
  discounted_price?: number;
  discount_percentage?: number;
  rating?: number;
  reviews_count?: number;
  stock_count?: number;
  in_stock: boolean;
  is_sponsored: boolean;
  coupons?: Coupon[];
  campaigns?: Campaign[];
  snapshot_date: string;
}

export interface Stats {
  total_products: number;
  total_snapshots: number;
  total_tasks: number;
  completed_tasks: number;
  total_sellers?: number;
  total_reviews?: number;
}

export interface StatTrends {
  products: number[];
  snapshots: number[];
  tasks: number[];
  completed: number[];
}

export interface SponsoredProduct {
  order_index: number;
  product_url: string;
  product_name?: string;
  seller_name?: string;
  price?: number;
  discounted_price?: number;
  image_url?: string;
  snapshot_date?: string;
}

export interface BrandProduct {
  url?: string;
  name?: string;
  price?: number;
  discounted_price?: number;
  image_url?: string;
}

export interface SponsoredBrand {
  seller_name: string;
  seller_id?: string;
  position?: number;
  products?: BrandProduct[];
  snapshot_date?: string;
}

export interface SponsoredProductsResponse {
  keyword: string;
  total_sponsored: number;
  sponsored_products: SponsoredProduct[];
}

export interface SponsoredBrandsResponse {
  keyword: string;
  sponsored_brands: SponsoredBrand[];
}

export interface MonitoredProduct {
  id: string;
  platform: string;
  sku: string;
  barcode?: string;
  product_url: string;
  product_name?: string;
  brand?: string;
  seller_stock_code?: string;
  threshold_price?: number;
  alert_campaign_price?: number;
  image_url?: string;
  is_active: boolean;
  last_fetched_at?: string;
  seller_count: number;
  has_price_alert: boolean;
  price_alert_count: number;
  has_campaign_alert: boolean;
  campaign_alert_count: number;
}

export interface SellerSnapshot {
  merchant_id: string;
  merchant_name: string;
  merchant_logo?: string;
  merchant_url_postfix?: string;
  merchant_url?: string;
  merchant_rating?: number;
  merchant_rating_count?: number;
  merchant_city?: string;
  price: number;
  list_price?: number;
  original_price?: number;
  minimum_price?: number;
  discount_rate?: number;
  stock_quantity?: number;
  buybox_order?: number;
  free_shipping: boolean;
  fast_shipping: boolean;
  is_fulfilled_by_hb: boolean;
  campaigns?: string[];
  campaign_price?: number;
  snapshot_date: string;
  price_alert: boolean;
  campaign_alert?: boolean;
}

export interface MonitoredProductsResponse {
  products: MonitoredProduct[];
  total: number;
  active_count: number;
  inactive_count: number;
  limit: number;
  offset: number;
}

export interface ProductWithSellers {
  product: MonitoredProduct;
  sellers: SellerSnapshot[];
}

export interface FetchTask {
  id: string;
  status: string;
  total_products: number;
  completed_products: number;
  failed_products: number;
  created_at: string;
  completed_at?: string;
}

export interface BulkProductInput {
  productUrl?: string;
  productName?: string;
  sku?: string;
  barcode?: string;
  brand?: string;
  price?: number;
  campaignPrice?: number;
  sellerStockCode?: string;
}

export interface GetProductsParams {
  platform?: string;
  brand?: string;
  price_alert_only?: boolean;
  campaign_alert_only?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface RequestOptions {
  signal?: AbortSignal;
  forceRefresh?: boolean;
}

export interface LastInactiveProduct {
  id: string;
  sku: string;
  product_name: string;
  brand: string;
  is_active: boolean;
}

export type ExportActiveFilter = 'all' | 'active' | 'inactive';

export type FetchType = 'active' | 'last_inactive' | 'inactive';

export interface SellerInfo {
  merchant_id: string;
  merchant_name: string;
  merchant_logo?: string;
  merchant_url_postfix?: string;
  merchant_rating?: number;
  product_count: number;
  price_alert_count: number;
  campaign_alert_count: number;
}

export interface SellersResponse {
  sellers: SellerInfo[];
  total: number;
  limit?: number;
  offset?: number;
}

export interface SellerProduct {
  product_id: string;
  sku?: string;
  barcode?: string;
  product_name?: string;
  product_url?: string;
  seller_url?: string;
  brand?: string;
  seller_stock_code?: string;
  image_url?: string;
  threshold_price?: number;
  seller_price?: number;
  original_price?: number;
  campaign_price?: number;
  alert_campaign_price?: number;
  campaigns?: string[];
  price_alert: boolean;
  campaign_alert: boolean;
  price_difference?: number;
  campaign_difference?: number;
  snapshot_date: string;
}

export interface SellerProductsResponse {
  products: SellerProduct[];
  total: number;
  merchant_name: string;
  price_alert_count: number;
  campaign_alert_count: number;
  limit?: number;
  offset?: number;
}

export interface ScrapeJobInfo {
  id: string;
  status: string;
  total_urls: number;
  completed_urls: number;
  failed_urls: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface ScrapeResultItem {
  id: number;
  url: string;
  product_name?: string;
  barcode?: string;
  status: string;
  scraped_data?: Record<string, unknown>;
  error_message?: string;
}

export interface ScrapeJobDetail extends ScrapeJobInfo {
  results: ScrapeResultItem[];
}

export interface TranscriptJobInfo {
  id: string;
  status: string;
  total_videos: number;
  completed_videos: number;
  failed_videos: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface TranscriptResultItem {
  id: number;
  video_url: string;
  product_name?: string;
  barcode?: string;
  status: string;
  language?: string;
  language_code?: string;
  is_generated?: boolean;
  transcript_text?: string;
  snippet_count?: number;
  error_message?: string;
}

export interface TranscriptJobDetail extends TranscriptJobInfo {
  results: TranscriptResultItem[];
}

export interface StoreProduct {
  id: string;
  platform: string;
  source_url: string;
  sku: string | null;
  barcode: string | null;
  product_name: string | null;
  brand: string | null;
  category: string | null;
  category_breadcrumbs: Array<{ name: string; url: string; position: number }> | null;
  price: number | null;
  currency: string | null;
  availability: string | null;
  rating: number | null;
  rating_count: number | null;
  review_count: number | null;
  reviews: Array<{ author: string; date: string; text: string; rating: number }> | null;
  image_url: string | null;
  images: string[] | null;
  description: string | null;
  seller_name: string | null;
  shipping_info: { cost: string; currency: string } | null;
  return_policy: { days: number; free_return: boolean } | null;
  product_specs: Record<string, string> | null;
  additional_properties: Record<string, string> | null;
  related_products: string[] | null;
  created_at: string | null;
  updated_at: string | null;
  raw_scraped_data?: any;
  og_data?: any;
}

export interface StoreProductFilters {
  brands: Array<{ name: string; count: number }>;
  categories: Array<{ name: string; count: number }>;
  platforms: Array<{ name: string; count: number }>;
  price_range: { min: number; max: number; avg: number };
}

export interface FilteredStats {
  avg_price: number;
  brand_count: number;
  category_count?: number;
}

export interface StoreProductListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  products: StoreProduct[];
  filtered_stats?: FilteredStats;
}

export interface CategoryProductItem {
  id: number;
  session_id: string;
  name: string;
  url: string;
  image_url: string;
  brand: string;
  price: number | null;
  original_price: number | null;
  discount_percentage: number | null;
  rating: number | null;
  review_count: number | null;
  is_sponsored: boolean;
  campaign_text: string;
  seller_name: string;
  page_number: number;
  position: number;
  detail_fetched: boolean;
  detail_data: any;
  sku: string | null;
  barcode: string | null;
  description: string | null;
  specs: Record<string, any> | null;
  shipping_type: string | null;
  stock_status: string | null;
  category_path: string | null;
  seller_list: Array<{ name: string; id?: string; listing_id?: string }> | null;
  updated_at: string | null;
  created_at: string | null;
}

export interface CategoryFilterData {
  brands: string[];
  sellers: string[];
  price_range: { min: number; max: number };
}

export interface CategoryProductListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  products: CategoryProductItem[];
  filtered_stats: { avg_price: number; brand_count: number; seller_count?: number; last_scraped?: string | null };
  sessions?: Array<{
    id: string;
    platform: string;
    category_url: string;
    category_name: string;
    breadcrumbs: Array<{ name: string; url?: string }>;
    total_products: number;
    pages_scraped: number;
    status: string;
    created_at: string;
    product_count: number;
  }>;
}

export interface CategoryTreeNode {
  name: string;
  full_path: string;
  count: number;
  depth: number;
  category_url?: string | null;
  children: CategoryTreeNode[];
}

export interface ScrapeJobStatus {
  job_id: string;
  status: string;
  total: number;
  completed: number;
  failed: number;
  pending: number;
  skipped: number;
  created_at: string | null;
  completed_at: string | null;
}
