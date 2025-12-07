 -- =====================================================
-- SITNOVA - Sistema Inteligente de Control de Acceso
-- DATABASE SCHEMA - Multi-Tenant
-- Version: 1.0
-- Created: 2025-01-22
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Para búsquedas de texto

-- =====================================================
-- MULTI-TENANT: CONDOMINIUMS (Tenants)
-- =====================================================
CREATE TABLE IF NOT EXISTS condominiums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Información básica
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100) DEFAULT 'Costa Rica',
    phone VARCHAR(20),
    email VARCHAR(255),

    -- Logo y branding
    logo_url VARCHAR(500),
    primary_color VARCHAR(7) DEFAULT '#3B82F6', -- HEX color

    -- Configuración de intercomunicador
    pbx_extension VARCHAR(50), -- Extensión en FreePBX
    pbx_caller_id VARCHAR(50), -- Caller ID para llamadas salientes

    -- Configuración de barrera/portón
    gate_control_type VARCHAR(50) DEFAULT 'api', -- 'api', 'relay', 'http', 'manual'
    gate_api_endpoint VARCHAR(500),
    gate_api_key VARCHAR(255),
    gate_relay_config JSONB, -- {pin: 12, duration: 3000}

    -- Configuración de cámaras Hikvision
    camera_plates_ip VARCHAR(50),
    camera_plates_username VARCHAR(100),
    camera_plates_password VARCHAR(255),
    camera_cedula_ip VARCHAR(50),
    camera_cedula_username VARCHAR(100),
    camera_cedula_password VARCHAR(255),

    -- Billing y suscripción
    subscription_plan VARCHAR(50) DEFAULT 'trial', -- 'trial', 'basic', 'pro', 'enterprise'
    subscription_status VARCHAR(50) DEFAULT 'active', -- 'active', 'suspended', 'cancelled'
    monthly_price DECIMAL(10, 2) DEFAULT 0,
    trial_ends_at TIMESTAMP,
    next_billing_date DATE,

    -- Límites del plan
    max_residents INTEGER DEFAULT 50,
    max_access_points INTEGER DEFAULT 1,
    log_retention_days INTEGER DEFAULT 30,

    -- Configuración de notificaciones
    whatsapp_enabled BOOLEAN DEFAULT true,
    push_enabled BOOLEAN DEFAULT true,
    sms_enabled BOOLEAN DEFAULT false,

    -- Estado
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ATTENTION PROTOCOLS (Protocolos configurables)
-- =====================================================
CREATE TABLE IF NOT EXISTS attention_protocols (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

    -- Identificación
    name VARCHAR(200) NOT NULL,
    description TEXT,

    -- Configuración del flujo
    protocol_config JSONB NOT NULL,
    /* Ejemplo de estructura:
    {
      "greeting": {
        "message": "Bienvenido a Los Almendros. ¿A quién visita?",
        "voice_settings": {
          "language": "es-CR",
          "speed": 1.0,
          "tone": "professional"
        }
      },
      "visitor_flow": {
        "check_pre_authorized": true,
        "check_vehicle_plate": true,
        "require_resident_approval": true,
        "max_wait_time_seconds": 30,
        "retry_call_times": 2,
        "auto_deny_if_no_answer": false
      },
      "delivery_flow": {
        "enabled": true,
        "auto_authorize": false,
        "require_package_photo": true,
        "require_cedula": true,
        "notify_resident_immediately": true
      },
      "service_flow": {
        "enabled": true,
        "allowed_services": ["plumber", "electrician", "cleaning"],
        "require_pre_authorization": true
      },
      "emergency_contacts": [
        {"name": "Admin", "phone": "+50612345678"}
      ],
      "business_hours": {
        "enabled": true,
        "start": "06:00",
        "end": "22:00",
        "timezone": "America/Costa_Rica"
      },
      "after_hours_behavior": {
        "allow_access": false,
        "emergency_only": true,
        "notification_contacts": ["+50612345678"]
      }
    }
    */

    -- Flags rápidos (denormalizados del JSON para queries)
    auto_authorize_known_vehicles BOOLEAN DEFAULT true,
    require_cedula_always BOOLEAN DEFAULT true,
    require_resident_approval BOOLEAN DEFAULT true,

    -- Control
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(condominium_id, name)
);

