/**
 * Kullanicinin hangi sayfada / urunde / kategoride oldugunu dondurur.
 * ChatPanel bunu page_context olarak API'ye gonderir.
 *
 * Strateji: URL search params + route params uzerinden context cikar.
 * State'e bagimlilik yok — gereksiz re-render riski minimum.
 */

import { useMemo } from 'react'
import { useLocation, useParams, useSearchParams } from 'react-router-dom'

export interface PageContext {
  page: string
  product_id?: string
  sku?: string
  product_name?: string
  platform?: string
  category_name?: string
  session_id?: string
  merchant_id?: string
  seller_name?: string
  keyword?: string
  filters?: Record<string, string>
}

export interface SuggestedPrompt {
  text: string
}

/** String'i 100 karakterle kisalt — context label'lar icin */
function truncate(val: string | null | undefined, max = 100): string | undefined {
  if (!val) return undefined
  return val.length > max ? val.slice(0, max) : val
}

export function useChatContext(): {
  context: PageContext | null
  suggestions: SuggestedPrompt[]
} {
  const location = useLocation()
  const params = useParams()
  const [searchParams] = useSearchParams()

  // useMemo ile gereksiz re-render once al — searchParams degismedikce hesaplama yapma
  return useMemo(() => {
    const path = location.pathname

    // ------------------------------------------------------------------
    // Price Monitor: /price-monitor
    // URL params: platform yok (state icinde), selectedProduct state icinde
    // En azindan platform'u sessionStorage'dan oku (usePriceMonitor burada yazar)
    // ------------------------------------------------------------------
    if (path.includes('/price-monitor')) {
      // PriceMonitor platform bilgisini URL'e yazmaz; URL'de yoksa
      // window.location'a bakariz ama SSR yoksa dogrudan okuyabiliriz.
      // Guclu alternatif: sessionStorage fallback (kullanici onceden girdiyse)
      const platform = truncate(searchParams.get('platform'))

      const context: PageContext = {
        page: 'price_monitor',
        ...(platform && { platform }),
      }

      const suggestions: SuggestedPrompt[] = platform
        ? [
            { text: `${platform === 'hepsiburada' ? 'HB' : 'TY'} urunlerimde fiyat alarmi var mi?` },
            { text: 'En cok fiyat degisen urunum hangisi?' },
            { text: 'Portfolyomun genel durumu nedir?' },
          ]
        : [
            { text: 'Hangi urunlerimde fiyat alarmi var?' },
            { text: 'En cok fiyat degisen urunum hangisi?' },
            { text: 'Portfolyomun genel durumu nedir?' },
          ]

      return { context, suggestions }
    }

    // ------------------------------------------------------------------
    // Dashboard: /
    // ------------------------------------------------------------------
    if (path === '/') {
      return {
        context: { page: 'dashboard' },
        suggestions: [
          { text: 'Bugun kac alarm tetiklendi?' },
          { text: 'En riskli urunum hangisi?' },
          { text: 'En karli urunum hangisi?' },
        ],
      }
    }

    // ------------------------------------------------------------------
    // Category Explorer: /category-explorer
    // URL params: platform, category, view, catBrand, catSeller
    // useCategoryExplorer hook'u bunlari URL'e sync ediyor
    // ------------------------------------------------------------------
    if (path.includes('/category-explorer') || path.includes('/category')) {
      const platform = truncate(searchParams.get('platform'))
      const categoryName = truncate(searchParams.get('category'))
      const sessionId = truncate(searchParams.get('session_id'))
      const catBrand = truncate(searchParams.get('catBrand'))
      const catSeller = truncate(searchParams.get('catSeller'))

      // Aktif filtreler varsa filters objesine ekle
      const filters: Record<string, string> = {}
      if (catBrand) filters.brand = catBrand
      if (catSeller) filters.seller = catSeller

      const context: PageContext = {
        page: 'category_explorer',
        ...(platform && { platform }),
        ...(categoryName && { category_name: categoryName }),
        ...(sessionId && { session_id: sessionId }),
        ...(Object.keys(filters).length > 0 && { filters }),
      }

      // Dinamik suggestions — kategori biliniyorsa spesifik sor
      const suggestions: SuggestedPrompt[] = categoryName
        ? [
            { text: `${categoryName} kategorisindeki en ucuz 5 urun nedir?` },
            { text: `${categoryName} kategorisinde ortalama fiyat nedir?` },
            { text: `${categoryName} kategorisinde hangi marka one cikiyor?` },
          ]
        : [
            { text: 'Bu kategorideki ortalama fiyat nedir?' },
            { text: 'En cok satan markalar hangileri?' },
            { text: 'Hangi kategori daha karli?' },
          ]

      return { context, suggestions }
    }

    // ------------------------------------------------------------------
    // Seller Detail: /sellers/:merchantId
    // Route param: merchantId
    // URL params: platform
    // ------------------------------------------------------------------
    if (path.includes('/sellers') && params.merchantId) {
      const merchantId = truncate(params.merchantId)
      const platform = truncate(searchParams.get('platform'))
      // SellerDetail sayfasi merchantName'i state'te tutuyor — URL'de yok
      // Sadece merchant_id ve platform gonderiyoruz

      const context: PageContext = {
        page: 'seller_detail',
        ...(merchantId && { merchant_id: merchantId }),
        ...(platform && { platform }),
      }

      return {
        context,
        suggestions: [
          { text: 'Bu saticinin fiyat stratejisi nasil?' },
          { text: 'Bu saticiyla hangi urunlerde rekabet ediyorum?' },
          { text: 'Bu saticinin en cok satan urunleri neler?' },
        ],
      }
    }

    // ------------------------------------------------------------------
    // Sellers List: /sellers
    // URL params: platform
    // ------------------------------------------------------------------
    if (path.includes('/sellers')) {
      const platform = truncate(searchParams.get('platform'))

      const context: PageContext = {
        page: 'sellers',
        ...(platform && { platform }),
      }

      return {
        context,
        suggestions: [
          { text: 'En aktif rakip saticim kim?' },
          { text: 'Hangi saticilar fiyat kirdi?' },
          {
            text: platform
              ? `${platform === 'hepsiburada' ? 'HB' : 'TY'} platformunda kac rakip saticim var?`
              : 'Kac rakip saticim var?',
          },
        ],
      }
    }

    // ------------------------------------------------------------------
    // Keyword Search: /search veya /keyword-search
    // URL params: q, keyword
    // ------------------------------------------------------------------
    if (path.includes('/search') || path.includes('/keyword-search')) {
      const keyword = truncate(
        searchParams.get('q') || searchParams.get('keyword'),
      )
      const platform = truncate(searchParams.get('platform'))

      const context: PageContext = {
        page: 'keyword_search',
        ...(keyword && { keyword }),
        ...(platform && { platform }),
      }

      const suggestions: SuggestedPrompt[] = keyword
        ? [
            { text: `"${keyword}" aramasinda rakiplerim kimler?` },
            { text: `"${keyword}" keyword'unde ilk sayfaya girmek ne kadar zorlu?` },
            { text: `"${keyword}" icin optimize fiyat ne olmali?` },
          ]
        : [
            { text: 'Hangi keyword\'lerde daha iyi siralamam var?' },
            { text: 'Rakiplerimin keyword stratejisi nedir?' },
            { text: 'Hangi keyword\'de fiyat avantajim var?' },
          ]

      return { context, suggestions }
    }

    // ------------------------------------------------------------------
    // Genel fallback
    // ------------------------------------------------------------------
    return {
      context: null,
      suggestions: [
        { text: 'Fiyat alarmi olan urunlerim hangileri?' },
        { text: 'En karli urunum hangisi?' },
        { text: 'Rakiplerimin fiyat durumu nasil?' },
      ],
    }
  }, [location.pathname, params.merchantId, searchParams])
}
