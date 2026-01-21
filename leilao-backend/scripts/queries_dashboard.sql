-- ================================================
-- QUERIES PARA DASHBOARD - LEILOHUB
-- ================================================
-- Data: 2026-01-20
-- Uso: Analytics e métricas do sistema
-- ================================================

-- ================================================
-- 1. VISAO GERAL
-- ================================================

-- Total de imóveis
SELECT COUNT(*) as total_imoveis FROM properties;

-- Total de leiloeiros ativos
SELECT COUNT(DISTINCT auctioneer) as total_leiloeiros FROM properties;

-- Imóveis adicionados hoje
SELECT COUNT(*) as novos_hoje
FROM properties
WHERE DATE(created_at) = CURRENT_DATE;

-- Imóveis adicionados esta semana
SELECT COUNT(*) as novos_semana
FROM properties
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days';

-- ================================================
-- 2. DISTRIBUICAO POR ESTADO
-- ================================================

-- Total por estado (Top 10)
SELECT 
    state as uf,
    COUNT(*) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM properties) * 100, 1) as percentual
FROM properties
WHERE state IS NOT NULL AND state != ''
GROUP BY state
ORDER BY total DESC
LIMIT 10;

-- Total por estado (completo)
SELECT 
    COALESCE(state, 'SEM ESTADO') as uf,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE price > 0) as com_preco,
    AVG(price) FILTER (WHERE price > 0) as preco_medio
FROM properties
GROUP BY state
ORDER BY total DESC;

-- ================================================
-- 3. DISTRIBUICAO POR CATEGORIA
-- ================================================

-- Total por categoria
SELECT 
    category,
    COUNT(*) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM properties) * 100, 1) as percentual
FROM properties
GROUP BY category
ORDER BY total DESC;

-- Total por tipo de imóvel
SELECT 
    property_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE price > 0) as com_preco,
    AVG(price) FILTER (WHERE price > 0) as preco_medio
FROM properties
WHERE property_type IS NOT NULL
GROUP BY property_type
ORDER BY total DESC;

-- ================================================
-- 4. RANKING DE LEILOEIROS
-- ================================================

-- Top 20 leiloeiros por volume
SELECT 
    auctioneer_name as leiloeiro,
    COUNT(*) as total_imoveis,
    COUNT(*) FILTER (WHERE price > 0) as com_preco,
    AVG(price) FILTER (WHERE price > 0) as preco_medio,
    COUNT(DISTINCT state) as estados_atendidos,
    MAX(created_at) as ultima_atualizacao
FROM properties
GROUP BY auctioneer_name
ORDER BY total_imoveis DESC
LIMIT 20;

-- Leiloeiros com melhor qualidade de dados
SELECT 
    auctioneer_name as leiloeiro,
    COUNT(*) as total,
    ROUND(COUNT(*) FILTER (WHERE state IS NOT NULL)::numeric / COUNT(*) * 100, 1) as pct_com_estado,
    ROUND(COUNT(*) FILTER (WHERE city IS NOT NULL)::numeric / COUNT(*) * 100, 1) as pct_com_cidade,
    ROUND(COUNT(*) FILTER (WHERE price > 0)::numeric / COUNT(*) * 100, 1) as pct_com_preco,
    ROUND(
        (COUNT(*) FILTER (WHERE state IS NOT NULL)::numeric + 
         COUNT(*) FILTER (WHERE city IS NOT NULL)::numeric + 
         COUNT(*) FILTER (WHERE price > 0)::numeric) / (COUNT(*) * 3) * 100, 
        1
    ) as score_qualidade
FROM properties
GROUP BY auctioneer_name
HAVING COUNT(*) >= 10
ORDER BY score_qualidade DESC
LIMIT 20;

-- ================================================
-- 5. TIMELINE - NOVOS IMOVEIS
-- ================================================

-- Novos imóveis por dia (últimos 30 dias)
SELECT 
    DATE(created_at) as data,
    COUNT(*) as novos_imoveis,
    COUNT(DISTINCT auctioneer_name) as leiloeiros_ativos
FROM properties
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY data DESC;

-- Novos imóveis por hora (últimas 24h)
SELECT 
    DATE_TRUNC('hour', created_at) as hora,
    COUNT(*) as novos_imoveis
FROM properties
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY hora
ORDER BY hora DESC;

-- ================================================
-- 6. ANALISE DE PRECOS
-- ================================================

-- Estatísticas gerais de preços
SELECT 
    COUNT(*) FILTER (WHERE price > 0) as com_preco,
    COUNT(*) FILTER (WHERE price IS NULL OR price = 0) as sem_preco,
    ROUND(AVG(price) FILTER (WHERE price > 0), 2) as preco_medio,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) FILTER (WHERE price > 0), 2) as preco_mediano,
    MIN(price) FILTER (WHERE price > 0) as preco_minimo,
    MAX(price) FILTER (WHERE price > 0) as preco_maximo
FROM properties;

-- Faixas de preço
SELECT 
    CASE 
        WHEN price < 100000 THEN 'Ate R$ 100k'
        WHEN price < 300000 THEN 'R$ 100k - R$ 300k'
        WHEN price < 500000 THEN 'R$ 300k - R$ 500k'
        WHEN price < 1000000 THEN 'R$ 500k - R$ 1M'
        WHEN price < 2000000 THEN 'R$ 1M - R$ 2M'
        ELSE 'Acima de R$ 2M'
    END as faixa_preco,
    COUNT(*) as total,
    ROUND(AVG(price), 2) as preco_medio
FROM properties
WHERE price > 0
GROUP BY faixa_preco
ORDER BY preco_medio;

