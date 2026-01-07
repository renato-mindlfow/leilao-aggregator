# 📊 ANÁLISE PROFUNDA DE LEILOEIROS COM ERRO

**Data:** 2026-01-06 22:10:44
**Total Analisado:** 166 leiloeiros

## Resumo por Diagnóstico

| Diagnóstico | Quantidade | % | Prioridade |
|-------------|------------|---|------------|
| ESTRUTURA_MUDOU | 128 | 77.1% | 4.0 |
| CLOUDFLARE | 3 | 1.8% | 4.0 |
| SEM_IMOVEIS_LISTADOS | 14 | 8.4% | 3.0 |
| 403_FORBIDDEN | 2 | 1.2% | 3.0 |
| TIMEOUT | 1 | 0.6% | 3.0 |
| 404_NOT_FOUND | 2 | 1.2% | 2.0 |
| SSL_ERROR | 7 | 4.2% | 2.0 |
| DNS_FALHA | 9 | 5.4% | 1.0 |

## Legenda de Prioridade

- **5**: Alta - Scraper precisa de ajuste urgente (site funciona)
- **4**: Média-Alta - Requer implementação técnica (Playwright, headers)
- **3**: Média - Problema temporário ou site sem imóveis
- **2**: Baixa - Problema no servidor do leiloeiro
- **1**: Muito Baixa - Site offline/domínio expirado

---

## Detalhamento por Categoria


### ESTRUTURA_MUDOU (128 leiloeiros)

**Descrição:** Site funciona mas estrutura HTML mudou

**Ação Recomendada:** Atualizar seletores CSS do scraper

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
| Vivaleiloes | https://www.vivaleiloes.com.br | Nenhum imóvel encontrado |
| Biasileiloes | https://www.biasileiloes.com.br | Nenhum imóvel encontrado |
| Lancenoleilao | https://www.lancenoleilao.com.br | duplicate key value violates unique constraint "pr |
| Leje | https://www.leje.com.br | Nenhum imóvel encontrado |
| Unileiloes | https://www.unileiloes.com.br | Nenhum imóvel encontrado |
| Depaulaonline | https://www.depaulaonline.com.br | Nenhum imóvel encontrado |
| Lancetotal | https://www.lancetotal.com.br | N/A |
| Frazaoleiloes | https://www.frazaoleiloes.com.br | N/A |
| Picellileiloes | https://www.picellileiloes.com.br | Nenhum imóvel encontrado |
| Allianceleiloes | https://www.allianceleiloes.com.br | Nenhum imóvel encontrado |
| Moralesleiloes | https://www.moralesleiloes.com.br | Nenhum imóvel encontrado |
| Spencerleiloes | https://www.spencerleiloes.com.br | Nenhum imóvel encontrado |
| Horizonteleiloes | https://www.horizonteleiloes.com.br | Nenhum imóvel encontrado |
| Webleiloes | https://www.webleiloes.com.br | Nenhum imóvel encontrado |
| Alexandridisleiloes | https://www.alexandridisleiloes.com.br | Nenhum imóvel encontrado |
| Marquesleiloes | https://www.marquesleiloes.com.br | Nenhum imóvel encontrado |
| Oleiloes | https://www.oleiloes.com.br | Nenhum imóvel encontrado |
| Centraljudicial | https://www.centraljudicial.com.br | duplicate key value violates unique constraint "pr |
| Ctsleiloes | https://www.ctsleiloes.com.br | 'NoneType' object is not subscriptable |
| Cristianoescolaleiloes | https://www.cristianoescolaleiloes.com.b | Nenhum imóvel encontrado |

*... e mais 108 leiloeiros*

### CLOUDFLARE (3 leiloeiros)

**Descrição:** Bloqueado por Cloudflare/proteção anti-bot

**Ação Recomendada:** Implementar scraper com Playwright + stealth mode

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
| Sold | https://www.sold.com.br | Nenhum imóvel encontrado |
| Lancejudicial | https://www.lancejudicial.com.br | Nenhum imóvel encontrado |
| Flexleiloes | https://www.flexleiloes.com.br | 'NoneType' object is not subscriptable |

### SEM_IMOVEIS_LISTADOS (14 leiloeiros)

**Descrição:** Site funciona mas não há imóveis listados

