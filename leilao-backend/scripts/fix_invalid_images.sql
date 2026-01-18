-- ============================================
-- Script de Limpeza de Imagens Inválidas
-- ============================================
-- Este script marca como NULL todas as image_url que são:
-- - Logos/ícones de leiloeiros (logo, icon, favicon, etc.)
-- - Placeholders (placeholder, no-image, sem-foto, etc.)
-- - URLs muito curtas (< 20 caracteres)
-- - URLs com dimensões pequenas (16x16, 32x32, 48x48, 64x64)
--
-- Execute este script no Supabase SQL Editor
-- ============================================

-- 1. Identificar e limpar URLs com padrões de logo/ícone/placeholder
UPDATE properties
SET image_url = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE image_url IS NOT NULL
  AND (
    -- Padrões de texto na URL
    LOWER(image_url) LIKE '%logo%'
    OR LOWER(image_url) LIKE '%icon%'
    OR LOWER(image_url) LIKE '%favicon%'
    OR LOWER(image_url) LIKE '%placeholder%'
    OR LOWER(image_url) LIKE '%no-image%'
    OR LOWER(image_url) LIKE '%noimage%'
    OR LOWER(image_url) LIKE '%sem-foto%'
    OR LOWER(image_url) LIKE '%semfoto%'
    OR LOWER(image_url) LIKE '%banner%'
    OR LOWER(image_url) LIKE '%header%'
    OR LOWER(image_url) LIKE '%footer%'
    OR LOWER(image_url) LIKE '%loading%'
    OR LOWER(image_url) LIKE '%spinner%'
    OR LOWER(image_url) LIKE '%default%'
    OR LOWER(image_url) LIKE '%blank%'
    OR LOWER(image_url) LIKE '%empty%'
    -- URLs muito curtas (provavelmente inválidas)
    OR LENGTH(image_url) < 20
    -- Dimensões pequenas no nome da URL (16x16, 32x32, 48x48, 64x64)
    OR image_url LIKE '%16x16%'
    OR image_url LIKE '%32x32%'
    OR image_url LIKE '%48x48%'
    OR image_url LIKE '%64x64%'
  );

-- 2. Limpar URLs que são apenas domínios ou caminhos muito simples
UPDATE properties
SET image_url = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE image_url IS NOT NULL
  AND (
    -- URLs que terminam com apenas .com, .br, etc sem caminho
    image_url ~ '^https?://[^/]+\.(com|br|net|org)$'
    -- URLs que são só caminhos relativos simples
    OR (image_url NOT LIKE 'http%' AND LENGTH(image_url) < 30)
  );

-- 3. Verificar resultado
SELECT 
  COUNT(*) as total_properties,
  COUNT(CASE WHEN image_url IS NOT NULL THEN 1 END) as com_imagem,
  COUNT(CASE WHEN image_url IS NULL THEN 1 END) as sem_imagem,
  ROUND(
    (COUNT(CASE WHEN image_url IS NULL THEN 1 END)::FLOAT / COUNT(*)::FLOAT) * 100,
    2
  ) as percentual_sem_imagem
FROM properties
WHERE is_active = TRUE;

-- 4. Estatísticas por categoria
SELECT 
  category,
  COUNT(*) as total,
  COUNT(CASE WHEN image_url IS NOT NULL THEN 1 END) as com_imagem,
  COUNT(CASE WHEN image_url IS NULL THEN 1 END) as sem_imagem
FROM properties
WHERE is_active = TRUE
GROUP BY category
ORDER BY sem_imagem DESC;

-- ============================================
-- Trigger para validar automaticamente novas imagens
-- ============================================
-- Este trigger valida automaticamente imagens inseridas ou atualizadas

CREATE OR REPLACE FUNCTION validate_image_url()
RETURNS TRIGGER AS $$
BEGIN
  -- Se image_url é NULL, permitir
  IF NEW.image_url IS NULL THEN
    RETURN NEW;
  END IF;
  
  -- Se URL é muito curta, marcar como NULL
  IF LENGTH(NEW.image_url) < 20 THEN
    NEW.image_url := NULL;
    RETURN NEW;
  END IF;
  
  -- Se contém padrões inválidos, marcar como NULL
  IF (
    LOWER(NEW.image_url) LIKE '%logo%'
    OR LOWER(NEW.image_url) LIKE '%icon%'
    OR LOWER(NEW.image_url) LIKE '%favicon%'
    OR LOWER(NEW.image_url) LIKE '%placeholder%'
    OR LOWER(NEW.image_url) LIKE '%no-image%'
    OR LOWER(NEW.image_url) LIKE '%noimage%'
    OR LOWER(NEW.image_url) LIKE '%sem-foto%'
    OR LOWER(NEW.image_url) LIKE '%banner%'
    OR LOWER(NEW.image_url) LIKE '%header%'
    OR LOWER(NEW.image_url) LIKE '%footer%'
    OR LOWER(NEW.image_url) LIKE '%loading%'
    OR LOWER(NEW.image_url) LIKE '%spinner%'
    OR NEW.image_url LIKE '%16x16%'
    OR NEW.image_url LIKE '%32x32%'
    OR NEW.image_url LIKE '%48x48%'
    OR NEW.image_url LIKE '%64x64%'
  ) THEN
    NEW.image_url := NULL;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger se não existir
DROP TRIGGER IF EXISTS trigger_validate_image_url ON properties;
CREATE TRIGGER trigger_validate_image_url
  BEFORE INSERT OR UPDATE ON properties
  FOR EACH ROW
  EXECUTE FUNCTION validate_image_url();

-- ============================================
-- Fim do Script
-- ============================================
