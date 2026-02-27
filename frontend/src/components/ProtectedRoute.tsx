import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import PageSkeleton from './Skeleton'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <PageSkeleton />
  if (!user) return <Navigate to="/login" replace />

  // Onboarding kontrolu — ilk giris yapan kullanicilar
  const onboardingDone = localStorage.getItem('mp_onboarding_done')
  if (!onboardingDone && location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}
