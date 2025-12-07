-- ============================================
-- Migration: 004_add_evolution_config
-- Descripcion: Agrega configuracion de Evolution API por condominio
-- Fecha: 2025-12-06
-- ============================================

-- Agregar campo de extension PBX (para mapear llamadas a condominios)
ALTER TABLE condominiums ADD COLUMN IF NOT EXISTS pbx_extension VARCHAR(20);

-- Agregar campos de configuracion de Evolution API
ALTER TABLE condominiums ADD COLUMN IF NOT EXISTS evolution_api_url VARCHAR(500);
ALTER TABLE condominiums ADD COLUMN IF NOT EXISTS evolution_api_key VARCHAR(255);
ALTER TABLE condominiums ADD COLUMN IF NOT EXISTS evolution_instance_name VARCHAR(100);

-- Agregar campo para extension del operador
ALTER TABLE condominiums ADD COLUMN IF NOT EXISTS operator_extension VARCHAR(20) DEFAULT '1002';

-- Agregar campos de control de porton
ALTER TABLE condominiums ADD COLUMN IF NOT EXISTS gate_api_endpoint VARCHAR(500);
ALTER TABLE condominiums ADD COLUMN IF NOT EXISTS gate_api_key VARCHAR(255);

-- Comentarios
COMMENT ON COLUMN condominiums.pbx_extension IS 'Extension PBX/SIP asignada a este condominio (ej: 1000)';
COMMENT ON COLUMN condominiums.evolution_api_url IS 'URL del servidor Evolution API para este condominio';
COMMENT ON COLUMN condominiums.evolution_api_key IS 'API Key de Evolution API';
COMMENT ON COLUMN condominiums.evolution_instance_name IS 'Nombre de la instancia de WhatsApp en Evolution';
COMMENT ON COLUMN condominiums.operator_extension IS 'Extension SIP del operador humano para transferencias';
COMMENT ON COLUMN condominiums.gate_api_endpoint IS 'Endpoint API para control del porton';
COMMENT ON COLUMN condominiums.gate_api_key IS 'API Key para control del porton';

-- Crear indice para busqueda por extension PBX
CREATE INDEX IF NOT EXISTS idx_condominiums_pbx_extension ON condominiums(pbx_extension);

-- ============================================
-- Ejemplo de uso:
-- ============================================
-- UPDATE condominiums SET
--   evolution_api_url = 'https://evolution.miservidor.com',
--   evolution_api_key = 'api_key_aqui',
--   evolution_instance_name = 'sitnova-condoA',
--   operator_extension = '1002'
-- WHERE slug = 'los-almendros';
-- ============================================