-- Preço médio por estado (Top 10)
SELECT 
    state as uf,
    COUNT(*) as total,
    ROUND(AVG(price) FILTER (WHERE price > 0), 2) as preco_medio,
    MIN(price) FILTER (WHERE price > 0) as preco_minimo,
    MAX(price) FILTER (WHERE price > 0) as preco_maximo
FROM properties
WHERE state IS NOT NULL
GROUP BY state
HAVING COUNT(*) FILTER (WHERE price > 0) >= 5
ORDER BY total DESC
LIMIT 10;

-- ================================================
-- 7. QUALIDADE DOS DADOS
-- ================================================

-- Completude dos campos
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE title IS NOT NULL) as com_titulo,
    COUNT(*) FILTER (WHERE state IS NOT NULL) as com_estado,
    COUNT(*) FILTER (WHERE city IS NOT NULL) as com_cidade,
    COUNT(*) FILTER (WHERE price > 0) as com_preco,
    COUNT(*) FILTER (WHERE description IS NOT NULL) as com_descricao,
    COUNT(*) FILTER (WHERE latitude IS NOT NULL) as com_geocoding,
    ROUND(COUNT(*) FILTER (WHERE state IS NOT NULL)::numeric / COUNT(*) * 100, 1) as pct_estado,
    ROUND(COUNT(*) FILTER (WHERE city IS NOT NULL)::numeric / COUNT(*) * 100, 1) as pct_cidade,
    ROUND(COUNT(*) FILTER (WHERE price > 0)::numeric / COUNT(*) * 100, 1) as pct_preco,
    ROUND(COUNT(*) FILTER (WHERE latitude IS NOT NULL)::numeric / COUNT(*) * 100, 1) as pct_geocoding
FROM properties;

-- ================================================
-- 8. IMÓVEIS DESTACADOS
-- ================================================

-- Imóveis com maior desconto
SELECT 
    title,
    auctioneer_name,
    state,
    city,
    price,
    evaluation_value,
    discount_percentage,
    url
FROM properties
WHERE discount_percentage > 0
ORDER BY discount_percentage DESC
LIMIT 10;

-- Imóveis mais valiosos
SELECT 
    title,
    auctioneer_name,
    state,
    city,
    price,
    property_type,
    url
FROM properties
WHERE price > 0
ORDER BY price DESC
LIMIT 10;

-- Imóveis mais recentes
SELECT 
    title,
    auctioneer_name,
    state,
    city,
    price,
    created_at,
    url
FROM properties
ORDER BY created_at DESC
LIMIT 20;

-- ================================================
-- 9. BUSCA E FILTROS
-- ================================================

-- Buscar por estado e cidade
SELECT 
    title,
    auctioneer_name,
    city,
    state,
    price,
    url
FROM properties
WHERE state = 'SP' 
  AND city ILIKE '%São Paulo%'
ORDER BY price
LIMIT 20;

-- Buscar por faixa de preço
SELECT 
    title,
    auctioneer_name,
    city,
    state,
    price,
    url
FROM properties
WHERE price BETWEEN 100000 AND 500000
  AND state IS NOT NULL
ORDER BY price
LIMIT 20;

-- Buscar por leiloeiro
SELECT 
    title,
    city,
    state,
    price,
    created_at,
    url
FROM properties
WHERE auctioneer_name = 'Caixa'
ORDER BY created_at DESC
LIMIT 20;

-- ================================================
-- 10. GEOCODING
-- ================================================

-- Imóveis sem geocoding (prioridade)
SELECT 
    state,
    COUNT(*) as sem_geocoding
FROM properties
WHERE latitude IS NULL
  AND state IS NOT NULL
GROUP BY state
ORDER BY sem_geocoding DESC;

-- Imóveis com geocoding completo
SELECT 
    state,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE latitude IS NOT NULL) as com_geocoding,
    ROUND(COUNT(*) FILTER (WHERE latitude IS NOT NULL)::numeric / COUNT(*) * 100, 1) as pct_geocoding
FROM properties
WHERE state IS NOT NULL
GROUP BY state
ORDER BY total DESC;

-- ================================================
-- 11. VIEWS UTEIS (Criar se necessário)
-- ================================================

-- View: Resumo por leiloeiro
CREATE OR REPLACE VIEW vw_leiloeiros_resumo AS
SELECT 
    auctioneer_name,
    COUNT(*) as total_imoveis,
    COUNT(*) FILTER (WHERE price > 0) as com_preco,
    AVG(price) FILTER (WHERE price > 0) as preco_medio,
    COUNT(DISTINCT state) as estados,
    COUNT(DISTINCT city) as cidades,
    MAX(created_at) as ultima_atualizacao,
    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') as novos_semana
FROM properties
GROUP BY auctioneer_name;

-- View: Resumo por estado
CREATE OR REPLACE VIEW vw_estados_resumo AS
SELECT 
    state as uf,
    COUNT(*) as total_imoveis,
    COUNT(DISTINCT auctioneer_name) as leiloeiros,
    COUNT(DISTINCT city) as cidades,
    AVG(price) FILTER (WHERE price > 0) as preco_medio,
    COUNT(*) FILTER (WHERE latitude IS NOT NULL) as com_geocoding,
    ROUND(COUNT(*) FILTER (WHERE latitude IS NOT NULL)::numeric / COUNT(*) * 100, 1) as pct_geocoding
FROM properties
WHERE state IS NOT NULL
GROUP BY state;

-- View: Imóveis recentes (últimos 7 dias)
CREATE OR REPLACE VIEW vw_imoveis_recentes AS
SELECT 
    id,
    title,
    auctioneer_name,
    state,
    city,
    price,
    property_type,
    created_at,
    url
FROM properties
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY created_at DESC;

-- ================================================
-- FIM DAS QUERIES
-- ================================================
