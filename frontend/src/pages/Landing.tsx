import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

// --- SVG Icons ---

function IconTrendUp() {
  return (
    <svg
      className="w-6 h-6"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
    </svg>
  )
}

function IconUsersCompare() {
  return (
    <svg
      className="w-6 h-6"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

function IconCalculator() {
  return (
    <svg
      className="w-6 h-6"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  )
}

function IconCheck() {
  return (
    <svg
      className="w-4 h-4 shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
    </svg>
  )
}

// --- Data ---

const features = [
  {
    icon: <IconTrendUp />,
    title: 'Price Monitor',
    description: "1000'lerce urunun fiyatini gunluk otomatik tarayin, anlik degisiklikleri kacirmayin.",
  },
  {
    icon: <IconUsersCompare />,
    title: 'Rakip Analizi',
    description: 'Buybox durumu, satici karsilastirma ve kampanya takibi tek panelde.',
  },
  {
    icon: <IconCalculator />,
    title: 'Karlilik Hesaplama',
    description: 'Her satis icin net kar hesaplayin, zarar riskini erkenden gorün.',
  },
]

const steps = [
  { number: '01', text: "Urun SKU'larini girin veya CSV yukleyin" },
  { number: '02', text: 'Otomatik tarama zamanlayici kurun' },
  { number: '03', text: 'Fiyat alarmlarini ve esikleri belirleyin' },
  { number: '04', text: 'AI destekli insights ile karar alin' },
]

interface PricingPlan {
  name: string
  price: string
  period: string | null
  features: string[]
  cta: string
  ctaHref: string
  popular: boolean
  enterprise: boolean
}

const pricingPlans: PricingPlan[] = [
  {
    name: 'Free',
    price: '0',
    period: null,
    features: ['10 SKU', 'Gunluk 1x manuel tarama', 'Temel fiyat takibi', 'Email destek'],
    cta: 'Ucretsiz Basla',
    ctaHref: '/register',
    popular: false,
    enterprise: false,
  },
  {
    name: 'Starter',
    price: '299',
    period: '/ay',
    features: ['200 SKU', 'Gunluk 2x otomatik tarama', 'Buybox takibi', 'Email + chat destek'],
    cta: 'Simdi Baslat',
    ctaHref: '/register',
    popular: false,
    enterprise: false,
  },
  {
    name: 'Pro',
    price: '899',
    period: '/ay',
    features: [
      '1000 SKU',
      'Gunluk 4x otomatik tarama',
      'Rakip & kampanya analizi',
      'AI insights',
      'Webhook alarmlar',
      'Oncelikli destek',
    ],
    cta: 'Pro ile Buyü',
    ctaHref: '/register',
    popular: true,
    enterprise: false,
  },
  {
    name: 'Enterprise',
    price: 'Ozel',
    period: null,
    features: [
      'Sinırsiz SKU',
      'Ozel tarama sikligi',
      'Coklu kullanici',
      'Ozel entegrasyonlar',
      'Dedicated destek',
      'SLA garantisi',
    ],
    cta: 'Iletisime Gecin',
    ctaHref: 'mailto:hello@marketpulse.io',
    popular: false,
    enterprise: true,
  },
]

// --- Components ---

function Navbar({ isLoggedIn }: { isLoggedIn: boolean }) {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#e8e0d4]/60 dark:border-[#2A3F38]/60 bg-[#faf8f5]/80 dark:bg-[#0F1A17]/80 backdrop-blur-md">
      <nav className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to={isLoggedIn ? '/' : '/landing'} className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg brand-mark flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <span className="font-bold text-[#3a2d14] dark:text-[#F0FDF4] text-lg tracking-tight">
            MarketPulse
          </span>
        </Link>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-6 text-sm font-medium text-[#7a6b4e] dark:text-[#6B8F80]">
          <a href="#features" className="hover:text-[#3a2d14] dark:hover:text-[#F0FDF4] transition-colors">
            Ozellikler
          </a>
          <a href="#how-it-works" className="hover:text-[#3a2d14] dark:hover:text-[#F0FDF4] transition-colors">
            Nasil Calisir
          </a>
          <a href="#pricing" className="hover:text-[#3a2d14] dark:hover:text-[#F0FDF4] transition-colors">
            Fiyatlar
          </a>
        </div>

        {/* CTA */}
        <div className="flex items-center gap-2.5">
          {isLoggedIn ? (
            <Link
              to="/"
              className="px-4 py-2 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] text-sm font-semibold hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors"
            >
              Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="px-4 py-2 rounded-xl text-sm font-semibold text-[#5f471d] dark:text-[#4ADE80] hover:bg-[#5f471d]/8 dark:hover:bg-[#4ADE80]/10 transition-colors"
              >
                Giris Yap
              </Link>
              <Link
                to="/register"
                className="px-4 py-2 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] text-sm font-semibold hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors"
              >
                Ucretsiz Basla
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}

function HeroSection({ isLoggedIn }: { isLoggedIn: boolean }) {
  return (
    <section className="pt-32 pb-20 px-4 sm:px-6 text-center">
      {/* Badge */}
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#5f471d]/10 dark:bg-[#4ADE80]/10 border border-[#5f471d]/20 dark:border-[#4ADE80]/20 mb-8">
        <span className="w-2 h-2 rounded-full bg-[#5f471d] dark:bg-[#4ADE80] animate-pulse" />
        <span className="text-xs font-semibold text-[#5f471d] dark:text-[#4ADE80] uppercase tracking-wider">
          Hepsiburada &amp; Trendyol destegi
        </span>
      </div>

      {/* Headline */}
      <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#3a2d14] dark:text-[#F0FDF4] max-w-3xl mx-auto leading-tight">
        Pazaryeri Fiyat Takibini{' '}
        <span className="text-[#5f471d] dark:text-[#4ADE80]">Otomatiklestirin</span>
      </h1>

      {/* Subheadline */}
      <p className="mt-6 text-lg sm:text-xl text-[#7a6b4e] dark:text-[#6B8F80] max-w-2xl mx-auto leading-relaxed">
        Hepsiburada ve Trendyol'da rakip fiyatlarini izleyin, buybox kazanin, karlilik analizi yapin.
      </p>

      {/* CTAs */}
      <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
        {isLoggedIn ? (
          <Link
            to="/"
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold text-base hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors shadow-lg shadow-[#5f471d]/20 dark:shadow-[#4ADE80]/20"
          >
            Dashboard'a Git
          </Link>
        ) : (
          <>
            <Link
              to="/register"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold text-base hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors shadow-lg shadow-[#5f471d]/20 dark:shadow-[#4ADE80]/20"
            >
              Ucretsiz Basla
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl border border-[#d4c9b5] dark:border-[#2A3F38] bg-white dark:bg-[#1A2F28] text-[#3a2d14] dark:text-[#F0FDF4] font-semibold text-base hover:bg-[#faf8f5] dark:hover:bg-[#1A2F28]/70 transition-colors"
            >
              Giris Yap
            </Link>
          </>
        )}
      </div>

      {/* Social proof */}
      <p className="mt-6 text-sm text-[#7a6b4e] dark:text-[#6B8F80]">
        Kredi karti gerekmez &middot; 10 SKU sonsuza kadar ucretsiz
      </p>

      {/* Hero graphic */}
      <div className="mt-16 max-w-4xl mx-auto rounded-2xl border border-[#e8e0d4] dark:border-[#2A3F38] bg-white dark:bg-[#1A2F28] shadow-2xl shadow-[#3a2d14]/8 dark:shadow-black/40 overflow-hidden">
        {/* Fake browser chrome */}
        <div className="flex items-center gap-1.5 px-4 py-3 border-b border-[#e8e0d4] dark:border-[#2A3F38] bg-[#faf8f5] dark:bg-[#0F1A17]">
          <span className="w-3 h-3 rounded-full bg-red-400" />
          <span className="w-3 h-3 rounded-full bg-yellow-400" />
          <span className="w-3 h-3 rounded-full bg-green-400" />
          <div className="ml-4 flex-1 h-5 rounded-md bg-[#e8e0d4] dark:bg-[#2A3F38] max-w-sm" />
        </div>
        {/* Dashboard preview mockup */}
        <div className="p-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Takip Edilen SKU', value: '247' },
            { label: 'Fiyat Alarmi', value: '12' },
            { label: 'Buybox Orani', value: '%68' },
            { label: 'Ortalama Kar', value: '%18.4' },
          ].map((stat) => (
            <div key={stat.label} className="rounded-xl p-4 bg-[#faf8f5] dark:bg-[#0F1A17] border border-[#e8e0d4] dark:border-[#2A3F38]">
              <p className="text-xs text-[#7a6b4e] dark:text-[#6B8F80] mb-1">{stat.label}</p>
              <p className="text-xl font-bold text-[#5f471d] dark:text-[#4ADE80]">{stat.value}</p>
            </div>
          ))}
        </div>
        <div className="px-6 pb-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
          {['HB Spor Ayakkabi', 'TY Telefon Kilifi', 'HB Laptop Cantasi'].map((product, i) => (
            <div key={product} className="flex items-center justify-between rounded-xl px-4 py-3 bg-[#faf8f5] dark:bg-[#0F1A17] border border-[#e8e0d4] dark:border-[#2A3F38]">
              <span className="text-sm text-[#3a2d14] dark:text-[#F0FDF4] font-medium truncate mr-2">{product}</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full shrink-0 ${
                i === 1
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                  : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-[#4ADE80]'
              }`}>
                {i === 1 ? 'Uyari' : 'Buybox'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function FeaturesSection() {
  return (
    <section id="features" className="py-20 px-4 sm:px-6 bg-[#f5f1eb] dark:bg-[#0a1410]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-[#3a2d14] dark:text-[#F0FDF4]">
            Her seyi tek yerden yonetin
          </h2>
          <p className="mt-3 text-[#7a6b4e] dark:text-[#6B8F80] max-w-xl mx-auto">
            Pazaryerinde rekabetci kalmak icin ihtiyaciniz olan tum araclar.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group rounded-2xl p-6 bg-white dark:bg-[#1A2F28] border border-[#e8e0d4] dark:border-[#2A3F38] hover:border-[#5f471d]/40 dark:hover:border-[#4ADE80]/40 hover:shadow-lg hover:shadow-[#5f471d]/5 dark:hover:shadow-[#4ADE80]/5 transition-all duration-200"
            >
              <div className="w-12 h-12 rounded-xl bg-[#5f471d]/10 dark:bg-[#4ADE80]/10 flex items-center justify-center text-[#5f471d] dark:text-[#4ADE80] mb-4 group-hover:bg-[#5f471d]/15 dark:group-hover:bg-[#4ADE80]/15 transition-colors">
                {feature.icon}
              </div>
              <h3 className="text-lg font-semibold text-[#3a2d14] dark:text-[#F0FDF4] mb-2">
                {feature.title}
              </h3>
              <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80] leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-20 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-[#3a2d14] dark:text-[#F0FDF4]">
            4 adimda hazir
          </h2>
          <p className="mt-3 text-[#7a6b4e] dark:text-[#6B8F80] max-w-xl mx-auto">
            Kurulum dakikalar aliyor, sonuclar hemen gorunuyor.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step, index) => (
            <div key={step.number} className="relative">
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="hidden lg:block absolute top-8 left-[calc(100%-1rem)] w-full h-px bg-gradient-to-r from-[#d4c9b5] dark:from-[#2A3F38] to-transparent z-0" />
              )}
              <div className="relative z-10 rounded-2xl p-6 bg-white dark:bg-[#1A2F28] border border-[#e8e0d4] dark:border-[#2A3F38] h-full">
                <div className="w-10 h-10 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] flex items-center justify-center mb-4">
                  <span className="text-sm font-bold text-white dark:text-[#0F1A17]">
                    {step.number}
                  </span>
                </div>
                <p className="text-sm font-medium text-[#3a2d14] dark:text-[#F0FDF4] leading-relaxed">
                  {step.text}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function PricingSection() {
  return (
    <section id="pricing" className="py-20 px-4 sm:px-6 bg-[#f5f1eb] dark:bg-[#0a1410]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-[#3a2d14] dark:text-[#F0FDF4]">
            Isletmenize uygun plan
          </h2>
          <p className="mt-3 text-[#7a6b4e] dark:text-[#6B8F80] max-w-xl mx-auto">
            Kucukten buyuge her olcekteki e-ticaret isletmesi icin.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {pricingPlans.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-2xl p-6 flex flex-col border transition-all duration-200 ${
                plan.popular
                  ? 'bg-[#5f471d] dark:bg-[#1A2F28] border-[#5f471d] dark:border-[#4ADE80] shadow-xl shadow-[#5f471d]/20 dark:shadow-[#4ADE80]/15 scale-[1.02]'
                  : 'bg-white dark:bg-[#1A2F28] border-[#e8e0d4] dark:border-[#2A3F38]'
              }`}
            >
              {/* Popular badge */}
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#4ADE80] dark:bg-[#4ADE80] text-[#0F1A17] uppercase tracking-wide shadow">
                    Populer
                  </span>
                </div>
              )}

              {/* Plan name */}
              <p className={`text-sm font-semibold uppercase tracking-wider mb-3 ${
                plan.popular ? 'text-white/70' : 'text-[#7a6b4e] dark:text-[#6B8F80]'
              }`}>
                {plan.name}
              </p>

              {/* Price */}
              <div className="mb-6">
                {plan.enterprise ? (
                  <p className={`text-2xl font-bold ${
                    plan.popular ? 'text-white' : 'text-[#3a2d14] dark:text-[#F0FDF4]'
                  }`}>
                    Iletisime Gecin
                  </p>
                ) : (
                  <div className="flex items-baseline gap-1">
                    <span className={`text-4xl font-extrabold ${
                      plan.popular ? 'text-white' : 'text-[#3a2d14] dark:text-[#F0FDF4]'
                    }`}>
                      {plan.price}
                    </span>
                    {plan.price !== '0' && !plan.enterprise && (
                      <span className={`text-sm ${
                        plan.popular ? 'text-white/70' : 'text-[#7a6b4e] dark:text-[#6B8F80]'
                      }`}>
                        TL{plan.period}
                      </span>
                    )}
                    {plan.price === '0' && (
                      <span className={`text-sm ${
                        plan.popular ? 'text-white/70' : 'text-[#7a6b4e] dark:text-[#6B8F80]'
                      }`}>
                        TL
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Features */}
              <ul className="space-y-2.5 mb-8 flex-1">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <span className={`mt-0.5 ${
                      plan.popular ? 'text-[#4ADE80]' : 'text-[#5f471d] dark:text-[#4ADE80]'
                    }`}>
                      <IconCheck />
                    </span>
                    <span className={`text-sm ${
                      plan.popular ? 'text-white/85' : 'text-[#7a6b4e] dark:text-[#6B8F80]'
                    }`}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              {plan.enterprise ? (
                <a
                  href={plan.ctaHref}
                  className="block text-center py-2.5 px-4 rounded-xl border border-[#d4c9b5] dark:border-[#2A3F38] text-[#3a2d14] dark:text-[#F0FDF4] text-sm font-semibold hover:bg-[#faf8f5] dark:hover:bg-[#0F1A17] transition-colors"
                >
                  {plan.cta}
                </a>
              ) : (
                <Link
                  to={plan.ctaHref}
                  className={`block text-center py-2.5 px-4 rounded-xl text-sm font-semibold transition-colors ${
                    plan.popular
                      ? 'bg-[#4ADE80] text-[#0F1A17] hover:bg-[#4ADE80]/80'
                      : 'bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80'
                  }`}
                >
                  {plan.cta}
                </Link>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function CtaSection() {
  return (
    <section className="py-20 px-4 sm:px-6">
      <div className="max-w-3xl mx-auto text-center">
        <div className="rounded-3xl p-10 sm:p-14 bg-gradient-to-br from-[#5f471d] to-[#3d3427] dark:from-[#1A2F28] dark:to-[#0F1A17] border border-[#5f471d]/30 dark:border-[#4ADE80]/20 shadow-2xl shadow-[#3a2d14]/20 dark:shadow-black/40">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white dark:text-[#F0FDF4] mb-4">
            Hemen Baslayiniz
          </h2>
          <p className="text-white/70 dark:text-[#6B8F80] mb-8 text-lg">
            Rakiplerinizden once harekete gecin. Kredi karti gerekmez.
          </p>
          <Link
            to="/register"
            className="inline-block px-10 py-4 rounded-xl bg-[#4ADE80] text-[#0F1A17] font-bold text-base hover:bg-[#4ADE80]/80 transition-colors shadow-lg shadow-[#4ADE80]/20"
          >
            Ucretsiz Hesap Olustur
          </Link>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-[#e8e0d4] dark:border-[#2A3F38] py-8 px-4 sm:px-6 bg-[#faf8f5] dark:bg-[#0F1A17]">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg brand-mark flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <span className="font-bold text-[#3a2d14] dark:text-[#F0FDF4]">MarketPulse</span>
        </div>

        {/* Copyright */}
        <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80]">
          &copy; 2026 MarketPulse. Tum haklari saklidir.
        </p>

        {/* Links */}
        <div className="flex items-center gap-4 text-sm text-[#7a6b4e] dark:text-[#6B8F80]">
          <Link to="/login" className="hover:text-[#3a2d14] dark:hover:text-[#F0FDF4] transition-colors">
            Giris Yap
          </Link>
          <Link to="/register" className="hover:text-[#3a2d14] dark:hover:text-[#F0FDF4] transition-colors">
            Kayit Ol
          </Link>
        </div>
      </div>
    </footer>
  )
}

// --- Page ---

export default function Landing() {
  const { user, loading } = useAuth()
  const isLoggedIn = !loading && !!user

  return (
    <div className="min-h-screen bg-[#faf8f5] dark:bg-[#0F1A17] text-[#3a2d14] dark:text-[#F0FDF4] scroll-smooth">
      <Navbar isLoggedIn={isLoggedIn} />

      <main>
        <HeroSection isLoggedIn={isLoggedIn} />
        <FeaturesSection />
        <HowItWorksSection />
        <PricingSection />
        <CtaSection />
      </main>

      <Footer />
    </div>
  )
}
