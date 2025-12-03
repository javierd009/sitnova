-- ============================================
-- Migration: 003_add_address_to_residents
-- Descripcion: Agrega campos de direccion a la tabla residents
-- Fecha: 2024-12-03
-- ============================================

-- Agregar campo de direccion a residents (para indicaciones de llegada)
ALTER TABLE residents ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE residents ADD COLUMN IF NOT EXISTS address_instructions TEXT;

-- Comentarios para documentar
COMMENT ON COLUMN residents.address IS 'Direccion fisica de la casa/apartamento (ej: "Condominio Las Palmas, Bloque 3")';
COMMENT ON COLUMN residents.address_instructions IS 'Instrucciones para llegar (ej: "Segunda casa despues de la piscina, porton verde")';

-- Crear indice para busquedas por apartamento (si no existe)
CREATE INDEX IF NOT EXISTS idx_residents_apartment ON residents(apartment);

-- ============================================
-- Ejemplos de uso:
-- ============================================
-- UPDATE residents SET
--   address_instructions = 'Segunda casa a la derecha despues de la piscina'
-- WHERE apartment = '10';
--
-- El agente de voz usara address_instructions para dar indicaciones
-- al visitante una vez que el residente autorice el acceso.
-- ============================================
