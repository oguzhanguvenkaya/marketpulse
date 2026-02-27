import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/client'

interface SubscriptionInfo {
  plan_tier: string
  status: string
  sku_limit: number
  scan_frequency: number
  current_sku_count: number
  stripe_subscription_id: string | null
  created_at: string | null
}

interface PlanInfo {
  tier: string
  name: string
  price_monthly: number | null
  currency: string
  features: string[]
}

const PLAN_LABELS: Record<string, string> = {
  free: 'Ucretsiz',
  starter: 'Starter',
  pro: 'Pro',
  enterprise: 'Enterprise',
}

export default function Settings() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<'profile' | 'subscription' | 'alerts'>('profile')
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [plans, setPlans] = useState<PlanInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [upgradeLoading, setUpgradeLoading] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const [subRes, plansRes] = await Promise.all([
        api.get('/api/billing/subscription'),
        api.get('/api/billing/plans'),
      ])
      setSubscription(subRes.data)
      setPlans(plansRes.data.plans || [])
    } catch {
      // Billing henuz hazir degilse sessizce devam et
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleUpgrade = async (tier: string) => {
    setUpgradeLoading(tier)
    try {
      const origin = window.location.origin
      const res = await api.post('/api/billing/checkout', {
        plan_tier: tier,
        success_url: `${origin}/settings?payment=success`,
        cancel_url: `${origin}/settings?payment=canceled`,
      })
      if (res.data.checkout_url) {
        window.location.href = res.data.checkout_url
      }
    } catch {
      alert('Odeme sayfasi olusturulamadi. Lutfen tekrar deneyin.')
    } finally {
      setUpgradeLoading(null)
    }
  }

  const handleManageBilling = async () => {
    try {
      const res = await api.post('/api/billing/portal', {
        return_url: `${window.location.origin}/settings`,
      })
      if (res.data.portal_url) {
        window.location.href = res.data.portal_url
      }
    } catch {
      alert('Fatura portali acilamadi.')
    }
  }

  const tabs = [
    { id: 'profile' as const, label: 'Profil' },
    { id: 'subscription' as const, label: 'Abonelik' },
    { id: 'alerts' as const, label: 'Bildirimler' },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-xl font-bold text-[#3a2d14] dark:text-[#F0FDF4] mb-6">Ayarlar</h2>

      {/* Tab navigation */}
      <div className="flex gap-1 mb-6 bg-[#f5f0e8] dark:bg-[#162420] rounded-xl p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-white dark:bg-[#1A2F28] text-[#3a2d14] dark:text-[#F0FDF4] shadow-sm'
                : 'text-[#7a6b4e] dark:text-[#6B8F80] hover:text-[#3a2d14] dark:hover:text-[#F0FDF4]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="bg-white dark:bg-[#1A2F28] rounded-2xl border border-[#e8e0d4] dark:border-[#2A3F38] p-6">
          <h3 className="text-lg font-semibold text-[#3a2d14] dark:text-[#F0FDF4] mb-4">Profil Bilgileri</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#7a6b4e] dark:text-[#6B8F80] mb-1">Email</label>
              <p className="text-[#3a2d14] dark:text-[#F0FDF4]">{user?.email || '-'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#7a6b4e] dark:text-[#6B8F80] mb-1">Ad Soyad</label>
              <p className="text-[#3a2d14] dark:text-[#F0FDF4]">
                {user?.user_metadata?.full_name || 'Belirtilmemis'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#7a6b4e] dark:text-[#6B8F80] mb-1">Plan</label>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-[#f5f0e8] dark:bg-[#162420] text-[#5f471d] dark:text-[#4ADE80]">
                {PLAN_LABELS[subscription?.plan_tier || 'free'] || 'Ucretsiz'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Subscription Tab */}
      {activeTab === 'subscription' && (
        <div className="space-y-6">
          {/* Current plan */}
          {subscription && (
            <div className="bg-white dark:bg-[#1A2F28] rounded-2xl border border-[#e8e0d4] dark:border-[#2A3F38] p-6">
              <h3 className="text-lg font-semibold text-[#3a2d14] dark:text-[#F0FDF4] mb-4">Mevcut Plan</h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-[#3a2d14] dark:text-[#F0FDF4]">
                    {PLAN_LABELS[subscription.plan_tier] || subscription.plan_tier}
                  </p>
                  <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80] mt-1">
                    {subscription.current_sku_count} / {subscription.sku_limit} SKU kullaniliyor
                  </p>
                </div>
                <div className="text-right">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    subscription.status === 'active'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                  }`}>
                    {subscription.status === 'active' ? 'Aktif' : subscription.status}
                  </span>
                </div>
              </div>
              {/* Usage bar */}
              <div className="mt-4">
                <div className="w-full bg-[#f5f0e8] dark:bg-[#162420] rounded-full h-2">
                  <div
                    className="bg-[#5f471d] dark:bg-[#4ADE80] h-2 rounded-full transition-all"
                    style={{ width: `${Math.min((subscription.current_sku_count / subscription.sku_limit) * 100, 100)}%` }}
                  />
                </div>
              </div>
              {subscription.stripe_subscription_id && (
                <button
                  onClick={handleManageBilling}
                  className="mt-4 text-sm text-[#5f471d] dark:text-[#4ADE80] hover:underline"
                >
                  Fatura ve odeme yonetimi →
                </button>
              )}
            </div>
          )}

          {/* Plan cards */}
          {!loading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {plans.map((plan) => {
                const isCurrent = subscription?.plan_tier === plan.tier
                const isUpgrade = !isCurrent && plan.tier !== 'free'
                return (
                  <div
                    key={plan.tier}
                    className={`rounded-2xl border p-5 ${
                      isCurrent
                        ? 'border-[#5f471d] dark:border-[#4ADE80] bg-[#faf8f5] dark:bg-[#162420]'
                        : 'border-[#e8e0d4] dark:border-[#2A3F38] bg-white dark:bg-[#1A2F28]'
                    }`}
                  >
                    <h4 className="font-semibold text-[#3a2d14] dark:text-[#F0FDF4]">{plan.name}</h4>
                    <p className="text-2xl font-bold text-[#3a2d14] dark:text-[#F0FDF4] mt-2">
                      {plan.price_monthly != null ? `${plan.price_monthly} TL` : 'Iletisime gecin'}
                      {plan.price_monthly != null && plan.price_monthly > 0 && (
                        <span className="text-sm font-normal text-[#7a6b4e] dark:text-[#6B8F80]">/ay</span>
                      )}
                    </p>
                    <ul className="mt-4 space-y-2">
                      {plan.features.map((f, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-[#7a6b4e] dark:text-[#6B8F80]">
                          <svg className="w-4 h-4 text-[#5f471d] dark:text-[#4ADE80] flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          {f}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-4">
                      {isCurrent ? (
                        <span className="block text-center py-2 text-sm font-medium text-[#7a6b4e] dark:text-[#6B8F80]">
                          Mevcut plan
                        </span>
                      ) : isUpgrade ? (
                        <button
                          onClick={() => handleUpgrade(plan.tier)}
                          disabled={upgradeLoading === plan.tier}
                          className="w-full py-2 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold text-sm hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors disabled:opacity-50"
                        >
                          {upgradeLoading === plan.tier ? 'Yonlendiriliyor...' : 'Yukselt'}
                        </button>
                      ) : null}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Alerts Tab */}
      {activeTab === 'alerts' && (
        <div className="bg-white dark:bg-[#1A2F28] rounded-2xl border border-[#e8e0d4] dark:border-[#2A3F38] p-6">
          <h3 className="text-lg font-semibold text-[#3a2d14] dark:text-[#F0FDF4] mb-4">Bildirim Tercihleri</h3>
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-[#3a2d14] dark:text-[#F0FDF4]">Email Bildirimleri</p>
                <p className="text-xs text-[#7a6b4e] dark:text-[#6B8F80]">Fiyat degisimi ve buybox uyarilari</p>
              </div>
              <input
                type="checkbox"
                defaultChecked
                className="w-5 h-5 rounded accent-[#5f471d] dark:accent-[#4ADE80]"
              />
            </label>
            <label className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-[#3a2d14] dark:text-[#F0FDF4]">Kampanya Uyarilari</p>
                <p className="text-xs text-[#7a6b4e] dark:text-[#6B8F80]">Rakip kampanyaya girdiginde bildirim</p>
              </div>
              <input
                type="checkbox"
                defaultChecked
                className="w-5 h-5 rounded accent-[#5f471d] dark:accent-[#4ADE80]"
              />
            </label>
            <label className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-[#3a2d14] dark:text-[#F0FDF4]">Gunluk Ozet</p>
                <p className="text-xs text-[#7a6b4e] dark:text-[#6B8F80]">Her gun sabah ozet email</p>
              </div>
              <input
                type="checkbox"
                className="w-5 h-5 rounded accent-[#5f471d] dark:accent-[#4ADE80]"
              />
            </label>
          </div>
        </div>
      )}
    </div>
  )
}
