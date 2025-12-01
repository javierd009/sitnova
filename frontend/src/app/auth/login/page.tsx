import { LoginForm } from '@/features/auth/components/login-form'

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 p-4">
      <LoginForm />
    </main>
  )
}
