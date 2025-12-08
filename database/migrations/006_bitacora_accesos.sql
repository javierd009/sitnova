-- =====================================================
-- MIGRATION 006: Bitácora de Accesos
-- =====================================================
-- Tabla para registrar todos los intentos de acceso al condominio
-- con información detallada del visitante y resultado
-- =====================================================

-- Crear tipo enum para resultado de acceso
DO $$ BEGIN
    CREATE TYPE access_result AS ENUM (
        'autorizado',      -- Residente autorizó
        'denegado',        -- Residente denegó
        'pre_autorizado',  -- Visitante tenía pre-autorización
        'timeout',         -- Sin respuesta del residente
        'transferido',     -- Transferido a operador
        'error'            -- Error técnico
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Crear tipo enum para tipo de visitante
DO $$ BEGIN
    CREATE TYPE visitor_type AS ENUM (
        'persona',         -- Visitante a pie
        'vehiculo',        -- Vehículo
        'delivery',        -- Entrega/Mensajería
        'servicio',        -- Servicio técnico
        'otro'             -- Otro
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Tabla principal de bitácora
CREATE TABLE IF NOT EXISTS bitacora_accesos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Información del condominio
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,

    -- Información del visitante
    visitor_name VARCHAR(255),
    visitor_cedula VARCHAR(50),
    visitor_phone VARCHAR(50),
    visitor_type visitor_type DEFAULT 'persona',

    -- Información del vehículo (si aplica)
    vehicle_plate VARCHAR(20),
    vehicle_type VARCHAR(50),
    vehicle_color VARCHAR(50),

    -- Destino
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    resident_name VARCHAR(255),
    apartment VARCHAR(50),

    -- Motivo de visita
    visit_reason TEXT,

    -- Resultado del acceso
    access_result access_result NOT NULL,

    -- Información de la llamada
    call_id VARCHAR(100),          -- ID de la llamada en AsterSIPVox
    call_duration_seconds INTEGER, -- Duración de la llamada
    call_recording_url TEXT,       -- URL de grabación (si está habilitada)

    -- Autorización
    authorized_by VARCHAR(100),    -- Quién autorizó (residente, pre-auth, operador)
    authorization_method VARCHAR(50), -- whatsapp, llamada, pre-auth

    -- Operador (si fue transferido)
    operator_id UUID,
    operator_notes TEXT,

    -- Metadatos
    ip_address INET,
    user_agent TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Para búsqueda
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('spanish', coalesce(visitor_name, '')), 'A') ||
        setweight(to_tsvector('spanish', coalesce(resident_name, '')), 'B') ||
        setweight(to_tsvector('spanish', coalesce(apartment, '')), 'C') ||
        setweight(to_tsvector('spanish', coalesce(visit_reason, '')), 'D')
    ) STORED
);

-- Índices para búsqueda y filtrado
CREATE INDEX IF NOT EXISTS idx_bitacora_condominium ON bitacora_accesos(condominium_id);
CREATE INDEX IF NOT EXISTS idx_bitacora_created_at ON bitacora_accesos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bitacora_visitor_cedula ON bitacora_accesos(visitor_cedula);
CREATE INDEX IF NOT EXISTS idx_bitacora_vehicle_plate ON bitacora_accesos(vehicle_plate);
CREATE INDEX IF NOT EXISTS idx_bitacora_result ON bitacora_accesos(access_result);
CREATE INDEX IF NOT EXISTS idx_bitacora_apartment ON bitacora_accesos(apartment);
CREATE INDEX IF NOT EXISTS idx_bitacora_search ON bitacora_accesos USING GIN(search_vector);

-- Índice para búsqueda por fecha (para reportes)
CREATE INDEX IF NOT EXISTS idx_bitacora_date ON bitacora_accesos(DATE(created_at));

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_bitacora_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_bitacora_updated_at ON bitacora_accesos;
CREATE TRIGGER trigger_bitacora_updated_at
    BEFORE UPDATE ON bitacora_accesos
    FOR EACH ROW
    EXECUTE FUNCTION update_bitacora_updated_at();

-- Row Level Security
ALTER TABLE bitacora_accesos ENABLE ROW LEVEL SECURITY;

-- Política: Usuarios autenticados solo ven registros de su condominio
CREATE POLICY bitacora_select_policy ON bitacora_accesos
    FOR SELECT
    USING (
        condominium_id IN (
            SELECT condominium_id FROM user_condominiums
            WHERE user_id = auth.uid()
        )
    );

-- Política: Service role puede todo
CREATE POLICY bitacora_service_policy ON bitacora_accesos
    FOR ALL
    USING (auth.role() = 'service_role');