-- =====================================================
-- RESIDENTS (Residentes)
-- =====================================================
CREATE TABLE IF NOT EXISTS residents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

    -- Datos personales
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200) GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED,
    email VARCHAR(255),

    -- Teléfonos (Costa Rica: +506)
    phone_primary VARCHAR(20), -- Para llamadas del agente
    phone_mobile VARCHAR(20), -- Para WhatsApp/SMS
    phone_emergency VARCHAR(20),

    -- Identificación
    id_type VARCHAR(50), -- 'cedula', 'dimex', 'passport'
    id_number VARCHAR(50),

    -- Ubicación en el condominio
    unit_number VARCHAR(50) NOT NULL, -- "12", "A-304", etc.
    unit_type VARCHAR(50) DEFAULT 'house', -- 'house', 'apartment', 'commercial', 'townhouse'
    building VARCHAR(50), -- Para condominios con múltiples edificios
    floor VARCHAR(10),

    -- Contacto para sistema de voz
    pbx_extension VARCHAR(50), -- Extensión en FreePBX para transferir llamadas
    whatsapp_number VARCHAR(20), -- Puede ser diferente al phone_mobile

    -- Configuración de acceso
    auto_authorize_known_vehicles BOOLEAN DEFAULT true,
    auto_authorize_pre_authorized_visitors BOOLEAN DEFAULT true,
    require_notification_all_entries BOOLEAN DEFAULT false,
    max_visitors_per_day INTEGER, -- NULL = ilimitado

    -- Preferencias de notificación
    notify_via_whatsapp BOOLEAN DEFAULT true,
    notify_via_push BOOLEAN DEFAULT true,
    notify_via_sms BOOLEAN DEFAULT false,
    notify_via_call BOOLEAN DEFAULT false,

    -- Horarios de no molestar
    quiet_hours_start TIME,
    quiet_hours_end TIME,

    -- Notas
    notes TEXT,
    security_notes TEXT, -- Notas de seguridad (solo admin puede ver)

    -- Estado
    is_active BOOLEAN DEFAULT true,
    is_owner BOOLEAN DEFAULT true, -- vs renter
    move_in_date DATE,
    move_out_date DATE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(condominium_id, unit_number)
);

-- =====================================================
-- VEHICLES (Vehículos autorizados)
-- =====================================================
CREATE TABLE IF NOT EXISTS vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID NOT NULL REFERENCES residents(id) ON DELETE CASCADE,

    -- Datos del vehículo
    license_plate VARCHAR(20) NOT NULL,
    country_code VARCHAR(2) DEFAULT 'CR', -- Costa Rica

    -- Información adicional
    brand VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    color VARCHAR(50),
    vehicle_type VARCHAR(50), -- 'car', 'motorcycle', 'truck', 'van', 'bicycle', 'other'

    -- OCR reference
    plate_image_url VARCHAR(500), -- Foto de referencia de la placa
    vehicle_image_url VARCHAR(500), -- Foto del vehículo completo

    -- Control de acceso
    auto_authorize BOOLEAN DEFAULT true,
    is_temporary BOOLEAN DEFAULT false, -- Para vehículos temporales (alquiler, prestado)
    valid_from DATE,
    valid_until DATE,

    -- Estadísticas
    total_entries INTEGER DEFAULT 0,
    last_entry_at TIMESTAMP WITH TIME ZONE,

    -- Notas
    notes TEXT,

    -- Estado
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(condominium_id, license_plate)
);

