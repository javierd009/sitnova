export interface Condominium {
  id: string
  name: string
  address: string
  timezone: string
  logo_url: string | null
  settings: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface User {
  id: string
  email: string
  full_name: string
  phone: string | null
  role: 'super_admin' | 'admin' | 'operator' | 'resident'
  condominium_id: string
  apartment: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Resident {
  id: string
  condominium_id: string
  user_id: string | null
  full_name: string
  apartment: string
  phone: string
  phone_secondary: string | null
  email: string | null
  address: string | null
  address_instructions: string | null
  notification_preference: 'whatsapp' | 'call' | 'both'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Vehicle {
  id: string
  condominium_id: string
  resident_id: string
  license_plate: string
  vehicle_type: 'auto' | 'moto' | 'camion' | 'otro'
  brand: string | null
  model: string | null
  color: string | null
  is_authorized: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface PreAuthorizedVisitor {
  id: string
  condominium_id: string
  resident_id: string
  visitor_name: string
  cedula: string | null
  license_plate: string | null
  valid_from: string
  valid_until: string
  single_use: boolean
  used: boolean
  notes: string | null
  created_at: string
}

export interface AccessLog {
  id: string
  condominium_id: string
  session_id: string
  entry_type: 'vehicle' | 'pedestrian' | 'delivery'
  license_plate: string | null
  cedula: string | null
  visitor_name: string | null
  resident_id: string | null
  resident_name: string | null
  apartment: string | null
  access_decision: 'granted' | 'denied' | 'pending'
  authorization_type: 'auto_placa' | 'residente' | 'admin' | 'pre_autorizado' | 'protocolo' | 'delivery' | null
  denial_reason: string | null
  plate_image_url: string | null
  cedula_image_url: string | null
  notes: string | null
  created_at: string
}

export interface AccessStats {
  total_today: number
  granted_today: number
  denied_today: number
  pending_today: number
  vehicles_authorized: number
  pre_authorized_active: number
}