-- Vista para estadísticas diarias
CREATE OR REPLACE VIEW bitacora_estadisticas_diarias AS
SELECT
    condominium_id,
    DATE(created_at) as fecha,
    COUNT(*) as total_accesos,
    COUNT(*) FILTER (WHERE access_result = 'autorizado') as autorizados,
    COUNT(*) FILTER (WHERE access_result = 'denegado') as denegados,
    COUNT(*) FILTER (WHERE access_result = 'pre_autorizado') as pre_autorizados,
    COUNT(*) FILTER (WHERE access_result = 'timeout') as sin_respuesta,
    COUNT(*) FILTER (WHERE access_result = 'transferido') as transferidos,
    COUNT(*) FILTER (WHERE visitor_type = 'vehiculo') as vehiculos,
    COUNT(*) FILTER (WHERE visitor_type = 'delivery') as deliveries,
    AVG(call_duration_seconds) as duracion_promedio_llamada
FROM bitacora_accesos
GROUP BY condominium_id, DATE(created_at);

-- Vista para últimos accesos (para dashboard)
CREATE OR REPLACE VIEW bitacora_ultimos_accesos AS
SELECT
    b.id,
    b.condominium_id,
    c.name as condominium_name,
    b.visitor_name,
    b.visitor_cedula,
    b.visitor_type,
    b.vehicle_plate,
    b.resident_name,
    b.apartment,
    b.visit_reason,
    b.access_result,
    b.authorization_method,
    b.call_duration_seconds,
    b.created_at
FROM bitacora_accesos b
LEFT JOIN condominiums c ON b.condominium_id = c.id
ORDER BY b.created_at DESC;

-- Función para registrar acceso (usada por la API)
CREATE OR REPLACE FUNCTION registrar_acceso(
    p_condominium_id UUID,
    p_visitor_name VARCHAR(255),
    p_visitor_cedula VARCHAR(50),
    p_apartment VARCHAR(50),
    p_visit_reason TEXT,
    p_access_result access_result,
    p_visitor_type visitor_type DEFAULT 'persona',
    p_vehicle_plate VARCHAR(20) DEFAULT NULL,
    p_resident_name VARCHAR(255) DEFAULT NULL,
    p_call_id VARCHAR(100) DEFAULT NULL,
    p_call_duration INTEGER DEFAULT NULL,
    p_authorization_method VARCHAR(50) DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
    v_resident_id UUID;
BEGIN
    -- Buscar resident_id si hay apartment
    IF p_apartment IS NOT NULL THEN
        SELECT id INTO v_resident_id
        FROM residents
        WHERE condominium_id = p_condominium_id
        AND apartment = p_apartment
        LIMIT 1;
    END IF;

    -- Insertar registro
    INSERT INTO bitacora_accesos (
        condominium_id,
        visitor_name,
        visitor_cedula,
        visitor_type,
        vehicle_plate,
        resident_id,
        resident_name,
        apartment,
        visit_reason,
        access_result,
        call_id,
        call_duration_seconds,
        authorization_method
    ) VALUES (
        p_condominium_id,
        p_visitor_name,
        p_visitor_cedula,
        p_visitor_type,
        p_vehicle_plate,
        v_resident_id,
        COALESCE(p_resident_name, (SELECT name FROM residents WHERE id = v_resident_id)),
        p_apartment,
        p_visit_reason,
        p_access_result,
        p_call_id,
        p_call_duration,
        p_authorization_method
    ) RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant para la función
GRANT EXECUTE ON FUNCTION registrar_acceso TO authenticated, service_role;

-- Comentarios
COMMENT ON TABLE bitacora_accesos IS 'Registro completo de todos los intentos de acceso al condominio';
COMMENT ON COLUMN bitacora_accesos.access_result IS 'Resultado: autorizado, denegado, pre_autorizado, timeout, transferido, error';
COMMENT ON COLUMN bitacora_accesos.visitor_type IS 'Tipo: persona, vehiculo, delivery, servicio, otro';
COMMENT ON VIEW bitacora_estadisticas_diarias IS 'Estadísticas agregadas por día para reportes';
COMMENT ON VIEW bitacora_ultimos_accesos IS 'Vista optimizada para mostrar últimos accesos en dashboard';

-- Verificación
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'bitacora_accesos') THEN
        RAISE NOTICE '✅ Tabla bitacora_accesos creada correctamente';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'bitacora_estadisticas_diarias') THEN
        RAISE NOTICE '✅ Vista bitacora_estadisticas_diarias creada correctamente';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'bitacora_ultimos_accesos') THEN
        RAISE NOTICE '✅ Vista bitacora_ultimos_accesos creada correctamente';
    END IF;
END $$;
