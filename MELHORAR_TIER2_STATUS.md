# 🔧 MELHORAR TIER 2 - EM ANDAMENTO

**Data**: 20/01/2026  
**Status**: ⏳ Descobrindo paths corretos  
**Objetivo**: +500-2.000 imóveis adicionais (grátis)

---

## 📊 SITUAÇÃO ATUAL

### TIER 2 Resultados Anteriores:
- Sites processados: 87
- **Sucessos**: 3 sites (1.088 imóveis)
- **CloudFlare**: 52 sites (promovidos para TIER 3)
- **0 imóveis**: 32 sites ← **FOCO ATUAL**

### Problemas Identificados nos 32 Sites:
1. **Paths incorretos** (26 sites): `/imoveis` não existe
2. **CAPTCHA** (3 sites): marangonileiloes, monzonleiloes, sold
3. **Página vazia** (2 sites): anabrasilleiloes, hastalegal
4. **Erro SSL** (1 site): multleiloes.com

---

## 🎯 PLANO DE AÇÃO

### Fase 1: Descoberta Automática de Paths ⏳ EM ANDAMENTO

**Script**: `descobrir_paths.py`

**Método**:
1. **Teste de paths conhecidos**:
   - `/imoveis`, `/leiloes`, `/leilao`
   - `/produtos`, `/catalogo`
   - `/leiloes/imoveis`, `/produtos/imoveis`
   - `/lotes`, `/busca`, `/search`

2. **Análise de menu de navegação**:
   - Encontrar links no `<nav>`, `<header>`, `.menu`
   - Procurar textos: "imóveis", "leilões", "lotes", "produtos"

3. **Busca de formulários**:
   - Identificar campos de busca
   - Extrair action do formulário

**Sites sendo investigados** (15 prioritários):
1. agenciadeleiloes.com.br
2. bianchileiloes.com.br
3. ckleiloes.com.br
4. duxleiloes.com.br
5. gtleiloes.com.br
6. juleiloes.com.br
7. leffaleiloes.com.br
8. leiloesfederal.com.br
9. marceloleiloeiro.com.br
10. marquesbarretoleiloes.com.br
11. michellileiloes.com.br
12. pbcastro.com.br
13. rangelleiloes.com.br
14. renovarleiloes.com.br
15. sold.com.br

**Tempo estimado**: ~15 minutos

---

### Fase 2: Atualização do Extrator (Próximo)

**Ações**:
1. Ler mapeamento de paths descobertos
2. Atualizar `extrator_tier2_stealth.py`:
   - Adicionar suporte a paths específicos por domínio
   - Carregar de `config/paths_especificos.json`
3. Testar com 3-5 sites primeiro

---

### Fase 3: Re-execução Parcial (Depois)

**Ações**:
1. Executar TIER 2 **apenas** nos sites corrigidos
2. Validar resultados
3. Consolidar com dados anteriores

---

## 📈 RESULTADOS ESPERADOS

### Cenário Otimista (60% dos 15 sites):
- 9 sites com paths descobertos
- Média: 200 imóveis/site
- **Total: ~1.800 imóveis adicionais**

### Cenário Realista (40-50% dos 15 sites):
- 6-7 sites com paths descobertos
- Média: 150 imóveis/site
- **Total: ~900-1.050 imóveis adicionais**

### Cenário Conservador (30% dos 15 sites):
- 4-5 sites com paths descobertos
- Média: 100 imóveis/site
- **Total: ~400-500 imóveis adicionais**

---

## 💰 ANÁLISE FINANCEIRA

| Item | Valor |
|------|-------|
| Custo do script | $0 |
| Custo da re-execução | $0 |
| Créditos ScrapingBee | 0 |
| **Custo Total** | **$0** |

vs

| Item | TIER 3 (rejeitado) |
|------|-------------------|
| Custo | $19-20 USD |
| ROI projetado | Negativo |
| Imóveis esperados | 15-75 |

**Economia**: $19-20 USD  
**Retorno esperado**: 400-1.800 imóveis

---

## 📁 ARQUIVOS GERADOS

### Durante Descoberta:
```
logs/extracao_fase2/tier2/
├── sites_0_imoveis.json (lista dos 32 sites)
└── paths_descobertos.json (resultados da investigação)

config/
└── paths_especificos.json (mapeamento para usar no extrator)
```

### Após Re-execução:
```
logs/extracao_fase2/tier2/
└── tier2_resultados_corrigidos_YYYYMMDD_HHMMSS.json
```

---

## 🔄 PRÓXIMAS ETAPAS

1. ✅ Identificar 32 sites com 0 imóveis
2. ⏳ **Descobrir paths corretos** (15 sites prioritários)
3. ⏸️ Atualizar extrator TIER 2
4. ⏸️ Testar com 3-5 sites
5. ⏸️ Re-executar sites corrigidos
6. ⏸️ Consolidar resultados

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Alvo |
|---------|------|
| Paths descobertos | ≥ 6 de 15 (40%+) |
| Imóveis adicionais | ≥ 500 |
| Custo | $0 |
| Tempo total | < 2 horas |

---

**Última atualização**: 20/01/2026 ~20:25  
**Status**: Aguardando conclusão da descoberta automática de paths
