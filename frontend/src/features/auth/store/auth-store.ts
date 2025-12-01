import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Condominium } from '@/shared/types/database'

interface AuthState {
  user: User | null
  condominium: Condominium | null
  isLoading: boolean
  isAuthenticated: boolean
}

interface AuthActions {
  setUser: (user: User | null) => void
  setCondominium: (condominium: Condominium | null) => void
  setLoading: (loading: boolean) => void
  login: (user: User, condominium: Condominium) => void
  logout: () => void
  reset: () => void
}

const initialState: AuthState = {
  user: null,
  condominium: null,
  isLoading: true,
  isAuthenticated: false,
}

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set) => ({
      ...initialState,

      setUser: (user) => set({
        user,
        isAuthenticated: !!user
      }),

      setCondominium: (condominium) => set({ condominium }),

      setLoading: (isLoading) => set({ isLoading }),

      login: (user, condominium) => set({
        user,
        condominium,
        isAuthenticated: true,
        isLoading: false,
      }),

      logout: () => set({
        user: null,
        condominium: null,
        isAuthenticated: false,
        isLoading: false,
      }),

      reset: () => set(initialState),
    }),
    {
      name: 'sitnova-auth',
      partialize: (state) => ({
        user: state.user,
        condominium: state.condominium,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
