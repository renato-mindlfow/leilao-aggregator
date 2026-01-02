-- =============================================================
-- ADICIONA COLUNAS PARA CONTROLE DE GEOCODING ASSÍNCRONO
-- Execute este SQL no Supabase SQL Editor
-- =============================================================

-- Adiciona coluna de status de geocoding
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS geocoding_status VARCHAR(20) DEFAULT 'pending';

-- Adiciona coluna de tentativas de geocoding
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS geocoding_attempts INTEGER DEFAULT 0;

-- Adiciona coluna de último erro de geocoding
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS geocoding_error TEXT;

-- Adiciona coluna de quando foi geocodificado
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMP;

-- Índice para buscar pendentes de geocoding
CREATE INDEX IF NOT EXISTS idx_properties_geocoding_pending 
ON properties(geocoding_status) 
WHERE geocoding_status = 'pending';

-- Atualiza imóveis existentes que já têm coordenadas
UPDATE properties 
SET geocoding_status = 'done', geocoded_at = NOW()
WHERE latitude IS NOT NULL 
  AND longitude IS NOT NULL 
  AND geocoding_status = 'pending';

-- Atualiza imóveis sem endereço (não precisam de geocoding)
UPDATE properties 
SET geocoding_status = 'skipped'
WHERE (address IS NULL OR address = '')
  AND (city IS NULL OR city = '')
  AND geocoding_status = 'pending';

-- Verifica resultado
SELECT 
    geocoding_status,
    COUNT(*) as total
FROM properties
GROUP BY geocoding_status
ORDER BY total DESC;

