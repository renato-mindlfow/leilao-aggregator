-- =============================================================
-- MARCA ENDEREÇOS INVÁLIDOS PARA GEOCODING
-- Execute este SQL no Supabase SQL Editor
-- =============================================================

-- 1. Marcar endereços com texto promocional
UPDATE properties
SET geocoding_status = 'invalid_address'
WHERE address ILIKE '%ENTRE EM CONTATO%'
   OR address ILIKE '%WHATSAPP%'
   OR address ILIKE '%WWW.%'
   OR address ILIKE '%GRUPOLANCE%'
   OR address ILIKE '%MAIS INFORMAÇÕES%'
   OR address ILIKE '%.COM.BR%'
   OR address ILIKE '%DENTRE OUTRAS%';

-- 2. Marcar endereços de escritórios de leiloeiros
UPDATE properties
SET geocoding_status = 'invalid_address'
WHERE address ILIKE '%Serra de Botucatu, 880%'
   OR address ILIKE '%sala 1208, vila gomes cardim%';

-- 3. Verificar quantos foram marcados
SELECT geocoding_status, COUNT(*) 
FROM properties 
GROUP BY geocoding_status
ORDER BY COUNT(*) DESC;

-- 4. Verificar endereços problemáticos restantes
SELECT DISTINCT LEFT(address, 100) as endereco_truncado, COUNT(*)
FROM properties
WHERE geocoding_status = 'failed'
GROUP BY LEFT(address, 100)
ORDER BY COUNT(*) DESC
LIMIT 20;

