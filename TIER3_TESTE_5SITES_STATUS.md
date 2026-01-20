# 🧪 TIER 3 - TESTE COM 5 SITES

**Data**: 20/01/2026  
**Status**: ⏳ EM EXECUÇÃO  
**Objetivo**: Validar ScrapingBee antes de executar 77 sites completos

---

## 🎯 SITES SELECIONADOS PARA TESTE

| # | Site | Motivo da Seleção |
|---|------|-------------------|
| 1 | **megaleiloes.com.br** | Controle positivo - funcionou no TIER 2 (1.058 imóveis) |
| 2 | **fidalgoleiloes.com.br** | CloudFlare Challenge - promovido do TIER 2 |
| 3 | **bestleiloes.com.br** | CloudFlare Challenge - promovido do TIER 2 |
| 4 | **granadoleiloes.com.br** | CloudFlare Challenge - promovido do TIER 2 |
| 5 | **lottileiloes.com.br** | CloudFlare Challenge - promovido do TIER 2 |

---

## 🔧 MELHORIAS APLICADAS NO TESTE

### vs TIER 3 Original (0% sucesso):

**Antes**:
- 5 seletores limitados
- Filtro de URL restritivo
- Sem logging detalhado

**Agora**:
- ✅ **16 seletores robustos** (mesmos do TIER 2 corrigido)
- ✅ **Filtro de URL flexível** (`href != '#'`)
- ✅ **Logging detalhado** (HTML size, seletor usado, etc.)
- ✅ **Detecção de CloudFlare** no HTML retornado
- ✅ **Deduplicação de URLs**

---

## 💰 CUSTOS

| Item | Valor |
|------|-------|
| Créditos por site | 25 |
| Sites no teste | 5 |
| **Total do teste** | **125 créditos (~$1.25 USD)** |
| Custo se aprovar completo | 1.925 créditos (~$19-20 USD) |

---

## ✅ CRITÉRIO DE SUCESSO

| Taxa de Sucesso | Decisão |
|----------------|---------|
| **≥ 60%** (3+ sites) | ✅ APROVAR execução completa dos 77 sites |
| **40-59%** (2 sites) | ⚠️ AVALIAR - Considerar com expectativas ajustadas |
| **< 40%** (0-1 sites) | ❌ REJEITAR - Investigar mais antes de continuar |

---

## 📊 RESULTADOS ESPERADOS

### Cenário Otimista (80% sucesso):
- 4 de 5 sites funcionam
- megaleiloes: ~1.000 imóveis
- 3 sites CloudFlare: ~500-1.000 imóveis
- **Total: 1.500-2.500 imóveis no teste**
- **Projeção 77 sites: 8.000-12.000 imóveis**

### Cenário Realista (60% sucesso):
- 3 de 5 sites funcionam
- megaleiloes: ~1.000 imóveis
- 2 sites CloudFlare: ~300-500 imóveis
- **Total: 1.300-1.500 imóveis no teste**
- **Projeção 77 sites: 6.000-8.000 imóveis**

### Cenário Conservador (40% sucesso):
- 2 de 5 sites funcionam
- megaleiloes: ~1.000 imóveis
- 1 site CloudFlare: ~200 imóveis
- **Total: 1.200 imóveis no teste**
- **Projeção 77 sites: 4.000-5.000 imóveis**

---

## ⏱️ TEMPO ESTIMADO

- ScrapingBee wait: 5 segundos/site
- Processamento: ~10 segundos/site
- Pausa entre sites: 3 segundos
- **Total: ~1-2 minutos**

---

## 📁 ARQUIVOS QUE SERÃO GERADOS

```
logs/extracao_fase2/tier3/
└── teste_tier3_5sites_YYYYMMDD_HHMMSS.json
```

---

## 🔍 O QUE ESTAMOS TESTANDO

1. **ScrapingBee consegue contornar CloudFlare?**
   - 4 dos 5 sites têm CloudFlare Challenge
   - TIER 2 não conseguiu (0% nesses sites)
   - ScrapingBee deve conseguir ~90%+

2. **Os seletores melhorados funcionam?**
   - 16 seletores vs 5 originais
   - Filtro de URL flexível

3. **Os paths `/imoveis` estão corretos?**
   - TIER 3 original teve muitos HTTP 404
   - Verificar se precisamos paths específicos

---

## 📝 PRÓXIMA AÇÃO BASEADA NO RESULTADO

### Se ≥ 60% sucesso:
1. Aplicar as mesmas melhorias ao `extrator_tier3_scrapingbee.py` oficial
2. Executar os 77 sites completos
3. Esperar 5.000-10.000 imóveis adicionais

### Se 40-59% sucesso:
1. Analisar quais sites falharam e por quê
2. Ajustar paths específicos se necessário
3. Re-testar ou executar com expectativas ajustadas

### Se < 40% sucesso:
1. Investigar detalhadamente os erros
2. Verificar se CloudFlare ainda está bloqueando
3. Considerar outras estratégias antes de gastar $20 USD

---

**Última atualização**: 20/01/2026 ~20:05
