-- ============================================
-- Script de Limpeza de Dados Inválidos
-- ============================================
-- Este script limpa descontos inválidos (negativos ou maiores que 100%)
-- e recalcula descontos onde possível.
--
-- Execute este script no Supabase SQL Editor
-- ============================================

-- 1. Limpar descontos inválidos (negativos ou maiores que 100%)
UPDATE properties
SET discount_percentage = NULL
WHERE discount_percentage < 0 OR discount_percentage > 100;

-- 2. Recalcular descontos onde possível
UPDATE properties
SET discount_percentage = ROUND(
  ((evaluation_value - COALESCE(second_auction_value, first_auction_value)) / evaluation_value) * 100,
  2
)
WHERE evaluation_value > 0 
  AND evaluation_value > COALESCE(second_auction_value, first_auction_value)
  AND (discount_percentage IS NULL OR discount_percentage < 0 OR discount_percentage > 100);

-- 3. Verificar resultado
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN discount_percentage IS NOT NULL AND discount_percentage BETWEEN 0 AND 100 THEN 1 END) as validos,
  COUNT(CASE WHEN discount_percentage IS NULL THEN 1 END) as sem_desconto,
  MAX(discount_percentage) as maior_desconto
FROM properties;