-- =====================================================
-- PRE-AUTHORIZED VISITORS (Visitantes pre-autorizados)
-- =====================================================
CREATE TABLE IF NOT EXISTS pre_authorized_visitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID NOT NULL REFERENCES residents(id) ON DELETE CASCADE,

    -- Datos del visitante
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(20),

    -- Identificación
    id_type VARCHAR(50), -- 'cedula', 'dimex', 'passport'
    id_number VARCHAR(50),

    -- Vehículo (opcional)
    vehicle_plate VARCHAR(20),
    vehicle_description VARCHAR(200),

    -- Vigencia
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Configuración
    auto_authorize BOOLEAN DEFAULT true,
    max_entries INTEGER, -- NULL = ilimitado durante el periodo
    entries_used INTEGER DEFAULT 0,

    -- Tipo de visitante
    visitor_type VARCHAR(50) DEFAULT 'guest', -- 'guest', 'family', 'service', 'delivery', 'contractor'

    -- Horarios permitidos
    allowed_days VARCHAR(50)[], -- ['monday', 'tuesday', 'wednesday']
    allowed_hours_start TIME,
    allowed_hours_end TIME,

    -- Notas
    notes TEXT,
    purpose VARCHAR(500), -- "Reparación de plomería", "Familia de visita"

    -- Tracking
    created_by UUID REFERENCES residents(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- VISITOR REGISTRY (Registro permanente de visitantes)
-- =====================================================
CREATE TABLE IF NOT EXISTS visitor_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

    -- Datos extraídos del OCR de cédula
    id_type VARCHAR(50) NOT NULL, -- 'cedula', 'dimex', 'passport'
    id_number VARCHAR(50) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    birthdate DATE,

    -- Fotos
    id_photo_url VARCHAR(500), -- Última foto de cédula
    face_photo_url VARCHAR(500), -- Foto facial extraída (futuro: face recognition)

    -- Datos del OCR raw
    ocr_confidence FLOAT, -- 0-100
    ocr_raw_data JSONB, -- Todos los datos extraídos del OCR

    -- Vehículo habitual
    usual_vehicle_plate VARCHAR(20),

    -- Estadísticas de visitas
    total_visits INTEGER DEFAULT 0,
    first_visit_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_visit_at TIMESTAMP WITH TIME ZONE,

    -- Seguridad
    is_blacklisted BOOLEAN DEFAULT false,
    blacklist_reason TEXT,
    blacklisted_at TIMESTAMP WITH TIME ZONE,
    blacklisted_by UUID REFERENCES residents(id),
    security_notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(condominium_id, id_number)
);

-- =====================================================
-- VISITOR-RESIDENT HISTORY (Relación visitante-residente)
-- =====================================================
CREATE TABLE IF NOT EXISTS visitor_resident_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visitor_id UUID NOT NULL REFERENCES visitor_registry(id) ON DELETE CASCADE,
    resident_id UUID NOT NULL REFERENCES residents(id) ON DELETE CASCADE,
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

    -- Estadísticas
    visit_count INTEGER DEFAULT 1,
    first_visit TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_visit TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Notas
    relationship VARCHAR(100), -- "Familia", "Amigo", "Proveedor"
    notes TEXT,

    UNIQUE(visitor_id, resident_id)
);

