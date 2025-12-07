-- =====================================================
-- MIGRACION 005: Vehicle Entry/Exit Tracking
-- Fecha: 2025-12-06
-- Descripcion: Agrega tracking de entrada/salida de vehiculos
-- NOTA: Versión simplificada compatible con schema de producción
-- =====================================================

-- =====================================================
-- PASO 1: Agregar campo direction a access_logs
-- =====================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'access_logs' AND column_name = 'direction'
    ) THEN
        ALTER TABLE access_logs
        ADD COLUMN direction VARCHAR(10) NOT NULL DEFAULT 'entry';
        RAISE NOTICE 'Columna direction agregada a access_logs';
    ELSE
        RAISE NOTICE 'Columna direction ya existe en access_logs';
    END IF;
END $$;

-- Constraint para valores validos
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'access_logs_direction_check'
    ) THEN
        ALTER TABLE access_logs
        ADD CONSTRAINT access_logs_direction_check
        CHECK (direction IN ('entry', 'exit'));
        RAISE NOTICE 'Constraint direction_check agregado';
    END IF;
END $$;

-- =====================================================
-- PASO 2: Indices
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_access_logs_direction
ON access_logs(direction);

CREATE INDEX IF NOT EXISTS idx_access_logs_vehicle_tracking
ON access_logs(condominium_id, entry_type, direction, created_at DESC)
WHERE entry_type = 'vehicle';

-- =====================================================
-- PASO 3: Vista vehicle_tracking (SIMPLIFICADA)
-- =====================================================
-- Solo usa columnas que existen en produccion

CREATE OR REPLACE VIEW vehicle_tracking AS
SELECT
    al.id,
    al.condominium_id,
    c.name as condominium_name,
    al.created_at as timestamp,
    al.direction,
    al.license_plate,
    al.access_decision,
    -- JOIN por placa para obtener info del vehiculo registrado
    v.brand as vehicle_brand,
    v.model as vehicle_model,
    v.color as vehicle_color,
    r.full_name as owner_name,
    r.apartment,
    CASE
        WHEN v.id IS NOT NULL THEN 'registered'
        ELSE 'visitor'
    END as vehicle_status
FROM access_logs al
LEFT JOIN condominiums c ON al.condominium_id = c.id
LEFT JOIN vehicles v ON al.license_plate = v.license_plate AND v.condominium_id = al.condominium_id
LEFT JOIN residents r ON v.resident_id = r.id
WHERE al.entry_type = 'vehicle'
ORDER BY al.created_at DESC;

-- =====================================================
-- PASO 4: Vista vehicles_inside (SIMPLIFICADA)
-- =====================================================

CREATE OR REPLACE VIEW vehicles_inside AS
WITH latest_movement AS (
    SELECT
        license_plate,
        condominium_id,
        direction,
        created_at,
        ROW_NUMBER() OVER (
            PARTITION BY license_plate, condominium_id
            ORDER BY created_at DESC
        ) as rn
    FROM access_logs
    WHERE entry_type = 'vehicle'
    AND license_plate IS NOT NULL
)
SELECT
    lm.license_plate,
    lm.condominium_id,
    c.name as condominium_name,
    lm.created_at as entry_time,
    v.brand,
    v.model,
    v.color,
    r.full_name as owner_name,
    r.apartment,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - lm.created_at))/3600 as hours_inside
FROM latest_movement lm
LEFT JOIN condominiums c ON lm.condominium_id = c.id
LEFT JOIN vehicles v ON lm.license_plate = v.license_plate AND v.condominium_id = lm.condominium_id
LEFT JOIN residents r ON v.resident_id = r.id
WHERE lm.rn = 1
AND lm.direction = 'entry'
ORDER BY lm.created_at DESC;

-- =====================================================
-- PASO 5: Vista daily_vehicle_summary (SIMPLIFICADA)
-- =====================================================

CREATE OR REPLACE VIEW daily_vehicle_summary AS
SELECT
    al.condominium_id,
    DATE(al.created_at) as date,
    COUNT(CASE WHEN al.direction = 'entry' THEN 1 END) as total_entries,
    COUNT(CASE WHEN al.direction = 'exit' THEN 1 END) as total_exits,
    COUNT(DISTINCT al.license_plate) as unique_vehicles,
    -- Contar registrados vs visitantes usando JOIN por placa
    COUNT(CASE WHEN al.direction = 'entry' AND v.id IS NOT NULL THEN 1 END) as registered_entries,
    COUNT(CASE WHEN al.direction = 'entry' AND v.id IS NULL THEN 1 END) as visitor_entries
FROM access_logs al
LEFT JOIN vehicles v ON al.license_plate = v.license_plate AND v.condominium_id = al.condominium_id
WHERE al.entry_type = 'vehicle'
GROUP BY al.condominium_id, DATE(al.created_at)
ORDER BY date DESC;

-- =====================================================
-- PASO 6: Comentarios
-- =====================================================

COMMENT ON COLUMN access_logs.direction IS 'Direccion: entry (entrada) o exit (salida)';
COMMENT ON VIEW vehicle_tracking IS 'Historial de movimientos de vehiculos';
COMMENT ON VIEW vehicles_inside IS 'Vehiculos actualmente dentro del condominio';
COMMENT ON VIEW daily_vehicle_summary IS 'Resumen diario de entradas/salidas';

-- =====================================================
-- VERIFICACION
-- =====================================================

DO $$
DECLARE
    col_exists boolean;
    view1_exists boolean;
    view2_exists boolean;
    view3_exists boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'access_logs' AND column_name = 'direction'
    ) INTO col_exists;

    SELECT EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'vehicle_tracking') INTO view1_exists;
    SELECT EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'vehicles_inside') INTO view2_exists;
    SELECT EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'daily_vehicle_summary') INTO view3_exists;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'VERIFICACION DE MIGRACION 005';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Campo direction: %', CASE WHEN col_exists THEN 'OK' ELSE 'FALTA' END;
    RAISE NOTICE 'Vista vehicle_tracking: %', CASE WHEN view1_exists THEN 'OK' ELSE 'FALTA' END;
    RAISE NOTICE 'Vista vehicles_inside: %', CASE WHEN view2_exists THEN 'OK' ELSE 'FALTA' END;
    RAISE NOTICE 'Vista daily_vehicle_summary: %', CASE WHEN view3_exists THEN 'OK' ELSE 'FALTA' END;
    RAISE NOTICE '========================================';

    IF col_exists AND view1_exists AND view2_exists AND view3_exists THEN
        RAISE NOTICE 'MIGRACION 005 COMPLETADA EXITOSAMENTE';
    ELSE
        RAISE WARNING 'MIGRACION INCOMPLETA - Revisar logs';
    END IF;
END $$;
