import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const { user, loading, signIn } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (loading) return null
  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)

    const { error } = await signIn(email, password)
    if (error) {
      setError(error.message)
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#faf8f5] to-[#f0ece4] dark:from-[#0F1A17] dark:to-[#162420] p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl brand-mark flex items-center justify-center mx-auto mb-4">
            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-[#3a2d14] dark:text-[#F0FDF4]">MarketPulse</h1>
          <p className="text-sm text-[#7a6b4e] dark:text-[#6B8F80] mt-1">Hesabiniza giris yapin</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white dark:bg-[#1A2F28] rounded-2xl shadow-lg border border-[#e8e0d4] dark:border-[#2A3F38] p-6 space-y-4">
          {error && (
            <div className="px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-[#3a2d14] dark:text-[#F0FDF4] mb-1.5">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full px-3 py-2.5 rounded-xl border border-[#d4c9b5] dark:border-[#2A3F38] bg-[#faf8f5] dark:bg-[#0F1A17] text-[#3a2d14] dark:text-[#F0FDF4] text-sm focus:outline-none focus:ring-2 focus:ring-[#5f471d]/30 dark:focus:ring-[#4ADE80]/30 placeholder:text-[#b0a48c] dark:placeholder:text-[#4A6B5D]"
              placeholder="ornek@email.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-[#3a2d14] dark:text-[#F0FDF4] mb-1.5">
              Sifre
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full px-3 py-2.5 rounded-xl border border-[#d4c9b5] dark:border-[#2A3F38] bg-[#faf8f5] dark:bg-[#0F1A17] text-[#3a2d14] dark:text-[#F0FDF4] text-sm focus:outline-none focus:ring-2 focus:ring-[#5f471d]/30 dark:focus:ring-[#4ADE80]/30 placeholder:text-[#b0a48c] dark:placeholder:text-[#4A6B5D]"
              placeholder="Sifreniz"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-xl bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] font-semibold text-sm hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors disabled:opacity-50"
          >
            {submitting ? 'Giris yapiliyor...' : 'Giris Yap'}
          </button>
        </form>

        <p className="text-center text-sm text-[#7a6b4e] dark:text-[#6B8F80] mt-6">
          Hesabiniz yok mu?{' '}
          <Link to="/register" className="font-semibold text-[#5f471d] dark:text-[#4ADE80] hover:underline">
            Kayit Ol
          </Link>
        </p>
      </div>
    </div>
  )
}