-- =====================================================
-- ACCESS LOGS (CRÍTICO - Logs de todos los accesos)
-- =====================================================
CREATE TABLE IF NOT EXISTS access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

    -- Timestamp
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Tipo de entrada y dirección
    entry_type VARCHAR(50) NOT NULL, -- 'vehicle', 'intercom', 'pedestrian', 'emergency'
    direction VARCHAR(10) NOT NULL DEFAULT 'entry', -- 'entry' = entrada, 'exit' = salida
    access_point VARCHAR(100), -- "Puerta Principal", "Entrada Trasera"

    -- Residente relacionado
    resident_id UUID REFERENCES residents(id),
    unit_number VARCHAR(50), -- Denormalizado para queries rápidas

    -- Vehículo (si aplica)
    vehicle_id UUID REFERENCES vehicles(id),
    license_plate VARCHAR(20), -- Detectada por OCR (puede no estar en DB)
    plate_confidence FLOAT, -- Confianza del OCR (0-100)
    plate_image_url VARCHAR(500),
    vehicle_photo_url VARCHAR(500),

    -- Visitante (si aplica)
    visitor_id UUID REFERENCES visitor_registry(id),
    pre_authorized_visitor_id UUID REFERENCES pre_authorized_visitors(id),

    -- Datos del visitante (denormalizados del OCR)
    visitor_id_type VARCHAR(50), -- 'cedula', 'dimex', 'passport'
    visitor_id_number VARCHAR(50),
    visitor_full_name VARCHAR(200),
    visitor_birthdate DATE,
    visitor_id_photo_url VARCHAR(500),
    visitor_phone VARCHAR(20),

    -- OCR metadata
    ocr_confidence FLOAT, -- Confianza general del OCR
    ocr_processing_time INTEGER, -- Milisegundos
    ocr_raw_data JSONB, -- Datos crudos del OCR

    -- Detalles de la llamada/interacción (si fue por intercomunicador)
    call_id VARCHAR(255), -- ID de Ultravox
    call_duration INTEGER, -- Segundos
    call_transcript TEXT, -- Transcripción completa de la conversación
    audio_recording_url VARCHAR(500), -- URL de la grabación

    -- Decisión de acceso
    access_decision VARCHAR(50) NOT NULL, -- 'authorized', 'denied', 'pending', 'cancelled'
    decision_reason TEXT, -- "Vehículo autorizado", "Residente aprobó", "No contestó"
    decision_method VARCHAR(50), -- 'auto_vehicle', 'auto_pre_authorized', 'resident_approved', 'protocol', 'manual', 'emergency'

    -- Residente que autorizó (si aplica)
    authorized_by UUID REFERENCES residents(id),
    authorization_timestamp TIMESTAMP WITH TIME ZONE,

    -- Control de barrera/portón
    gate_opened BOOLEAN DEFAULT false,
    gate_opened_at TIMESTAMP WITH TIME ZONE,
    gate_close_at TIMESTAMP WITH TIME ZONE,

    -- Protocolo usado
    protocol_id UUID REFERENCES attention_protocols(id),
    protocol_name VARCHAR(200), -- Denormalizado

    -- Metadatos adicionales
    metadata JSONB, -- Datos variables según el tipo de acceso

    -- Flags de seguridad
    is_suspicious BOOLEAN DEFAULT false,
    suspicious_reason TEXT,
    reviewed_by UUID REFERENCES residents(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Indexing
    search_text TEXT -- Para búsquedas full-text
);

-- =====================================================
-- USERS (Usuarios del dashboard)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Nombre
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(200) GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED,

    -- Rol y permisos
    role VARCHAR(50) NOT NULL, -- 'super_admin', 'condominium_admin', 'security_staff', 'resident'

    -- Relación con condominio
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE CASCADE,

    -- Permisos específicos (JSON)
    permissions JSONB,
    /* {
      "condominiums": {"create": true, "read": true, "update": true, "delete": false},
      "residents": {"create": true, "read": true, "update": true, "delete": false},
      "access_logs": {"read": true, "export": true},
      "analytics": {"read": true}
    } */

    -- Avatar
    avatar_url VARCHAR(500),

    -- Notificaciones
    email_notifications BOOLEAN DEFAULT true,
    push_notifications BOOLEAN DEFAULT true,

    -- Autenticación
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_login_ip VARCHAR(50),
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,

    -- Estado
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- NOTIFICATIONS (Log de notificaciones enviadas)
-- =====================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE CASCADE,
    access_log_id UUID REFERENCES access_logs(id) ON DELETE CASCADE,

    -- Tipo y canal
    notification_type VARCHAR(50) NOT NULL, -- 'visitor_arrival', 'vehicle_entry', 'emergency', 'system'
    channel VARCHAR(50) NOT NULL, -- 'whatsapp', 'push', 'sms', 'call', 'email'

    -- Destinatario
    recipient_phone VARCHAR(20),
    recipient_email VARCHAR(255),
    recipient_device_token VARCHAR(500),

    -- Contenido
    title VARCHAR(200),
    message TEXT,
    image_url VARCHAR(500),
    action_url VARCHAR(500), -- Deep link o URL

    -- Estado de envío
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sent', 'delivered', 'failed', 'read'
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    failed_reason TEXT,

    -- Provider metadata
    provider_message_id VARCHAR(255), -- ID del proveedor (WhatsApp, OneSignal, etc)
    provider_response JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- SYSTEM EVENTS (Eventos del sistema para auditoría)
