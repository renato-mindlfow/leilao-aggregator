-- ================================================================
-- CORREÇÃO DE QUALIDADE DE DADOS - LEILOHUB
-- ================================================================
-- Script SQL para normalizar categorias, cidades e bairros
-- Pode ser executado diretamente no Supabase SQL Editor
-- Data: 2025-01-06
-- ================================================================

-- ================================================================
-- PARTE 1: NORMALIZAR CATEGORIAS
-- ================================================================

-- 1.1 Limpar valores inválidos
UPDATE properties
SET category = 'Outro',
    updated_at = CURRENT_TIMESTAMP
WHERE (category IS NULL 
   OR category = '' 
   OR LOWER(category) = 'none'
   OR category = 'None')
  AND is_active = TRUE;

-- 1.2 Normalizar para Title Case
UPDATE properties
SET category = 'Apartamento',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'apartamento'
  AND category != 'Apartamento'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Casa',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'casa'
  AND category != 'Casa'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Terreno',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'terreno'
  AND category != 'Terreno'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Comercial',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'comercial'
  AND category != 'Comercial'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Rural',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) IN ('rural', 'imóvel rural', 'imovel rural')
  AND category != 'Rural'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Galpão',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) IN ('galpão', 'galpao')
  AND category != 'Galpão'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Outro',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) IN ('outro', 'outros')
  AND category != 'Outro'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Loja',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'loja'
  AND category != 'Loja'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Garagem',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'garagem'
  AND category != 'Garagem'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Área',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) IN ('área', 'area')
  AND category != 'Área'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Sala Comercial',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'sala comercial'
  AND category != 'Sala Comercial'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Prédio',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) IN ('prédio', 'predio')
  AND category != 'Prédio'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Chácara',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) IN ('chácara', 'chacara')
  AND category != 'Chácara'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Sítio',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) IN ('sítio', 'sitio')
  AND category != 'Sítio'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Fazenda',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'fazenda'
  AND category != 'Fazenda'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Cobertura',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'cobertura'
  AND category != 'Cobertura'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Kitnet',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'kitnet'
  AND category != 'Kitnet'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Flat',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'flat'
  AND category != 'Flat'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Box',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'box'
  AND category != 'Box'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Vaga de Garagem',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'vaga de garagem'
  AND category != 'Vaga de Garagem'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Estacionamento',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'estacionamento'
  AND category != 'Estacionamento'
  AND is_active = TRUE;

UPDATE properties
SET category = 'Industrial',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(category) = 'industrial'
  AND category != 'Industrial'
  AND is_active = TRUE;

-- ================================================================
-- PARTE 2: NORMALIZAR CIDADES
-- ================================================================

-- Normalizar todas as cidades para Title Case usando INITCAP()
UPDATE properties
SET city = INITCAP(city),
    updated_at = CURRENT_TIMESTAMP
WHERE city IS NOT NULL
  AND city != ''
  AND city != INITCAP(city)
  AND is_active = TRUE;

-- ================================================================
-- PARTE 3: NORMALIZAR BAIRROS
-- ================================================================

-- Normalizar todos os bairros para Title Case usando INITCAP()
UPDATE properties
SET neighborhood = INITCAP(neighborhood),
    updated_at = CURRENT_TIMESTAMP
WHERE neighborhood IS NOT NULL
  AND neighborhood != ''
  AND neighborhood != INITCAP(neighborhood)
  AND is_active = TRUE;

-- ================================================================
-- VERIFICAÇÃO DE QUALIDADE
-- ================================================================

-- Verificar se ainda há duplicatas de categorias
SELECT 
    LOWER(category) as category_lower,
    array_agg(DISTINCT category) as variants,
    COUNT(DISTINCT category) as variant_count,
    COUNT(*) as total_properties
FROM properties
WHERE is_active = TRUE
GROUP BY LOWER(category)
HAVING COUNT(DISTINCT category) > 1
ORDER BY total_properties DESC;

-- Se retornar 0 linhas, está OK! ✅

-- Verificar se ainda há duplicatas de cidades (top 20)
SELECT 
    LOWER(city) as city_lower,
    array_agg(DISTINCT city) as variants,
    COUNT(DISTINCT city) as variant_count,
    COUNT(*) as total_properties
FROM properties
WHERE is_active = TRUE
GROUP BY LOWER(city)
HAVING COUNT(DISTINCT city) > 1
ORDER BY total_properties DESC
LIMIT 20;

-- Se retornar 0 linhas, está OK! ✅

-- Verificar se ainda há duplicatas de bairros (top 20)
SELECT 
    LOWER(neighborhood) as neighborhood_lower,
    array_agg(DISTINCT neighborhood) as variants,
    COUNT(DISTINCT neighborhood) as variant_count,
    COUNT(*) as total_properties
FROM properties
WHERE is_active = TRUE
  AND neighborhood IS NOT NULL
  AND neighborhood != ''
GROUP BY LOWER(neighborhood)
HAVING COUNT(DISTINCT neighborhood) > 1
ORDER BY total_properties DESC
LIMIT 20;

-- Se retornar 0 linhas, está OK! ✅

-- ================================================================
-- RELATÓRIO FINAL
-- ================================================================

-- Categorias únicas
SELECT 
    category,
    COUNT(*) as total_properties,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM properties
WHERE is_active = TRUE
  AND category IS NOT NULL
GROUP BY category
ORDER BY total_properties DESC;

-- Resumo geral
SELECT 
    COUNT(*) as total_properties,
    COUNT(DISTINCT category) as unique_categories,
    COUNT(DISTINCT city) as unique_cities,
    COUNT(DISTINCT neighborhood) as unique_neighborhoods
FROM properties
WHERE is_active = TRUE;

-- ================================================================
-- FIM DO SCRIPT
-- ================================================================

