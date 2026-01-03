-- Adicionar colunas para scraping inteligente com descoberta de estrutura
-- Data: 03/01/2026

-- Adicionar coluna para armazenar configuração de scraping
ALTER TABLE auctioneers 
ADD COLUMN IF NOT EXISTS scrape_config JSONB DEFAULT NULL;

-- Adicionar coluna para status da descoberta
ALTER TABLE auctioneers 
ADD COLUMN IF NOT EXISTS discovery_status VARCHAR(20) DEFAULT 'pending';

-- Adicionar coluna para data da última descoberta
ALTER TABLE auctioneers 
ADD COLUMN IF NOT EXISTS last_discovery_at TIMESTAMP DEFAULT NULL;

-- Adicionar coluna para hash da estrutura (validação de mudanças)
ALTER TABLE auctioneers 
ADD COLUMN IF NOT EXISTS structure_hash VARCHAR(64) DEFAULT NULL;

-- Adicionar coluna para métricas de validação
ALTER TABLE auctioneers 
ADD COLUMN IF NOT EXISTS validation_metrics JSONB DEFAULT '{"consecutive_failures": 0, "total_extractions": 0, "successful_extractions": 0}'::jsonb;

-- Índices para busca rápida
CREATE INDEX IF NOT EXISTS idx_auctioneers_discovery_status 
ON auctioneers(discovery_status);

CREATE INDEX IF NOT EXISTS idx_auctioneers_structure_hash 
ON auctioneers(structure_hash);

CREATE INDEX IF NOT EXISTS idx_auctioneers_last_discovery_at 
ON auctioneers(last_discovery_at);

-- Comentários
COMMENT ON COLUMN auctioneers.scrape_config IS 'Configuração JSON com estrutura do site descoberta pela IA';
COMMENT ON COLUMN auctioneers.discovery_status IS 'Status: pending, completed, failed, needs_rediscovery';
COMMENT ON COLUMN auctioneers.structure_hash IS 'Hash MD5 da estrutura da homepage para detectar mudanças';
COMMENT ON COLUMN auctioneers.validation_metrics IS 'Métricas de validação: falhas consecutivas, total de extrações, etc.';

