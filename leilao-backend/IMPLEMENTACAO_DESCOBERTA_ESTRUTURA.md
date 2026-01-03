# Implementação: Scraping Inteligente com Descoberta de Estrutura

**Data:** 03/01/2026  
**Status:** ✅ Completo

## 📋 Resumo

Implementado sistema completo de scraping inteligente que descobre automaticamente a estrutura de sites de leiloeiros e usa essa informação para extrair imóveis de forma mais eficiente.

## 🗄️ Mudanças no Banco de Dados

### Migração SQL
- **Arquivo:** `migrations/002_add_discovery_columns.sql`
- **Script de aplicação:** `scripts/apply_discovery_migration.py`

### Novas Colunas na Tabela `auctioneers`:
- `scrape_config` (JSONB) - Configuração descoberta pela IA
- `discovery_status` (VARCHAR) - Status: pending, completed, failed, needs_rediscovery
- `last_discovery_at` (TIMESTAMP) - Data da última descoberta
- `structure_hash` (VARCHAR) - Hash MD5 da estrutura para detectar mudanças
- `validation_metrics` (JSONB) - Métricas de validação (falhas, sucessos, etc)

### Índices Criados:
- `idx_auctioneers_discovery_status`
- `idx_auctioneers_structure_hash`
- `idx_auctioneers_last_discovery_at`

## 📁 Arquivos Criados

### 1. `app/services/site_discovery.py`
Serviço que descobre a estrutura de sites usando IA:
- Baixa homepage do site
- Analisa com OpenAI (GPT-4o-mini)
- Identifica filtros, paginação, selectors
- Valida URLs descobertas
- Calcula hash da estrutura

### 2. `app/services/discovery_orchestrator.py`
Orquestra o processo de descoberta:
- `run_discovery()` - Executa descoberta para múltiplos leiloeiros
- `run_single_discovery()` - Descoberta para um leiloeiro específico
- `run_rediscovery()` - Re-descoberta automática
- `get_discovery_stats()` - Estatísticas de descoberta

### 3. `app/services/structure_validator.py`
Valida e decide quando re-descobrir:
- `needs_rediscovery()` - Verifica se precisa re-descoberta
- `check_structure_changed()` - Compara hash da estrutura
- `update_validation_metrics()` - Atualiza métricas após extração
- `calculate_config_expiry()` - Calcula data de expiração

## 🔄 Arquivos Modificados

### 1. `app/services/universal_scraper.py`
Adicionados métodos:
- `scrape_with_config()` - Scraping usando configuração descoberta
- `_extract_from_url()` - Extração de uma URL específica
- `_paginate_with_config()` - Paginação usando configuração

### 2. `app/services/scraper_orchestrator.py`
Adicionado método:
- `run_all_smart()` - Executa scraping inteligente usando configs quando disponíveis
- `_get_active_auctioneers_with_config()` - Busca leiloeiros com suas configurações

### 3. `app/main.py`
Novos endpoints:
- `POST /api/discovery/run` - Executa descoberta
- `POST /api/discovery/single/{auctioneer_id}` - Descoberta única
- `GET /api/discovery/stats` - Estatísticas
- `POST /api/scraper/run-smart` - Scraping inteligente
- `POST /api/discovery/rediscovery` - Re-descoberta
- `GET /api/discovery/needs-rediscovery` - Lista que precisam re-descoberta
- `POST /api/discovery/check-structure/{auctioneer_id}` - Verifica mudanças

### 4. `scripts/daily_maintenance.py`
Atualizado para incluir:
- Verificação automática de configs expiradas
- Re-descoberta automática de sites problemáticos

### 5. `scripts/apply_discovery_migration.py`
Novo script para aplicar a migração SQL

## 🚀 Como Usar

### 1. Aplicar Migração do Banco
```bash
cd leilao-backend
python scripts/apply_discovery_migration.py
```

### 2. Executar Descoberta Inicial
```bash
# Via API
curl -X POST "http://localhost:8000/api/discovery/run?limit=5"

# Ou via Python
python -c "
import asyncio
from app.services.discovery_orchestrator import discovery_orchestrator
result = asyncio.run(discovery_orchestrator.run_discovery(limit=5))
print(result)
"
```