**Ação Recomendada:** Leiloeiro pode não ter imóveis ativos no momento; manter monitoramento | URL sugerida: https://www.lut.com.br/imoveis

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
| Lut | https://www.lut.com.br | Nenhum imóvel encontrado |
| Portalzuk | https://www.portalzuk.com.br/ | Nenhum imóvel encontrado |
| Hastapublica | https://www.hastapublica.com.br | Nenhum imóvel encontrado |
| Hastavip | https://www.hastavip.com.br | Nenhum imóvel encontrado |
| Gilsoninumaruleiloes | https://www.gilsoninumaruleiloes.com.br | Nenhum imóvel encontrado |
| Psnleiloes | https://www.psnleiloes.com.br | Nenhum imóvel encontrado |
| Benedettoleiloes | https://www.benedettoleiloes.com.br | Nenhum imóvel encontrado |
| Savoyleiloes | https://www.savoyleiloes.com.br | Nenhum imóvel encontrado |
| Leiloesfreire | https://www.leiloesfreire.com.br | Nenhum imóvel encontrado |
| Alvaroleiloes | https://www.alvaroleiloes.com.br | Nenhum imóvel encontrado |
| Fabioleiloes | https://www.fabioleiloes.com.br | Nenhum imóvel encontrado |
| Leiloescentrooeste | https://www.leiloescentrooeste.com.br | Nenhum imóvel encontrado |
| Rmmleiloes | https://www.rmmleiloes.com.br | Nenhum imóvel encontrado |
| Leiloesjudiciaisrs | https://www.leiloesjudiciaisrs.com.br | Nenhum imóvel encontrado |

### 403_FORBIDDEN (2 leiloeiros)

**Descrição:** Acesso negado - pode precisar de headers especiais

**Ação Recomendada:** Adicionar headers customizados ou usar proxy

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
| Montenegroleiloes | https://www.montenegroleiloes.com.br | Nenhum imóvel encontrado |
| Ruipintoleiloeiro | https://www.ruipintoleiloeiro.com.br | Nenhum imóvel encontrado |

### TIMEOUT (1 leiloeiros)

**Descrição:** Site muito lento ou não responde

**Ação Recomendada:** Tentar novamente mais tarde; pode ser instabilidade temporária

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
| Nortonleiloes | https://www.nortonleiloes.com.br | Nenhum imóvel encontrado |

### 404_NOT_FOUND (2 leiloeiros)

**Descrição:** Página não encontrada - URL pode ter mudado

**Ação Recomendada:** Descobrir nova URL de listagem de imóveis

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
| Anabrasilleiloes | https://www.anabrasilleiloes.com.br | Nenhum imóvel encontrado |
| Hastalegal | https://www.hastalegal.com.br | Nenhum imóvel encontrado |

### SSL_ERROR (7 leiloeiros)

**Descrição:** Problema com certificado SSL

**Ação Recomendada:** Tentar com http:// ou ignorar verificação SSL

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
| Freitasleiloeiro | https://www.freitasleiloeiro.com.br | N/A |
| Sumareleiloes | https://www.sumareleiloes.com.br | Nenhum imóvel encontrado |
| E-Confianca | https://www.e-confianca.com.br | Nenhum imóvel encontrado |
| Jcleiloeiro | https://www.jcleiloeiro.com.br | Nenhum imóvel encontrado |
| Oreidosleiloes | https://www.oreidosleiloes.com.br | Nenhum imóvel encontrado |
| Josequencaleiloeiro | https://www.josequencaleiloeiro.com.br | Nenhum imóvel encontrado |
| Gustavomorettoleiloeiro | https://www.gustavomorettoleiloeiro.com. | Nenhum imóvel encontrado |

### DNS_FALHA (9 leiloeiros)

**Descrição:** DNS não resolve - domínio pode ter expirado

**Ação Recomendada:** Verificar se domínio mudou ou expirou

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
| Mikedutraleiloeiro | https://www.mikedutraleiloeiro.com.br | Nenhum imóvel encontrado |
| Leiloeiroqueiroz | https://www.leiloeiroqueiroz.com.br | Nenhum imóvel encontrado |
| Whleiloes | https://www.whleiloes.com.br | Nenhum imóvel encontrado |
| Superlanceleilao | https://www.superlanceleilao.com.br | Nenhum imóvel encontrado |
| Vizeuonline | https://www.vizeuonline.com.br | Nenhum imóvel encontrado |
| Melhorlanceleiloes | https://www.melhorlanceleiloes.com.br | Nenhum imóvel encontrado |
| Leiloeirospcom Br | https://www.leiloeirospcom.br | Nenhum imóvel encontrado |
| Publicumleiloes | https://www.publicumleiloes.com.br | Nenhum imóvel encontrado |
| Muckleiloes | https://www.muckleiloes.com.br | Nenhum imóvel encontrado |

