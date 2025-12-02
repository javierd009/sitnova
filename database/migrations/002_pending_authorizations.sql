-- =====================================================
-- SITNOVA - Pending Authorizations Table
-- Migration: 002
-- Description: Table for storing pending authorization requests
--              Persists across container restarts
-- =====================================================

-- Create table for pending authorizations
CREATE TABLE IF NOT EXISTS pending_authorizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Phone number (unique key for lookups)
    phone VARCHAR(20) NOT NULL,

    -- Authorization details
    apartment VARCHAR(100) NOT NULL,
    visitor_name VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pendiente',  -- pendiente, autorizado, denegado, mensaje, expirado

    -- Custom message from resident
    mensaje_personalizado TEXT,

    -- OCR data (optional)
    cedula VARCHAR(50),
    placa VARCHAR(20),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP WITH TIME ZONE,

    -- For TTL cleanup (auto-expire old records)
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 minutes'),

    -- Index for fast phone lookups
    CONSTRAINT unique_phone_pending UNIQUE(phone)
);

-- Index for phone number lookups (the most common query)
CREATE INDEX IF NOT EXISTS idx_pending_auth_phone ON pending_authorizations(phone);

-- Index for apartment lookups
CREATE INDEX IF NOT EXISTS idx_pending_auth_apartment ON pending_authorizations(apartment);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_pending_auth_status ON pending_authorizations(status);

-- Index for cleanup queries (find expired records)
CREATE INDEX IF NOT EXISTS idx_pending_auth_expires ON pending_authorizations(expires_at);

-- Function to clean up expired authorizations (run periodically)
CREATE OR REPLACE FUNCTION cleanup_expired_authorizations()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM pending_authorizations
    WHERE expires_at < CURRENT_TIMESTAMP
    AND status = 'pendiente';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Optional: Create a scheduled job to clean up (requires pg_cron extension)
-- SELECT cron.schedule('cleanup-pending-auth', '*/5 * * * *', 'SELECT cleanup_expired_authorizations()');

-- Comment
COMMENT ON TABLE pending_authorizations IS 'Pending authorization requests from visitors awaiting resident response via WhatsApp';
