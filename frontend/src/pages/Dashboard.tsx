import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Link } from 'react-router-dom'
import api from '../services/client'
import { useAuth } from '../contexts/AuthContext'

interface DashboardSummary {
  sku_overview: {
    total: number
    limit: number
    usage_percent: number
    by_platform: Record<string, number>
  }
  alerts: {
    today_count: number
    threshold_violations: Array<{
      product_id: string
      product_name: string
      sku: string
      platform: string
      current_price: number
      threshold_price: number
      seller: string
    }>
  }
  plan: { tier: string; sku_limit: number }
  last_scan: { at: string | null; next: string | null }
  recent_searches: Array<{
    keyword: string
    platform: string
    products: number
    date: string
  }>
}

interface PriceMovers {
  price_drops: PriceMover[]
  price_increases: PriceMover[]
}

interface PriceMover {
  product_id: string
  product_name: string
  sku: string
  platform: string
  old_price: number
  new_price: number
  change_percent: number
  direction: string
}

interface ProfitabilityOverview {
  total_products_with_cost: number
  profitable_count: number
  losing_count: number
  top_profitable: ProfitItem[]
  top_losing: ProfitItem[]
}

interface ProfitItem {
  product_id: string
  product_name: string
  sku: string
  sale_price: number
  net_profit: number
  margin_percent: number
  profitable: boolean
}

const PLAN_LABELS: Record<string, string> = {
  free: 'Ucretsiz',
  starter: 'Starter',
  pro: 'Pro',
  enterprise: 'Enterprise',
}

