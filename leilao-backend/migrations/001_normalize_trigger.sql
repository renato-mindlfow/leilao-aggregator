-- ============================================
-- TRIGGER: Normalização automática de dados
-- ============================================

-- Função de normalização
CREATE OR REPLACE FUNCTION normalize_property_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Normalizar cidade para Title Case
    IF NEW.city IS NOT NULL THEN
        NEW.city := INITCAP(NEW.city);
    END IF;
    
    -- Normalizar bairro para Title Case
    IF NEW.neighborhood IS NOT NULL THEN
        NEW.neighborhood := INITCAP(NEW.neighborhood);
    END IF;
    
    -- Limpar URLs de imagem inválidas
    IF NEW.image_url IS NOT NULL THEN
        IF NEW.image_url LIKE '%connect.facebook.net%'
           OR NEW.image_url LIKE '%facebook.com%'
           OR NEW.image_url LIKE '%bank_icons%'
           OR LOWER(NEW.image_url) LIKE '%logo%'
           OR LOWER(NEW.image_url) LIKE '%placeholder%'
           OR LOWER(NEW.image_url) LIKE '%no-image%'
           OR LOWER(NEW.image_url) LIKE '%sem-foto%'
           OR LENGTH(NEW.image_url) < 20
        THEN
            NEW.image_url := NULL;
        END IF;
    END IF;
    
    -- Garantir source_url para imóveis da Caixa
    IF NEW.id LIKE 'caixa-%' AND (NEW.source_url IS NULL OR NEW.source_url = '') THEN
        NEW.source_url := 'https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=' || REPLACE(NEW.id, 'caixa-', '');
    END IF;
    
    -- Atualizar timestamp
    NEW.updated_at := NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Remover trigger existente se houver
DROP TRIGGER IF EXISTS trigger_normalize_property ON properties;

-- Criar trigger para INSERT e UPDATE
CREATE TRIGGER trigger_normalize_property
    BEFORE INSERT OR UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION normalize_property_data();

-- Comentário
COMMENT ON FUNCTION normalize_property_data() IS 'Normaliza dados de propriedades automaticamente (cidade, bairro, imagem, URL)';

