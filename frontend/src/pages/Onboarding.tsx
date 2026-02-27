import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/client'

type Step = 'welcome' | 'platform' | 'add-sku' | 'threshold' | 'scan' | 'done'

export default function Onboarding() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('welcome')
  const [platform, setPlatform] = useState<'hepsiburada' | 'trendyol'>('hepsiburada')
  const [sku, setSku] = useState('')
  const [threshold, setThreshold] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [addedProduct, setAddedProduct] = useState<{ id: string; name: string } | null>(null)
  const [scanResult, setScanResult] = useState<{ success: boolean; message: string } | null>(null)

  const steps: { key: Step; label: string }[] = [
    { key: 'welcome', label: 'Hosgeldin' },
    { key: 'platform', label: 'Platform' },
    { key: 'add-sku', label: 'Ilk SKU' },
    { key: 'threshold', label: 'Esik Deger' },
    { key: 'scan', label: 'Tarama' },
    { key: 'done', label: 'Tamam' },
  ]

  const currentIndex = steps.findIndex((s) => s.key === step)

  const handleAddSku = async () => {
    if (!sku.trim()) {
      setError('SKU girin')
      return
    }
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/api/price-monitor/products', {
        platform,
        products: [{ sku: sku.trim() }],
      })
      if (res.data.added > 0 || res.data.updated > 0) {
        setAddedProduct({
          id: res.data.results?.[0]?.id || '',
          name: res.data.results?.[0]?.product_name || sku,
        })
        setStep('threshold')
      } else {
        setError('Urun eklenemedi. Lutfen SKU\'yu kontrol edin.')
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Urun eklenirken hata olustu')
    } finally {
      setLoading(false)
    }
  }

  const handleSetThreshold = async () => {
    if (threshold && addedProduct?.id) {
      try {
        await api.patch(`/api/price-monitor/products/${addedProduct.id}`, {
          threshold_price: parseFloat(threshold.replace(',', '.')),
        })
      } catch {
        // Threshold kaydetme opsiyonel, hata durumunda devam et
      }
    }
    setStep('scan')
  }

  const handleScan = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.post(`/api/price-monitor/fetch?platform=${platform}`)
      setScanResult({ success: true, message: res.data.message || 'Tarama baslatildi!' })
    } catch (err: any) {
      setScanResult({
        success: false,
        message: err?.response?.data?.detail || 'Tarama baslatilirken hata olustu',
      })
    } finally {
      setLoading(false)
      setStep('done')
    }
  }

  const finishOnboarding = () => {
    localStorage.setItem('mp_onboarding_done', '1')
    navigate('/price-monitor')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#faf8f5] to-[#f0ece4] dark:from-[#0F1A17] dark:to-[#162420] p-4">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {steps.map((s, i) => (
            <div key={s.key} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  i <= currentIndex
                    ? 'bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17]'
                    : 'bg-[#e8e0d4] dark:bg-[#2A3F38] text-[#7a6b4e] dark:text-[#6B8F80]'
                }`}
              >
                {i < currentIndex ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              {i < steps.length - 1 && (
                <div
                  className={`w-6 h-0.5 ${
                    i < currentIndex ? 'bg-[#5f471d] dark:bg-[#4ADE80]' : 'bg-[#e8e0d4] dark:bg-[#2A3F38]'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-[#1A2F28] rounded-2xl shadow-lg border border-[#e8e0d4] dark:border-[#2A3F38] p-8">
          {/* Welcome */}
          {step === 'welcome' && (
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl brand-mark flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-[#3a2d14] dark:text-[#F0FDF4] mb-2">
                MarketPulse'a Hosgeldiniz!
              </h2>
              <p className="text-[#7a6b4e] dark:text-[#6B8F80] mb-6">
                Pazaryeri fiyat takibini 2 dakikada kurun. Rakiplerinizi izleyin, fiyat degisimlerinden aninda haberdar olun.
              </p>
              <button
                onClick={() => setStep('platform')}
                className="w-full py-3 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors"
              >
                Baslayalim
              </button>
            </div>
          )}

          {/* Platform Selection */}
          {step === 'platform' && (
            <div>
              <h2 className="text-xl font-bold text-[#3a2d14] dark:text-[#F0FDF4] mb-2">
                Hangi platformda satiyorsunuz?
              </h2>
              <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80] mb-6">
                Daha sonra diger platformlari da ekleyebilirsiniz.
              </p>
              <div className="grid grid-cols-2 gap-3 mb-6">
                {(['hepsiburada', 'trendyol'] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPlatform(p)}
                    className={`py-4 px-4 rounded-xl border-2 font-semibold transition-all ${
                      platform === p
                        ? 'border-[#5f471d] dark:border-[#4ADE80] bg-[#faf8f5] dark:bg-[#162420] text-[#3a2d14] dark:text-[#F0FDF4]'
                        : 'border-[#e8e0d4] dark:border-[#2A3F38] text-[#7a6b4e] dark:text-[#6B8F80] hover:border-[#d4c9b5] dark:hover:border-[#3A5048]'
                    }`}
                  >
                    {p === 'hepsiburada' ? 'Hepsiburada' : 'Trendyol'}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setStep('add-sku')}
                className="w-full py-3 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors"
              >
                Devam Et
              </button>
            </div>
          )}

          {/* Add First SKU */}
          {step === 'add-sku' && (
            <div>
              <h2 className="text-xl font-bold text-[#3a2d14] dark:text-[#F0FDF4] mb-2">
                Ilk urunuzu ekleyin
              </h2>
              <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80] mb-6">
                {platform === 'hepsiburada' ? 'Hepsiburada' : 'Trendyol'} urun SKU kodunu girin.
                URL'den veya urun sayfasindan bulabilirsiniz.
              </p>

              {error && (
                <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}

              <input
                type="text"
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                placeholder={platform === 'hepsiburada' ? 'Ornek: HBV00001ABC12' : 'Ornek: 123456789'}
                className="w-full px-4 py-3 rounded-xl border border-[#d4c9b5] dark:border-[#2A3F38] bg-[#faf8f5] dark:bg-[#0F1A17] text-[#3a2d14] dark:text-[#F0FDF4] text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-[#5f471d]/30 dark:focus:ring-[#4ADE80]/30"
                onKeyDown={(e) => e.key === 'Enter' && handleAddSku()}
              />

              <div className="flex gap-3">
                <button
                  onClick={() => setStep('platform')}
                  className="flex-1 py-3 rounded-xl border border-[#d4c9b5] dark:border-[#2A3F38] text-[#7a6b4e] dark:text-[#6B8F80] font-semibold hover:bg-[#f5f0e8] dark:hover:bg-[#162420] transition-colors"
                >
                  Geri
                </button>
                <button
                  onClick={handleAddSku}
                  disabled={loading}
                  className="flex-1 py-3 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Ekleniyor...' : 'Urun Ekle'}
                </button>
              </div>

              <button
                onClick={() => {
                  setStep('threshold')
                  setAddedProduct(null)
                }}
                className="w-full mt-3 text-sm text-[#7a6b4e] dark:text-[#6B8F80] hover:underline"
              >
                Simdilik atla, sonra ekleyecegim
              </button>
            </div>
          )}

          {/* Threshold */}
          {step === 'threshold' && (
            <div>
              <h2 className="text-xl font-bold text-[#3a2d14] dark:text-[#F0FDF4] mb-2">
                Fiyat esik degerini belirleyin
              </h2>
              <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80] mb-6">
                Rakip fiyati bu degerin altina dustugunde sizi uyaralim.
                {addedProduct?.name && (
                  <span className="block mt-1 font-medium text-[#3a2d14] dark:text-[#F0FDF4]">
                    Urun: {addedProduct.name}
                  </span>
                )}
              </p>

              <div className="relative mb-4">
                <input
                  type="text"
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                  placeholder="Ornek: 99.90"
                  className="w-full px-4 py-3 pr-10 rounded-xl border border-[#d4c9b5] dark:border-[#2A3F38] bg-[#faf8f5] dark:bg-[#0F1A17] text-[#3a2d14] dark:text-[#F0FDF4] text-sm focus:outline-none focus:ring-2 focus:ring-[#5f471d]/30 dark:focus:ring-[#4ADE80]/30"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[#7a6b4e] dark:text-[#6B8F80] text-sm">TL</span>
              </div>

              <button
                onClick={handleSetThreshold}
                className="w-full py-3 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors"
              >
                Devam Et
              </button>

              <button
                onClick={() => setStep('scan')}
                className="w-full mt-3 text-sm text-[#7a6b4e] dark:text-[#6B8F80] hover:underline"
              >
                Atla
              </button>
            </div>
          )}

          {/* Scan */}
          {step === 'scan' && (
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-[#f5f0e8] dark:bg-[#162420] flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-[#5f471d] dark:text-[#4ADE80]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-[#3a2d14] dark:text-[#F0FDF4] mb-2">
                Ilk taramayi baslatin
              </h2>
              <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80] mb-6">
                Urunlerinizin guncel satici fiyatlarini cekmeye hazirsiniz.
                Tarama birkaç dakika surebilir.
              </p>

              <button
                onClick={handleScan}
                disabled={loading}
                className="w-full py-3 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors disabled:opacity-50"
              >
                {loading ? 'Baslatiliyor...' : 'Simdi Tara'}
              </button>

              <button
                onClick={() => setStep('done')}
                className="w-full mt-3 text-sm text-[#7a6b4e] dark:text-[#6B8F80] hover:underline"
              >
                Sonra tararim
              </button>
            </div>
          )}

          {/* Done */}
          {step === 'done' && (
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-[#3a2d14] dark:text-[#F0FDF4] mb-2">
                Hazirsaniz!
              </h2>
              <p className="text-[#7a6b4e] dark:text-[#6B8F80] mb-2">
                MarketPulse kurulumunuz tamamlandi.
              </p>
              {scanResult && (
                <p className={`text-sm mb-4 ${scanResult.success ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {scanResult.message}
                </p>
              )}
              <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80] mb-6">
                Dashboard'da urunlerinizi takip edebilir, daha fazla SKU ekleyebilir
                ve alarm tercihlerinizi ayarlayabilirsiniz.
              </p>

              <button
                onClick={finishOnboarding}
                className="w-full py-3 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors"
              >
                Dashboard'a Git
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
