-- =====================================================
-- MIGRACIÓN: Función de Introspección de Schema
-- Ejecutar UNA VEZ en Supabase SQL Editor
-- Permite que el script Python obtenga el schema completo
-- =====================================================

-- Función que retorna el schema completo como JSON
CREATE OR REPLACE FUNCTION get_full_schema()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'fetched_at', now()::text,
        'tables', (
            SELECT jsonb_object_agg(
                t.table_name,
                jsonb_build_object(
                    'columns', (
                        SELECT jsonb_agg(
                            jsonb_build_object(
                                'name', c.column_name,
                                'type', c.data_type,
                                'nullable', c.is_nullable = 'YES',
                                'default', c.column_default,
                                'max_length', c.character_maximum_length
                            )
                            ORDER BY c.ordinal_position
                        )
                        FROM information_schema.columns c
                        WHERE c.table_schema = 'public'
                        AND c.table_name = t.table_name
                    ),
                    'primary_key', (
                        SELECT jsonb_agg(kcu.column_name)
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                        WHERE tc.table_schema = 'public'
                        AND tc.table_name = t.table_name
                        AND tc.constraint_type = 'PRIMARY KEY'
                    ),
                    'foreign_keys', (
                        SELECT jsonb_agg(
                            jsonb_build_object(
                                'column', kcu.column_name,
                                'references_table', ccu.table_name,
                                'references_column', ccu.column_name
                            )
                        )
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage ccu
                            ON tc.constraint_name = ccu.constraint_name
                        WHERE tc.table_schema = 'public'
                        AND tc.table_name = t.table_name
                        AND tc.constraint_type = 'FOREIGN KEY'
                    )
                )
            )
            FROM information_schema.tables t
            WHERE t.table_schema = 'public'
            AND t.table_type = 'BASE TABLE'
        ),
        'views', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'name', v.viewname,
                    'definition', v.definition
                )
            )
            FROM pg_views v
            WHERE v.schemaname = 'public'
        ),
        'indexes', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'name', i.indexname,
                    'table', i.tablename,
                    'definition', i.indexdef
                )
            )
            FROM pg_indexes i
            WHERE i.schemaname = 'public'
        ),
        'enums', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'name', t.typname,
                    'values', (
                        SELECT jsonb_agg(e.enumlabel ORDER BY e.enumsortorder)
                        FROM pg_enum e
                        WHERE e.enumtypid = t.oid
                    )
                )
            )
            FROM pg_type t
            JOIN pg_namespace n ON t.typnamespace = n.oid
            WHERE n.nspname = 'public'
            AND t.typtype = 'e'
        ),
        'row_counts', (
            SELECT jsonb_object_agg(
                relname,
                n_live_tup
            )
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
        )
    ) INTO result;

    RETURN result;
END;
$$;

-- Dar permisos para que service_role pueda ejecutarla
GRANT EXECUTE ON FUNCTION get_full_schema() TO service_role;

-- Verificar que se creó correctamente
SELECT 'Función get_full_schema() creada exitosamente' as status;
