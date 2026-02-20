# Frontend - React + TypeScript + Vite

## Tech Stack

- React 19 with TypeScript
- Vite 7 (dev server + build)
- TailwindCSS v4
- Plotly.js (charts)
- React Router DOM v7
- Axios (HTTP client)

## Directory Structure

```
frontend/src/
├── pages/                         # Route pages (lazy-loaded)
│   ├── Dashboard.tsx              # Overview: stats, keyword search, recent tasks
│   ├── Products.tsx               # Product listing with filters
│   ├── ProductDetail.tsx          # Single product: info, snapshots, sellers, reviews
│   ├── Ads.tsx                    # Sponsored ads: brand ads & product ads per search
│   ├── PriceMonitor.tsx           # SKU price tracking: bulk import, fetch, seller prices
│   ├── Sellers.tsx                # Seller listing with aggregated metrics
│   ├── SellerDetail.tsx           # Single seller: products, pricing
│   ├── UrlScraper.tsx             # Generic URL scraping: single/bulk/CSV
│   ├── VideoTranscripts.tsx       # YouTube transcript extraction
│   └── JsonEditor.tsx             # JSON file editor with dynamic field rendering
│
├── components/
│   └── Layout.tsx                 # App shell: sidebar navigation, header, mobile menu
│
├── services/
│   ├── api.ts                     # Axios API client (700+ lines)
│   │   ├── All API call functions
│   │   ├── TypeScript interfaces
│   │   └── Cache invalidation helpers
│   └── queryCache.ts              # Client-side query cache (TTL-based)
│
├── App.tsx                        # Router setup with lazy loading
├── main.tsx                       # Entry point
├── index.css                      # TailwindCSS + custom dark theme
└── App.css                        # Additional styles
```

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Stats overview, keyword search form, recent search tasks |
| Products | `/products` | Filterable product grid with search, platform, and sort |
| Product Detail | `/products/:id` | Tabs: Info, Price History (Plotly chart), Sellers, Reviews |
| Ads | `/ads` | Sponsored brand ads and individual sponsored products per search |
| Price Monitor | `/price-monitor` | Add SKUs, trigger fetch, view seller prices, export CSV |
| Sellers | `/sellers` | Seller list with product count, avg price, rating |
| Seller Detail | `/sellers/:merchantId` | All products for a seller, pricing breakdown |
| URL Scraper | `/url-scraper` | Scrape any URL: single input, bulk JSON, or CSV upload |
| Video Transcripts | `/video-transcripts` | Extract YouTube transcripts: single, bulk, or CSV |
| JSON Editor | `/json-editor` | Upload/edit JSON files with auto-detected field types |

## Theme

Palantir-style dark theme:

- Background: `#0a0b0d` (dark-900) to `#3d434e` (dark-300)
- Accent: `#00d4ff` (cyan) for primary actions
- Status: Green (success), Orange (warning), Red (danger)
- Glow variants for interactive elements
- Animations: fade-in, slide-in, pulse-glow

## API Client

`services/api.ts` provides typed functions for all backend endpoints. Uses:
- Axios with `/api` base URL
- `X-API-Key` header from `VITE_INTERNAL_API_KEY`
- Client-side query cache (`queryCache.ts`) with configurable TTL

## Running

```bash
npm run dev      # Dev server on port 5173
npm run build    # Production build to dist/
npm run preview  # Preview production build
```

## Build

Production build outputs to `dist/` which is served by the backend as a SPA.
