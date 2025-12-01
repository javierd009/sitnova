import type { User, Condominium } from '@/shared/types/database'

export interface AuthState {
  user: User | null
  condominium: Condominium | null
  isLoading: boolean
  isAuthenticated: boolean
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface SignUpData {
  email: string
  password: string
  fullName: string
  phone?: string
  condominiumId: string
}

export interface AuthSession {
  user: User
  condominium: Condominium
  accessToken: string
  refreshToken: string
}