export default function Dashboard() {
  const { user } = useAuth()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [movers, setMovers] = useState<PriceMovers | null>(null)
  const [profitability, setProfitability] = useState<ProfitabilityOverview | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    setLoading(true)
    try {
      const [summaryRes, moversRes, profitRes] = await Promise.allSettled([
        api.get('/api/dashboard/summary'),
        api.get('/api/dashboard/price-movers'),
        api.get('/api/dashboard/profitability-overview'),
      ])
      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value.data)
      if (moversRes.status === 'fulfilled') setMovers(moversRes.value.data)
      if (profitRes.status === 'fulfilled') setProfitability(profitRes.value.data)
    } catch {
      toast.error('Dashboard verileri yuklenemedi', { id: 'dashboard-error' })
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-5 animate-pulse">
        <div className="h-8 bg-[var(--surface-raised)] rounded w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-28 bg-[var(--surface-raised)] rounded-xl" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="h-64 bg-[var(--surface-raised)] rounded-xl" />
          <div className="h-64 bg-[var(--surface-raised)] rounded-xl" />
        </div>
      </div>
    )
  }

  const tier = summary?.plan?.tier || 'free'

  return (
    <div className="space-y-5 md:space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-text-primary">
            Merhaba{user?.user_metadata?.full_name ? `, ${user.user_metadata.full_name}` : ''}
          </h1>
          <p className="text-sm text-text-muted mt-1">Bugunun ozeti</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          tier === 'pro' ? 'bg-violet-500/10 text-violet-400' :
          tier === 'starter' ? 'bg-blue-500/10 text-blue-400' :
          tier === 'enterprise' ? 'bg-amber-500/10 text-amber-400' :
          'bg-gray-500/10 text-gray-400'
        }`}>
          {PLAN_LABELS[tier] || tier}
        </span>
      </div>

      {/* Top Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {/* SKU Kullanimi */}
        <div className="card-dark p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-text-muted text-xs">SKU Kullanimi</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
          </div>
          <div className="text-2xl font-bold text-text-primary">
            {summary?.sku_overview?.total || 0}
            <span className="text-sm text-text-muted font-normal"> / {summary?.sku_overview?.limit || 10}</span>
          </div>
          <div className="mt-2 h-1.5 bg-[var(--surface-base)] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all bg-blue-500"
              style={{ width: `${Math.min(summary?.sku_overview?.usage_percent || 0, 100)}%` }}
            />
          </div>
          {summary?.sku_overview?.by_platform && Object.keys(summary.sku_overview.by_platform).length > 0 && (
            <div className="mt-2 flex gap-3 text-[10px] text-text-muted">
              {Object.entries(summary.sku_overview.by_platform).map(([p, c]) => (
                <span key={p} className="capitalize">{p}: {c}</span>
              ))}
            </div>
          )}
        </div>

        {/* Fiyat Alarmlari */}
        <div className="card-dark p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-text-muted text-xs">Bugunun Alarmlari</span>
            <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
          </div>
          <div className="text-2xl font-bold text-text-primary">{summary?.alerts?.today_count || 0}</div>
          <p className="text-[10px] text-text-muted mt-1">
            {(summary?.alerts?.threshold_violations?.length || 0)} esik ihlali
          </p>
        </div>

        {/* Son Tarama */}
        <div className="card-dark p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-text-muted text-xs">Son Tarama</span>
            <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
          </div>
          <div className="text-sm font-medium text-text-primary">
            {summary?.last_scan?.at
              ? new Date(summary.last_scan.at).toLocaleString('tr-TR', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })
              : 'Henuz tarama yok'}
          </div>
          {summary?.last_scan?.next && (
            <p className="text-[10px] text-text-muted mt-1">
              Sonraki: {new Date(summary.last_scan.next).toLocaleString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
            </p>
          )}
        </div>

        {/* Karlilik */}
        <div className="card-dark p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-text-muted text-xs">Karlilik</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold text-green-400">{profitability?.profitable_count || 0}</span>
            <span className="text-text-muted text-xs">karli</span>
            <span className="text-lg font-bold text-red-400 ml-2">{profitability?.losing_count || 0}</span>
            <span className="text-text-muted text-xs">zararda</span>
          </div>
          <p className="text-[10px] text-text-muted mt-1">
            {profitability?.total_products_with_cost || 0} maliyet girilmis urun
          </p>
        </div>
      </div>

      {/* Threshold Violations Alert */}
      {summary?.alerts?.threshold_violations && summary.alerts.threshold_violations.length > 0 && (
        <div className="card-dark border-l-4 border-l-red-500 p-4">
          <div className="flex items-center gap-2 mb-3">
            <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h3 className="text-sm font-semibold text-red-400">Esik Ihlalleri</h3>
          </div>
          <div className="space-y-2">
            {summary.alerts.threshold_violations.slice(0, 5).map(v => (
              <Link
                key={v.product_id}
                to={`/price-monitor`}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-[var(--surface-hover)] transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-text-primary truncate">{v.product_name || v.sku}</div>
                  <div className="text-[10px] text-text-muted">{v.seller} - {v.platform}</div>
                </div>
                <div className="text-right ml-3">
                  <div className="text-sm font-medium text-red-400">{v.current_price.toFixed(2)} TL</div>
                  <div className="text-[10px] text-text-muted line-through">{v.threshold_price.toFixed(2)} TL esik</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Price Movers */}
        <div className="card-dark overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--surface-border)] flex items-center gap-2">
            <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <h2 className="text-sm font-semibold text-text-primary">Fiyat Hareketleri (7 gun)</h2>
          </div>
          <div className="p-4">
            {(!movers || (movers.price_drops.length === 0 && movers.price_increases.length === 0)) ? (
              <p className="text-text-muted text-sm text-center py-6">Henuz fiyat degisimi yok</p>
            ) : (
              <div className="space-y-3">
                {/* Drops */}
                {movers.price_drops.slice(0, 5).map(m => (
                  <div key={m.product_id} className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-text-primary truncate">{m.product_name || m.sku}</div>
                      <div className="text-[10px] text-text-muted capitalize">{m.platform}</div>
                    </div>
                    <div className="text-right ml-3">
                      <div className="text-sm font-medium text-red-400">{m.change_percent.toFixed(1)}%</div>
                      <div className="text-[10px] text-text-muted">{m.old_price.toFixed(0)} → {m.new_price.toFixed(0)} TL</div>
                    </div>
                  </div>
                ))}
                {/* Increases */}
                {movers.price_increases.slice(0, 3).map(m => (
                  <div key={m.product_id} className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-text-primary truncate">{m.product_name || m.sku}</div>
                      <div className="text-[10px] text-text-muted capitalize">{m.platform}</div>
                    </div>
                    <div className="text-right ml-3">
                      <div className="text-sm font-medium text-green-400">+{m.change_percent.toFixed(1)}%</div>
                      <div className="text-[10px] text-text-muted">{m.old_price.toFixed(0)} → {m.new_price.toFixed(0)} TL</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Profitability Overview */}
        <div className="card-dark overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--surface-border)] flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2 className="text-sm font-semibold text-text-primary">Karlilik Ozeti</h2>
          </div>
          <div className="p-4">
            {(!profitability || profitability.total_products_with_cost === 0) ? (
              <div className="text-center py-6">
                <p className="text-text-muted text-sm">Maliyet bilgisi girilmis urun yok</p>
                <Link to="/price-monitor" className="text-accent-primary text-xs mt-1 inline-block hover:underline">
                  Price Monitor'a git →
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {profitability.top_profitable.map(p => (
                  <div key={p.product_id} className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-text-primary truncate">{p.product_name || p.sku}</div>
                      <div className="text-[10px] text-text-muted">{p.sale_price.toFixed(0)} TL satis</div>
                    </div>
                    <div className="text-right ml-3">
                      <div className="text-sm font-medium text-green-400">+{p.net_profit.toFixed(0)} TL</div>
                      <div className="text-[10px] text-text-muted">%{p.margin_percent.toFixed(1)} marj</div>
                    </div>
                  </div>
                ))}
                {profitability.top_losing.map(p => (
                  <div key={p.product_id} className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-text-primary truncate">{p.product_name || p.sku}</div>
                      <div className="text-[10px] text-text-muted">{p.sale_price.toFixed(0)} TL satis</div>
                    </div>
                    <div className="text-right ml-3">
                      <div className="text-sm font-medium text-red-400">{p.net_profit.toFixed(0)} TL</div>
                      <div className="text-[10px] text-text-muted">%{p.margin_percent.toFixed(1)} marj</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Searches */}
      <div className="card-dark overflow-hidden">
        <div className="px-4 py-3 border-b border-[var(--surface-border)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <h2 className="text-sm font-semibold text-text-primary">Son Aramalar</h2>
          </div>
          <Link to="/products" className="text-accent-primary text-xs hover:underline">Tumu →</Link>
        </div>
        <div className="divide-y divide-[var(--surface-border)]">
          {(!summary?.recent_searches || summary.recent_searches.length === 0) ? (
            <div className="p-6 text-center text-text-muted text-sm">Henuz arama yapilmamis</div>
          ) : (
            summary.recent_searches.map((s, i) => (
              <div key={i} className="px-4 py-3 flex items-center justify-between hover:bg-[var(--surface-hover)] transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[var(--surface-base)] flex items-center justify-center">
                    <svg className="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <div>
                    <div className="text-sm text-text-primary font-medium">{s.keyword}</div>
                    <div className="text-[10px] text-text-muted capitalize">{s.platform} - {new Date(s.date).toLocaleDateString('tr-TR')}</div>
                  </div>
                </div>
                <span className="text-xs text-text-muted">{s.products} urun</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Link to="/price-monitor" className="card-dark p-4 hover:bg-[var(--surface-hover)] transition-colors text-center">
          <svg className="w-6 h-6 text-blue-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
          <span className="text-xs text-text-primary">Price Monitor</span>
        </Link>
        <Link to="/products" className="card-dark p-4 hover:bg-[var(--surface-hover)] transition-colors text-center">
          <svg className="w-6 h-6 text-yellow-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <span className="text-xs text-text-primary">Keyword Arama</span>
        </Link>
        <Link to="/sellers" className="card-dark p-4 hover:bg-[var(--surface-hover)] transition-colors text-center">
          <svg className="w-6 h-6 text-purple-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
          </svg>
          <span className="text-xs text-text-primary">Saticilar</span>
        </Link>
        <Link to="/settings" className="card-dark p-4 hover:bg-[var(--surface-hover)] transition-colors text-center">
          <svg className="w-6 h-6 text-gray-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-xs text-text-primary">Ayarlar</span>
        </Link>
      </div>
    </div>
  )
}
