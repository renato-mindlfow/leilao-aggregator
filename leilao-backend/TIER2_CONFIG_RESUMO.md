# RESUMO CONFIGURAÇÃO TIER 2 - 30 SITES

## Status Geral
- **Total de sites:** 30
- **Configs criados:** 30
- **Método detectado:** API REST (Superbid) - **REQUER VALIDAÇÃO MANUAL**

## ⚠️ IMPORTANTE
O script de análise inicial detectou que todos os sites usam a API Superbid com `portalId=2`, mas isso pode ser um **falso positivo**. A API Superbid pode aceitar qualquer portalId e retornar os mesmos dados.

**AÇÃO NECESSÁRIA:** Validar manualmente cada site para confirmar:
1. Se realmente usa API Superbid
2. Qual o portalId correto de cada site
3. Se não usa API, identificar seletores com browser

## Lista de Sites Configurados

| # | Site | ID | URL | Método | Status |
|---|------|-----|-----|--------|--------|
| 1 | Superbid | superbid | https://www.superbid.net | api_rest | ✅ |
| 2 | Lance no Leilão | lancenoleilao | https://www.lancenoleilao.com.br | api_rest | ⚠️ Requer validação |
| 3 | LUT | lut | https://www.lut.com.br | api_rest | ⚠️ Requer validação |
| 4 | Big Leilão | bigleilao | https://www.bigleilao.com.br | api_rest | ⚠️ Requer validação |
| 5 | Via Leilões | vialeiloes | https://www.vialeiloes.com.br | api_rest | ⚠️ Requer validação |
| 6 | Freitas Leiloeiro | freitasleiloeiro | https://www.freitasleiloeiro.com.br | api_rest | ⚠️ **NÃO USA API** - Requer browser |
| 7 | Frazão Leilões | frazaoleiloes | https://www.frazaoleiloes.com.br | api_rest | ⚠️ Requer validação |
| 8 | Franco Leilões | francoleiloes | https://www.francoleiloes.com.br | api_rest | ⚠️ Requer validação |
| 9 | Lance Judicial | lancejudicial | https://www.lancejudicial.com.br | api_rest | ⚠️ Requer validação |
| 10 | Leilões Freire | leiloesfreire | https://www.leiloesfreire.com.br | api_rest | ⚠️ Requer validação |
| 11 | BFR Contábil | bfrcontabil | https://www.bfrcontabil.com.br | api_rest | ⚠️ Requer validação |
| 12 | Kronberg Leilões | kronbergleiloes | https://www.kronbergleiloes.com.br | api_rest | ⚠️ Requer validação |
| 13 | LeiloMaster | leilomaster | https://www.leilomaster.com.br | api_rest | ⚠️ Requer validação |
| 14 | Nossos Leilão | nossoleilao | https://www.nossoleilao.com.br | api_rest | ⚠️ Requer validação |
| 15 | Líder Leilões | liderleiloes | https://www.liderleiloes.com.br | api_rest | ⚠️ Requer validação |
| 16 | Leilões Judiciais RS | leiloesjudiciaisrs | https://www.leiloesjudiciaisrs.com.br | api_rest | ⚠️ Requer validação |
| 17 | Santa Maria Leilões | santamarialeiloes | https://www.santamarialeiloes.com.br | api_rest | ⚠️ Requer validação |
| 18 | MG Leilões RS | mgleiloes-rs | https://www.mgleiloes-rs.com.br | api_rest | ⚠️ Requer validação |
| 19 | Rocha Leilões | rochaleiloes | https://www.rochaleiloes.com.br | api_rest | ⚠️ Requer validação |
| 20 | Rigolon Leilões | rigolonleiloes | https://www.rigolonleiloes.com.br | api_rest | ⚠️ Requer validação |
| 21 | Hasta Legal | hastalegal | https://www.hastalegal.com.br | api_rest | ⚠️ Requer validação |
| 22 | Hasta Pública | hastapublica | https://www.hastapublica.com.br | api_rest | ⚠️ Requer validação |
| 23 | Escritório de Leilões | escritoriodeleiloes | https://www.escritoriodeleiloes.com.br | api_rest | ⚠️ Requer validação |
| 24 | Grandes Leilões | grandesleiloes | https://www.grandesleiloes.com.br | api_rest | ⚠️ Requer validação |
| 25 | Tonial Leilões | tonialleiloes | https://www.tonialleiloes.com.br | api_rest | ⚠️ Requer validação |
| 26 | Trevisan Leilões | trevisanleiloes | https://www.trevisanleiloes.com.br | api_rest | ⚠️ Requer validação |
| 27 | Vidal Leilões | vidalleiloes | https://www.vidalleiloes.com.br | api_rest | ⚠️ Requer validação |
| 28 | Web Leilões | webleiloes | https://www.webleiloes.com.br | api_rest | ⚠️ Requer validação |
| 29 | Zuccalmaglio Leilões | zuccalmaglioleiloes | https://www.zuccalmaglioleiloes.com.br | api_rest | ⚠️ Requer validação |
| 30 | Zago Leilões | zagoleiloes | https://www.zagoleiloes.com.br | api_rest | ⚠️ Requer validação |

## Próximos Passos

1. **Validação Manual com Browser:**
   - Acessar cada site
   - Verificar requisições de rede para confirmar uso de API Superbid
   - Identificar portalId correto (se usar API)
   - Identificar seletores (se não usar API)

2. **Sites Prioritários para Validação:**
   - Freitas Leiloeiro (confirmado: NÃO usa API Superbid)
   - Sites do LOTE 1 (Superbid/White-label) - provavelmente usam API
   - Sites do LOTE 2-6 - requerem validação individual

3. **Formato de Config Final:**
   - Se usar API: manter formato atual
   - Se não usar API: adicionar seletores e paginação

## Arquivos Gerados

- **Configs:** `leilao-backend/app/configs/sites/*.json` (30 arquivos)
- **Resumo:** `leilao-backend/tier2_analysis_summary.json`
- **Script:** `leilao-backend/analisar_tier2_sites.py`

