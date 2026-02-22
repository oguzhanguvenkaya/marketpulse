import MarketplaceProductList from '../components/MarketplaceProductList';

export default function TrendyolProducts() {
  return (
    <MarketplaceProductList
      platform="trendyol"
      platformLabel="Trendyol"
      platformColor="#f27a1a"
      platformIcon={
        <svg className="w-5 h-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
      }
    />
  );
}