-- =====================================================
CREATE TABLE IF NOT EXISTS system_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Evento
    event_type VARCHAR(100) NOT NULL, -- 'user_login', 'config_change', 'emergency_access', 'system_error'
    event_category VARCHAR(50), -- 'security', 'config', 'access', 'system'
    severity VARCHAR(50) DEFAULT 'info', -- 'info', 'warning', 'error', 'critical'

    -- Descripción
    description TEXT NOT NULL,

    -- Contexto
    ip_address VARCHAR(50),
    user_agent TEXT,
    request_id VARCHAR(255),

    -- Datos adicionales
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Condominiums
CREATE INDEX idx_condominiums_slug ON condominiums(slug);
CREATE INDEX idx_condominiums_is_active ON condominiums(is_active);

-- Residents
CREATE INDEX idx_residents_condominium ON residents(condominium_id);
CREATE INDEX idx_residents_unit_number ON residents(condominium_id, unit_number);
CREATE INDEX idx_residents_full_name ON residents USING gin(to_tsvector('spanish', full_name));
CREATE INDEX idx_residents_phone ON residents(phone_primary);
CREATE INDEX idx_residents_is_active ON residents(is_active);

-- Vehicles
CREATE INDEX idx_vehicles_condominium ON vehicles(condominium_id);
CREATE INDEX idx_vehicles_resident ON vehicles(resident_id);
CREATE INDEX idx_vehicles_plate ON vehicles(license_plate);
CREATE INDEX idx_vehicles_active ON vehicles(is_active);

-- Pre-authorized visitors
CREATE INDEX idx_pre_auth_visitors_condominium ON pre_authorized_visitors(condominium_id);
CREATE INDEX idx_pre_auth_visitors_resident ON pre_authorized_visitors(resident_id);
CREATE INDEX idx_pre_auth_visitors_valid ON pre_authorized_visitors(valid_from, valid_until);
CREATE INDEX idx_pre_auth_visitors_id_number ON pre_authorized_visitors(id_number);

-- Visitor registry
CREATE INDEX idx_visitor_registry_condominium ON visitor_registry(condominium_id);
CREATE INDEX idx_visitor_registry_id_number ON visitor_registry(id_number);
CREATE INDEX idx_visitor_registry_name ON visitor_registry USING gin(to_tsvector('spanish', full_name));
CREATE INDEX idx_visitor_registry_blacklisted ON visitor_registry(is_blacklisted);

-- Access logs (CRÍTICO para performance)
CREATE INDEX idx_access_logs_condominium ON access_logs(condominium_id);
CREATE INDEX idx_access_logs_timestamp ON access_logs(timestamp DESC);
CREATE INDEX idx_access_logs_resident ON access_logs(resident_id);
CREATE INDEX idx_access_logs_visitor ON access_logs(visitor_id);
CREATE INDEX idx_access_logs_plate ON access_logs(license_plate);
CREATE INDEX idx_access_logs_decision ON access_logs(access_decision);
CREATE INDEX idx_access_logs_entry_type ON access_logs(entry_type);
CREATE INDEX idx_access_logs_direction ON access_logs(direction);
CREATE INDEX idx_access_logs_call_id ON access_logs(call_id);
CREATE INDEX idx_access_logs_search ON access_logs USING gin(to_tsvector('spanish', search_text));

-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_condominium ON users(condominium_id);
CREATE INDEX idx_users_role ON users(role);