---

## Plano de Ação Priorizado

### Fase 1: Quick Wins (Prioridade 5)
Leiloeiros cujo site funciona mas o scraper precisa ajuste. Maior ROI.


### Fase 2: Implementação Técnica (Prioridade 4)
Requer Playwright, headers especiais ou análise de API.

- **Vivaleiloes**: Site funciona mas estrutura HTML pode ter mudado
- **Biasileiloes**: Site funciona mas estrutura HTML pode ter mudado
- **Lancenoleilao**: Site funciona mas estrutura HTML pode ter mudado
- **Sold**: Proteção anti-bot detectada (Cloudflare/similar)
- **Leje**: Site funciona mas estrutura HTML pode ter mudado
- **Unileiloes**: Site funciona mas estrutura HTML pode ter mudado
- **Depaulaonline**: Site funciona mas estrutura HTML pode ter mudado
- **Lancetotal**: Site funciona mas estrutura HTML pode ter mudado
- **Frazaoleiloes**: Site funciona mas estrutura HTML pode ter mudado
- **Picellileiloes**: Site funciona mas estrutura HTML pode ter mudado

### Fase 3: Monitoramento (Prioridade 3)
Problemas temporários ou sites sem imóveis no momento.

- 17 leiloeiros para monitorar

### Fase 4: Baixa Prioridade (Prioridade 1-2)
Sites com problemas estruturais ou offline.

- 18 leiloeiros (considerar desativar temporariamente)

---

## URLs Descobertas

Novas URLs de listagem de imóveis encontradas automaticamente:

| Leiloeiro | URL Atual | URL Sugerida |
|-----------|-----------|--------------|
| Lut | https://www.lut.com.br | https://www.lut.com.br/imoveis |
| Portalzuk | https://www.portalzuk.com.br/ | https://www.portalzuk.com.br/leilao-de-imoveis |
| Hastapublica | https://www.hastapublica.com.br | https://www.hastapublica.com.br/leiloes |
| Hastavip | https://www.hastavip.com.br | https://www.hastavip.com.br/imoveis |
| Gilsoninumaruleiloes | https://www.gilsoninumaruleiloes.com.br | https://www.gilsoninumaruleiloes.com.br/imoveis |
| Psnleiloes | https://www.psnleiloes.com.br | https://www.psnleiloes.com.br/imoveis |
| Benedettoleiloes | https://www.benedettoleiloes.com.br | https://www.benedettoleiloes.com.br/leiloes |
| Kriegerleiloes | https://www.kriegerleiloes.com.br | https://www.kriegerleiloes.com.br/busca |
| Alencastroleiloes | https://www.alencastroleiloes.com.br | https://www.alencastroleiloes.com.br/leilao |
| Leiloesfreire | https://www.leiloesfreire.com.br | https://www.leiloesfreire.com.br/leiloes |
| Alvaroleiloes | https://www.alvaroleiloes.com.br | https://www.alvaroleiloes.com.br/leilao |
| Fabioleiloes | https://www.fabioleiloes.com.br | https://www.fabioleiloes.com.br/leilao |
| Leiloescentrooeste | https://www.leiloescentrooeste.com.br | https://www.leiloescentrooeste.com.br/leilao |
| Parquedosleiloes | https://www.parquedosleiloes.com.br | https://www.parquedosleiloes.com.br/leiloes |
| Rmmleiloes | https://www.rmmleiloes.com.br | https://www.rmmleiloes.com.br/busca |
| Mega Leilões | https://www.megaleiloes.com.br | https://www.megaleiloes.com.br/imoveis |
| Lunellileiloes | https://www.lunellileiloes.com.br | https://www.lunellileiloes.com.br/leiloes |
| Leiloesbonfadini | https://www.leiloesbonfadini.com.br | https://www.leiloesbonfadini.com.br/venda |
| Alexsandroleiloes | https://www.alexsandroleiloes.com.br | https://www.alexsandroleiloes.com.br/busca |
