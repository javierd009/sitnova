import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SITNOVA Admin - Sistema de Control de Acceso',
  description: 'Panel de administracion multi-tenant para condominios',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es">
      <body className="font-sans">{children}</body>
    </html>
  )
}