### 3. Executar Scraping Inteligente
```bash
# Via API
curl -X POST "http://localhost:8000/api/scraper/run-smart?limit=5&skip_geocoding=true"

# Ou via Python
python -c "
import asyncio
from app.services.scraper_orchestrator import scraper_orchestrator
result = asyncio.run(scraper_orchestrator.run_all_smart(skip_geocoding=True, limit=5))
print(result)
"
```

### 4. Verificar Status
```bash
curl "http://localhost:8000/api/discovery/stats"
```

### 5. Re-descoberta Automática
```bash
# Via API
curl -X POST "http://localhost:8000/api/discovery/rediscovery?limit=10"

# Ou executar manutenção diária
python scripts/daily_maintenance.py
```

## 📊 Estrutura da Configuração (scrape_config)

```json
{
  "version": "1.0",
  "discovered_at": "2026-01-03T20:00:00Z",
  "expires_at": "2026-02-02T20:00:00Z",
  "site_type": "filter_based",
  "base_url": "https://example.com",
  
  "property_filters": [
    {"name": "Apartamento", "url": "/busca?categoria=apartamento", "validated": true},
    {"name": "Casa", "url": "/busca?categoria=casa", "validated": true}
  ],
  
  "pagination": {
    "type": "query_param",
    "param": "page",
    "start": 1,
    "pattern": "?page={n}"
  },
  
  "selectors": {
    "property_list": ".lista-imoveis .item",
    "property_link": "a.ver-detalhes",
    "next_page": ".paginacao .next"
  },
  
  "fallback_url": "/imoveis",
  "requires_js": false,
  
  "validation": {
    "structure_hash": "a1b2c3d4e5f6...",
    "last_validated_at": "2026-01-03T20:00:00Z",
    "consecutive_failures": 0,
    "total_extractions": 0,
    "successful_extractions": 0
  },
  
  "notes": "Site usa filtros por categoria na sidebar"
}
```

## 🔄 Fluxo de Funcionamento

### Fase 1: Descoberta (1x por leiloeiro)
1. Acessa homepage do site
2. IA analisa estrutura e identifica filtros/paginação
3. Valida URLs descobertas
4. Salva configuração no banco com hash da estrutura

### Fase 2: Extração (diária)
1. Lê configuração do leiloeiro
2. Vai direto aos URLs de filtros descobertos
3. Extrai imóveis de cada filtro
4. Pagina usando configuração descoberta
5. Atualiza métricas de validação

### Fase 3: Validação (automática)
1. Verifica se config expirou (>30 dias)
2. Verifica falhas consecutivas (>=3)
3. Verifica taxa de sucesso (<50%)
4. Re-descobre automaticamente se necessário

## 📈 Impacto Esperado

| Métrica | Antes | Depois |
|---------|-------|--------|
| Taxa de sucesso | ~30% | >70% |
| Requisições por leiloeiro | 15-20 | 3-5 |
| Custo OpenAI | Alto | Baixo |
| Cobertura de imóveis | Parcial | Completa |
| Tempo de scraping | ~2min/leiloeiro | ~30s/leiloeiro |

## ✅ Próximos Passos

1. **Aplicar migração SQL** no banco de produção
2. **Executar descoberta inicial** para todos os leiloeiros
3. **Monitorar métricas** de sucesso/falha
4. **Configurar job diário** para re-descoberta automática
5. **Ajustar parâmetros** de validação conforme necessário

## 🐛 Troubleshooting

### Erro: "DATABASE_URL não configurada"
- Verificar se `.env` está configurado corretamente

### Erro: "OpenAI API Key não encontrada"
- Configurar `OPENAI_API_KEY` no `.env`

### Descoberta falhando para muitos sites
- Verificar logs para identificar padrões
- Ajustar prompt de descoberta se necessário
- Verificar se sites estão acessíveis

### Config expirando muito rápido
- Ajustar `CONFIG_EXPIRY_DAYS` em `structure_validator.py`

---

**Implementação completa!** ✅