-- Notifications
CREATE INDEX idx_notifications_condominium ON notifications(condominium_id);
CREATE INDEX idx_notifications_resident ON notifications(resident_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- System events
CREATE INDEX idx_system_events_condominium ON system_events(condominium_id);
CREATE INDEX idx_system_events_type ON system_events(event_type);
CREATE INDEX idx_system_events_created_at ON system_events(created_at DESC);

-- =====================================================
-- FUNCTIONS & TRIGGERS
-- =====================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_condominiums_updated_at BEFORE UPDATE ON condominiums
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_protocols_updated_at BEFORE UPDATE ON attention_protocols
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_residents_updated_at BEFORE UPDATE ON residents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vehicles_updated_at BEFORE UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pre_auth_visitors_updated_at BEFORE UPDATE ON pre_authorized_visitors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_visitor_registry_updated_at BEFORE UPDATE ON visitor_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update search_text in access_logs for full-text search
CREATE OR REPLACE FUNCTION update_access_log_search_text()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_text := COALESCE(NEW.visitor_full_name, '') || ' ' ||
                      COALESCE(NEW.visitor_id_number, '') || ' ' ||
                      COALESCE(NEW.license_plate, '') || ' ' ||
                      COALESCE(NEW.unit_number, '');
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER set_access_log_search_text BEFORE INSERT OR UPDATE ON access_logs
    FOR EACH ROW EXECUTE FUNCTION update_access_log_search_text();

-- Update vehicle entry count and last entry
CREATE OR REPLACE FUNCTION update_vehicle_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.vehicle_id IS NOT NULL AND NEW.gate_opened = true THEN
        UPDATE vehicles
        SET
            total_entries = total_entries + 1,
            last_entry_at = NEW.timestamp
        WHERE id = NEW.vehicle_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_vehicle_stats_trigger AFTER INSERT ON access_logs
    FOR EACH ROW EXECUTE FUNCTION update_vehicle_stats();

-- Update visitor registry stats
CREATE OR REPLACE FUNCTION update_visitor_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.visitor_id IS NOT NULL AND NEW.gate_opened = true THEN
        UPDATE visitor_registry
        SET
            total_visits = total_visits + 1,
            last_visit_at = NEW.timestamp
        WHERE id = NEW.visitor_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_visitor_stats_trigger AFTER INSERT ON access_logs
    FOR EACH ROW EXECUTE FUNCTION update_visitor_stats();

-- Update pre-authorized visitor usage
CREATE OR REPLACE FUNCTION update_pre_auth_visitor_usage()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.pre_authorized_visitor_id IS NOT NULL AND NEW.gate_opened = true THEN
        UPDATE pre_authorized_visitors
        SET entries_used = entries_used + 1
        WHERE id = NEW.pre_authorized_visitor_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_pre_auth_usage_trigger AFTER INSERT ON access_logs
    FOR EACH ROW EXECUTE FUNCTION update_pre_auth_visitor_usage();

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE condominiums ENABLE ROW LEVEL SECURITY;
ALTER TABLE attention_protocols ENABLE ROW LEVEL SECURITY;
ALTER TABLE residents ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE pre_authorized_visitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE visitor_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE visitor_resident_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_events ENABLE ROW LEVEL SECURITY;

-- Helper function to get user's condominium_id
CREATE OR REPLACE FUNCTION get_user_condominium_id()
RETURNS UUID AS $$
    SELECT condominium_id FROM users WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER;

-- Helper function to check if user is super admin
CREATE OR REPLACE FUNCTION is_super_admin()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid() AND role = 'super_admin'
    );
$$ LANGUAGE sql SECURITY DEFINER;

-- POLICIES: Super Admin can see everything
CREATE POLICY "Super admins have full access"
    ON condominiums FOR ALL
    USING (is_super_admin());

-- POLICIES: Condominium admins can only see their condominium
CREATE POLICY "Condominium admins can view their condominium"
    ON condominiums FOR SELECT
    USING (id = get_user_condominium_id());

