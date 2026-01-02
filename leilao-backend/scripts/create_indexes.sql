-- =============================================================
-- ÍNDICES PARA OTIMIZAÇÃO DE PERFORMANCE
-- Execute este script no Supabase SQL Editor
-- =============================================================

-- Índice para busca por categoria
CREATE INDEX IF NOT EXISTS idx_properties_category 
ON properties(category);

-- Índice para busca por estado
CREATE INDEX IF NOT EXISTS idx_properties_state 
ON properties(state);

-- Índice para busca por cidade
CREATE INDEX IF NOT EXISTS idx_properties_city 
ON properties(city);

-- Índice para ordenação por data do primeiro leilão
CREATE INDEX IF NOT EXISTS idx_properties_first_auction_date 
ON properties(first_auction_date DESC NULLS LAST);

-- Índice para ordenação por data do segundo leilão
CREATE INDEX IF NOT EXISTS idx_properties_second_auction_date 
ON properties(second_auction_date DESC NULLS LAST);

-- Índice para ordenação por valor de avaliação
CREATE INDEX IF NOT EXISTS idx_properties_evaluation_value 
ON properties(evaluation_value DESC NULLS LAST);

-- Índice para ordenação por valor do primeiro leilão
CREATE INDEX IF NOT EXISTS idx_properties_first_auction_value 
ON properties(first_auction_value ASC NULLS LAST);

-- Índice para ordenação por desconto
CREATE INDEX IF NOT EXISTS idx_properties_discount 
ON properties(discount_percentage DESC NULLS LAST);

-- Índice composto para filtros comuns (estado + categoria)
CREATE INDEX IF NOT EXISTS idx_properties_state_category 
ON properties(state, category);

-- Índice composto para filtros com ordenação (estado + data)
CREATE INDEX IF NOT EXISTS idx_properties_state_date 
ON properties(state, first_auction_date DESC NULLS LAST);

-- Índice para busca por leiloeiro
CREATE INDEX IF NOT EXISTS idx_properties_auctioneer 
ON properties(auctioneer_id);

-- Índice para imóveis ativos
CREATE INDEX IF NOT EXISTS idx_properties_active 
ON properties(is_active) WHERE is_active = true;

-- Índice para busca textual no título (se PostgreSQL >= 12)
-- Nota: Requer extensão pg_trgm
-- CREATE INDEX IF NOT EXISTS idx_properties_title_trgm 
-- ON properties USING gin(title gin_trgm_ops);

-- Habilitar extensão para busca textual (execute primeiro se necessário)
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================
-- ESTATÍSTICAS APÓS CRIAÇÃO DOS ÍNDICES
-- =============================================================

-- Verifica índices criados
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'properties'
ORDER BY indexname;

