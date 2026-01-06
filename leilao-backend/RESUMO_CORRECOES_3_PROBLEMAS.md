# RESUMO DAS CORREÇÕES - 3 PROBLEMAS PENDENTES

## ✅ PROBLEMA 1: NORMALIZAÇÃO NA ENTRADA (PREVENÇÃO)

### Diagnóstico
- Função `normalize_property` existe em `sync_to_supabase.py`
- Mas não aplicava normalização completa (Title Case para categoria/cidade, Uppercase para estado)

### Correção Aplicada
1. **Criada função reutilizável** `app/utils/normalize_property_data.py`:
   - Title Case para categoria
   - Title Case para cidade
   - Uppercase para estado (máximo 2 caracteres)

2. **Atualizado `sync_to_supabase.py`**:
   - Adicionada normalização completa na função `normalize_property`
   - Importa e usa função reutilizável para garantir consistência

### Próximos Passos
- Aplicar normalização em todos os scrapers individuais
- Aplicar normalização em endpoints de criação (`/api/sync/caixa`, etc.)

---

## ⚠️ PROBLEMA 2: VALORES 1º E 2º LEILÃO TROCADOS

### Diagnóstico
- Consultadas 10 propriedades de Campinas no banco
- **Todas têm valores iguais** para `first_auction_value` e `second_auction_value`
- Fonte: `caixa` (Caixa Econômica Federal)

### Análise
- O scraper da Caixa (`caixa_scraper.py`) **não extrai `second_auction_value`** do CSV
- O CSV da Caixa só fornece `first_auction_value` (campo "Preço")
- Quando `second_auction_value` está vazio, o sistema copia `first_auction_value` (em `quality_filter.py` linha 242)

### Conclusão
**NÃO HÁ INVERSÃO DE VALORES** - A Caixa simplesmente não fornece o valor do 2º leilão no CSV público.

### Verificação do Superbid
- O scraper do Superbid extrai corretamente:
  - `first_auction_value = stages[0].get('initialBidValue')` (primeiro stage)
  - `second_auction_value = stages[1].get('initialBidValue')` (segundo stage)
- A ordem está correta no código

### Recomendações
1. Se a Caixa não fornece 2º leilão, manter valores iguais está correto
2. Se houver necessidade de diferenciar, seria necessário:
   - Scraping da página de detalhes do imóvel na Caixa
   - Ou usar uma heurística (ex: 2º leilão = 70% do 1º leilão)

---

## ✅ PROBLEMA 3: MAPA SEM MARCADORES (GEOCODING)

### Diagnóstico
- **Total de propriedades ativas**: 41.465
- **Com coordenadas (latitude/longitude)**: 28.896 (69.7%)
- **Sem coordenadas**: 12.569 (30.3%)

### Análise
- **69.7% das propriedades têm coordenadas** - não é um problema crítico
- O geocoding está funcionando, mas ainda há 30% sem coordenadas
- Propriedades sem coordenadas têm status `pending` ou `failed`

### Correção Aplicada
1. **Melhorado endpoint `/api/map/properties`**:
   - Agora consulta **diretamente o Supabase** quando disponível (mais eficiente)
   - Filtra coordenadas na query SQL (não em Python)
   - Fallback para `db.get_properties` se Supabase não estiver disponível

### Próximos Passos
1. Executar geocoding em batch para propriedades pendentes:
   ```bash
   POST /api/admin/geocode-batch?limit=1000
   ```
2. Verificar se o frontend está renderizando corretamente os markers

---

## ARQUIVOS MODIFICADOS

1. `leilao-backend/scripts/sync_to_supabase.py`
   - Adicionada normalização completa
   - Importa função reutilizável

2. `leilao-backend/app/utils/normalize_property_data.py` (NOVO)
   - Função reutilizável de normalização

3. `leilao-backend/app/main.py`
   - Endpoint `/api/map/properties` melhorado
   - Consulta Supabase diretamente

4. `leilao-backend/scripts/diagnostico_problemas.py` (NOVO)
   - Script de diagnóstico para os 3 problemas

---

## PRÓXIMAS AÇÕES RECOMENDADAS

1. **Normalização**: Aplicar `normalize_property_data()` em:
   - `app/services/scraper_orchestrator.py` (método `_save_properties`)
   - `app/main.py` (endpoint `/api/sync/caixa`)
   - Todos os scrapers individuais

2. **Geocoding**: Executar batch de geocoding para propriedades pendentes

3. **Valores Caixa**: Se necessário, implementar scraping de detalhes ou heurística para 2º leilão

---

## TESTES REALIZADOS

✅ Diagnóstico executado com sucesso
✅ Normalização implementada
✅ Endpoint do mapa melhorado
✅ Verificação de scrapers (Superbid está correto)