CREATE POLICY "Condominium admins can update their condominium"
    ON condominiums FOR UPDATE
    USING (id = get_user_condominium_id());

-- POLICIES: Residents
CREATE POLICY "Users can view residents from their condominium"
    ON residents FOR SELECT
    USING (condominium_id = get_user_condominium_id() OR is_super_admin());

CREATE POLICY "Admins can manage residents in their condominium"
    ON residents FOR ALL
    USING (
        condominium_id = get_user_condominium_id() AND
        EXISTS (
            SELECT 1 FROM users
            WHERE id = auth.uid() AND role IN ('super_admin', 'condominium_admin')
        )
    );

-- POLICIES: Access logs
CREATE POLICY "Users can view access logs from their condominium"
    ON access_logs FOR SELECT
    USING (condominium_id = get_user_condominium_id() OR is_super_admin());

-- Residents can only see their own access logs
CREATE POLICY "Residents can view their own access logs"
    ON access_logs FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE id = auth.uid()
            AND role = 'resident'
            AND resident_id = access_logs.resident_id
        )
    );

-- Similar policies for other tables...
-- (Se pueden agregar más políticas específicas según necesidades)

-- =====================================================
-- SEED DATA
-- =====================================================

-- Insert default super admin user (CAMBIAR PASSWORD EN PRODUCCIÓN)
INSERT INTO users (email, password_hash, role, first_name, last_name, is_active, email_verified)
VALUES (
    'admin@sitnova.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5eoHZj.QLI8kO', -- password: "changeme123"
    'super_admin',
    'Super',
    'Admin',
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- =====================================================
-- VIEWS FOR ANALYTICS
-- =====================================================

-- View: Daily access stats per condominium
CREATE OR REPLACE VIEW daily_access_stats AS
SELECT
    condominium_id,
    DATE(timestamp) as date,
    COUNT(*) as total_accesses,
    COUNT(CASE WHEN access_decision = 'authorized' THEN 1 END) as authorized,
    COUNT(CASE WHEN access_decision = 'denied' THEN 1 END) as denied,
    COUNT(CASE WHEN entry_type = 'vehicle' THEN 1 END) as vehicle_entries,
    COUNT(CASE WHEN entry_type = 'intercom' THEN 1 END) as intercom_entries,
    COUNT(CASE WHEN decision_method = 'auto_vehicle' THEN 1 END) as auto_authorized
FROM access_logs
GROUP BY condominium_id, DATE(timestamp)
ORDER BY date DESC;

-- View: Resident activity summary
CREATE OR REPLACE VIEW resident_activity_summary AS
SELECT
    r.id as resident_id,
    r.condominium_id,
    r.full_name,
    r.unit_number,
    COUNT(DISTINCT v.id) as total_vehicles,
    COUNT(DISTINCT al.id) as total_accesses,
    COUNT(DISTINCT CASE WHEN al.entry_type = 'intercom' THEN al.visitor_id END) as unique_visitors,
    MAX(al.timestamp) as last_access
FROM residents r
LEFT JOIN vehicles v ON v.resident_id = r.id AND v.is_active = true
LEFT JOIN access_logs al ON al.resident_id = r.id
WHERE r.is_active = true
GROUP BY r.id, r.condominium_id, r.full_name, r.unit_number;

-- View: Top visitors by condominium
CREATE OR REPLACE VIEW top_visitors AS
SELECT
    condominium_id,
    visitor_id,
    visitor_full_name,
    visitor_id_number,
    COUNT(*) as visit_count,
    MAX(timestamp) as last_visit,
    COUNT(DISTINCT resident_id) as residents_visited
FROM access_logs
WHERE visitor_id IS NOT NULL
AND timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY condominium_id, visitor_id, visitor_full_name, visitor_id_number
ORDER BY visit_count DESC;

-- View: Vehicle entry/exit tracking dashboard
-- Vista para dashboard de entrada/salida de vehículos por condominio
CREATE OR REPLACE VIEW vehicle_tracking AS
SELECT
    al.id,
    al.condominium_id,
    c.name as condominium_name,
    al.timestamp,
    al.direction,
    al.license_plate,
    al.plate_confidence,
    al.plate_image_url,
    al.vehicle_photo_url,
    v.brand as vehicle_brand,
    v.model as vehicle_model,
    v.color as vehicle_color,
    v.vehicle_type,
    COALESCE(r.full_name, al.visitor_full_name) as owner_or_visitor,
    r.apartment,
    al.access_decision,
    al.decision_reason,
    CASE
        WHEN v.id IS NOT NULL THEN 'registered'
        WHEN al.visitor_id IS NOT NULL THEN 'visitor'
        ELSE 'unknown'
    END as vehicle_status
FROM access_logs al
LEFT JOIN condominiums c ON al.condominium_id = c.id
LEFT JOIN vehicles v ON al.vehicle_id = v.id
LEFT JOIN residents r ON COALESCE(v.resident_id, al.resident_id) = r.id
WHERE al.entry_type = 'vehicle'
ORDER BY al.timestamp DESC;

-- View: Vehicle presence (who is currently inside)
-- Vista para saber qué vehículos están actualmente dentro del condominio
CREATE OR REPLACE VIEW vehicles_inside AS
WITH latest_movement AS (
    SELECT
        license_plate,
        condominium_id,
        direction,
        timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY license_plate, condominium_id
            ORDER BY timestamp DESC
        ) as rn
    FROM access_logs
    WHERE entry_type = 'vehicle'
    AND license_plate IS NOT NULL
)
SELECT
    lm.license_plate,
    lm.condominium_id,
    c.name as condominium_name,
    lm.timestamp as entry_time,
    v.brand,
    v.model,
    v.color,
    r.full_name as owner_name,
    r.apartment,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - lm.timestamp))/3600 as hours_inside
