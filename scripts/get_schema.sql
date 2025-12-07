-- =====================================================
-- SCRIPT: Obtener Schema de Producción
-- Ejecutar en Supabase SQL Editor ANTES de hacer migraciones
-- Copiar el resultado y pegarlo para análisis
-- =====================================================

-- 1. LISTAR TODAS LAS TABLAS
SELECT
    '=== TABLAS ===' as info;

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 2. COLUMNAS DE CADA TABLA (las más importantes)
SELECT
    '=== COLUMNAS POR TABLA ===' as info;

SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN (
    'access_logs',
    'condominiums',
    'residents',
    'vehicles',
    'pre_authorized_visitors',
    'visitor_registry',
    'notifications',
    'pending_authorizations'
)
ORDER BY table_name, ordinal_position;

-- 3. VISTAS EXISTENTES
SELECT
    '=== VISTAS ===' as info;

SELECT
    viewname
FROM pg_views
WHERE schemaname = 'public';

-- 4. INDICES EN ACCESS_LOGS
SELECT
    '=== INDICES EN ACCESS_LOGS ===' as info;

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'access_logs';

-- 5. CONSTRAINTS EN ACCESS_LOGS
SELECT
    '=== CONSTRAINTS EN ACCESS_LOGS ===' as info;

SELECT
    conname as constraint_name,
    contype as type
FROM pg_constraint
WHERE conrelid = 'access_logs'::regclass;
