-- ============================================================
-- LEILOHUB - CAMPOS DE AUDITORIA E TRIGGER DE NORMALIZAÇÃO
-- Data: 2026-01-21
-- Execute este script no Supabase SQL Editor
-- ============================================================

-- ============================================================
-- PARTE 1: ADICIONAR CAMPOS DE AUDITORIA À TABELA PROPERTIES
-- ============================================================

-- Adicionar campos de auditoria
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_errors TEXT[];
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_warnings TEXT[];
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_timestamp TIMESTAMP;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS audit_version VARCHAR(10);

-- Criar índice para busca por status de auditoria
CREATE INDEX IF NOT EXISTS idx_properties_audit_status ON properties(audit_status);

-- Comentários para documentação
COMMENT ON COLUMN properties.audit_status IS 'Status da auditoria: pending, passed, failed';
COMMENT ON COLUMN properties.audit_errors IS 'Array de erros encontrados na auditoria';
COMMENT ON COLUMN properties.audit_warnings IS 'Array de avisos (não bloqueiam commit)';
COMMENT ON COLUMN properties.audit_timestamp IS 'Data/hora da última auditoria';
COMMENT ON COLUMN properties.audit_version IS 'Versão das regras de auditoria usadas';

-- ============================================================
-- PARTE 2: FUNÇÃO DE NORMALIZAÇÃO AUTOMÁTICA
-- ============================================================

-- Função de normalização
CREATE OR REPLACE FUNCTION normalize_property_data()
RETURNS TRIGGER AS $$
DECLARE
    state_corrections JSONB := '{
        "Sã": "SP", "Sa": "SP", "Sp": "SP", "sp": "SP",
        "Ri": "RJ", "Rj": "RJ", "rj": "RJ",
        "Mi": "MG", "Mg": "MG", "mg": "MG",
        "Go": "GO", "go": "GO",
        "Ba": "BA", "ba": "BA",
        "Ce": "CE", "ce": "CE",
        "Pe": "PE", "pe": "PE",
        "Ma": "MA", "ma": "MA",
        "Pr": "PR", "pr": "PR",
        "Pa": "PA", "pa": "PA",
        "Rs": "RS", "rs": "RS",
        "Sc": "SC", "sc": "SC",
        "Es": "ES", "es": "ES",
        "Mt": "MT", "mt": "MT",
        "Ms": "MS", "ms": "MS",
        "Df": "DF", "df": "DF", "Di": "DF", "di": "DF",
        "Se": "SE", "se": "SE",
        "Ro": "RO", "ro": "RO",
        "To": "TO", "to": "TO",
        "Pi": "PI", "pi": "PI",
        "Al": "AL", "al": "AL",
        "Rn": "RN", "rn": "RN",
        "Pb": "PB", "pb": "PB",
        "Am": "AM", "am": "AM",
        "Ap": "AP", "ap": "AP",
        "Rr": "RR", "rr": "RR",
        "Ac": "AC", "ac": "AC"
    }';
    corrected_state TEXT;
BEGIN
    -- ========================================
    -- 1. NORMALIZAR ESTADO
    -- ========================================
    
    IF NEW.state IS NOT NULL AND NEW.state != '' THEN
        -- Primeiro tentar correção do mapa
        corrected_state := state_corrections ->> NEW.state;
        
        IF corrected_state IS NOT NULL THEN
            NEW.state := corrected_state;
        ELSE
            -- Se não encontrou no mapa, apenas fazer UPPERCASE
            NEW.state := UPPER(NEW.state);
        END IF;
        
        -- Rejeitar valores inválidos conhecidos (setar para NULL)
        IF NEW.state IN ('XX', 'NI', 'NA', 'UF', 'NÃ', 'NÂ') THEN
            NEW.state := NULL;
        END IF;
        
        -- Validar se é um estado válido do Brasil
        IF NEW.state IS NOT NULL AND NEW.state NOT IN (
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ) THEN
            -- Estado não reconhecido - manter NULL para revisão manual
            NEW.state := NULL;
        END IF;
    END IF;
    
    -- ========================================
    -- 2. NORMALIZAR CATEGORIA (Title Case)
    -- ========================================
    
    IF NEW.category IS NOT NULL THEN
        NEW.category := INITCAP(LOWER(NEW.category));
    END IF;
    
    -- ========================================
    -- 3. NORMALIZAR CIDADE (Title Case)
    -- ========================================
    
    IF NEW.city IS NOT NULL THEN
        -- Remover estado do final se presente (ex: "São Paulo - SP")
        IF NEW.city ~ '\s*-\s*[A-Za-z]{2}\s*$' THEN
            -- Se estado está vazio, extrair da cidade
            IF NEW.state IS NULL OR NEW.state = '' THEN
                NEW.state := UPPER(TRIM(REGEXP_REPLACE(NEW.city, '.*\s*-\s*', '')));
            END IF;
            -- Remover estado da cidade
            NEW.city := TRIM(REGEXP_REPLACE(NEW.city, '\s*-\s*[A-Za-z]{2}\s*$', ''));
        END IF;
        
        -- Aplicar Title Case
        NEW.city := INITCAP(NEW.city);
    END IF;
    
    -- ========================================
    -- 4. ATUALIZAR TIMESTAMP
    -- ========================================
    
    NEW.updated_at := NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- PARTE 3: CRIAR TRIGGER
-- ============================================================

-- Remover trigger antigo se existir
DROP TRIGGER IF EXISTS trigger_normalize_property ON properties;

-- Criar novo trigger
CREATE TRIGGER trigger_normalize_property
    BEFORE INSERT OR UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION normalize_property_data();

-- ============================================================
-- PARTE 4: VERIFICAÇÃO
-- ============================================================

-- Verificar se trigger foi criado
SELECT 
    tgname as trigger_name,
    tgenabled as enabled,
    pg_get_triggerdef(oid) as definition
FROM pg_trigger 
WHERE tgname = 'trigger_normalize_property';

-- Ver distribuição de estados após todas as correções
SELECT 
    'VERIFICAÇÃO FINAL' as info,
    COUNT(*) as total_registros,
    SUM(CASE WHEN state IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO') THEN 1 ELSE 0 END) as estados_validos,
    SUM(CASE WHEN state IS NULL OR state = '' THEN 1 ELSE 0 END) as estados_vazios,
    SUM(CASE WHEN state IS NOT NULL AND state <> '' AND state NOT IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO') THEN 1 ELSE 0 END) as estados_invalidos
FROM properties;
