'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '../store/auth-store'
import { authService } from '../services/auth-service'

export function useAuth() {
  const router = useRouter()
  const { user, condominium, isLoading, isAuthenticated, login, logout, setLoading } = useAuthStore()

  useEffect(() => {
    const initAuth = async () => {
      try {
        const session = await authService.getSession()
        if (session) {
          login(session.user, session.condominium)
        } else {
          setLoading(false)
        }
      } catch (error) {
        console.error('Error initializing auth:', error)
        setLoading(false)
      }
    }

    initAuth()

    const { data: { subscription } } = authService.onAuthStateChange(async (event) => {
      if (event === 'SIGNED_OUT') {
        logout()
        router.push('/auth/login')
      }
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [login, logout, setLoading, router])

  const handleLogout = async () => {
    try {
      await authService.logout()
      logout()
      router.push('/auth/login')
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  return {
    user,
    condominium,
    isLoading,
    isAuthenticated,
    logout: handleLogout,
  }
}

export function useRequireAuth() {
  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuthStore()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth/login')
    }
  }, [isAuthenticated, isLoading, router])

  return { isLoading }
}