FROM latest_movement lm
LEFT JOIN condominiums c ON lm.condominium_id = c.id
LEFT JOIN vehicles v ON lm.license_plate = v.license_plate AND v.condominium_id = lm.condominium_id
LEFT JOIN residents r ON v.resident_id = r.id
WHERE lm.rn = 1
AND lm.direction = 'entry'
ORDER BY lm.timestamp DESC;

-- View: Daily entry/exit summary by condominium
-- Vista resumen diario de entradas/salidas por condominio
CREATE OR REPLACE VIEW daily_vehicle_summary AS
SELECT
    condominium_id,
    DATE(timestamp) as date,
    COUNT(CASE WHEN direction = 'entry' THEN 1 END) as total_entries,
    COUNT(CASE WHEN direction = 'exit' THEN 1 END) as total_exits,
    COUNT(DISTINCT license_plate) as unique_vehicles,
    COUNT(CASE WHEN direction = 'entry' AND vehicle_id IS NOT NULL THEN 1 END) as registered_entries,
    COUNT(CASE WHEN direction = 'entry' AND vehicle_id IS NULL THEN 1 END) as visitor_entries
FROM access_logs
WHERE entry_type = 'vehicle'
GROUP BY condominium_id, DATE(timestamp)
ORDER BY date DESC;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE condominiums IS 'Condominios (Multi-tenant principal)';
COMMENT ON TABLE attention_protocols IS 'Protocolos de atención configurables por condominio';
COMMENT ON TABLE residents IS 'Residentes de cada condominio';
COMMENT ON TABLE vehicles IS 'Vehículos autorizados por residente';
COMMENT ON TABLE access_logs IS 'CRÍTICO: Log completo de todos los accesos con OCR data';
COMMENT ON TABLE visitor_registry IS 'Registro permanente de visitantes con datos de cédula (OCR)';
COMMENT ON TABLE notifications IS 'Log de notificaciones enviadas (WhatsApp, Push, SMS)';
COMMENT ON TABLE system_events IS 'Eventos del sistema para auditoría y debugging';
