# 🚀 INSTRUÇÕES - Scraper TOP 10 Leiloeiros

## Resumo

Este script faz scraping dos **10 maiores leiloeiros** identificados no concorrente, com potencial de **~3.900 imóveis**.

## URLs Verificadas

| # | Leiloeiro | URL | Imóveis Esperados |
|---|-----------|-----|-------------------|
| 1 | ARG Leilões | www.argleiloes.com.br | 599 |
| 2 | Realiza Leilões | www.realizaleiloes.com.br | 598 |
| 3 | Isaias Leilões | www.isaiasleiloes.com.br | 544 |
| 4 | Leilões Ceruli | www.leiloesceruli.com.br | 537 |
| 5 | MGL Leilões | www.mgl.com.br | 447 |
| 6 | Leilões RN | www.leiloesrn.com.br | 321 |
| 7 | Grupo Lance | www.grupolance.com.br | 247 |
| 8 | LB Leilões | www.lbleiloes.com.br | 213 |
| 9 | Globo Leilões | globoleiloes.com.br | 209 |
| 10 | TrustBid | www.trustbid.com.br | 188 |

**Total: ~3.903 imóveis**

---

## Instalação

```bash
# 1. Instalar dependências
pip install playwright psycopg2-binary python-dotenv

# 2. Instalar Chromium para Playwright
playwright install chromium
```

---

## Configuração

Crie um arquivo `.env` na mesma pasta:

```env
DATABASE_URL=postgresql://postgres.nawbptwbmdgrkbpbwxzl:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

---

## Uso

### Execução Completa (10 leiloeiros, 50 imóveis cada)
```bash
python SCRAPER_TOP10_LEILOEIROS.py
```

### Testar com 3 leiloeiros
```bash
python SCRAPER_TOP10_LEILOEIROS.py --limit 3
```

### Ver o navegador (debug)
```bash
python SCRAPER_TOP10_LEILOEIROS.py --headless false --limit 1
```

### Não salvar no banco (apenas JSON)
```bash
python SCRAPER_TOP10_LEILOEIROS.py --no-db
```

### Mais propriedades por leiloeiro
```bash
python SCRAPER_TOP10_LEILOEIROS.py --max-properties 100
```

---

## Saída

O script gera:

1. **Console**: Progresso e estatísticas em tempo real
2. **JSON**: Arquivo `top10_scraping_YYYYMMDD_HHMMSS.json` com todos os dados
3. **Banco**: Insere/atualiza na tabela `properties` do Supabase

---

## Estrutura dos Dados Coletados

```json
{
  "title": "Apartamento 2 quartos - Centro",
  "source_url": "https://www.argleiloes.com.br/imovel/12345",
  "auctioneer_id": "arg_leiloes",
  "auctioneer_name": "ARG Leilões",
  "state": "SP",
  "city": "São Paulo",
  "category": "Apartamento",
  "auction_type": "Judicial",
  "evaluation_value": 350000.00,
  "first_auction_value": 280000.00,
  "second_auction_value": 210000.00,
  "discount_percentage": 40.0,
  "area_total": 65.5,
  "image_url": "https://...",
  "first_auction_date": "2026-01-15"
}
```

---

## Técnicas de Stealth

O script usa várias técnicas para evitar bloqueio:

1. **Playwright** ao invés de Selenium
2. **Stealth Scripts** que ocultam automação
3. **User-Agent** de Chrome real
4. **Headers** completos de navegador
5. **Rate limiting** (1.5s entre requisições)
6. **Scroll** para carregar lazy content

---

## Troubleshooting

### "Playwright não instalado"
```bash
pip install playwright
playwright install chromium
```

### "DATABASE_URL não configurada"
- Verifique se o arquivo `.env` existe
- Ou passe `--no-db` para salvar apenas JSON

### "Timeout ao acessar site"
- Aumente o timeout no código (linha ~190)
- Ou tente com `--headless false` para ver o que acontece

### "Bloqueio Cloudflare persistente"
- O script já tem stealth, mas alguns sites são mais rígidos
- Considere usar ScrapingBee como fallback

---

## Próximos Passos

Após executar este script:

1. Verificar dados coletados no JSON
2. Validar no Supabase (tabela `properties`)
3. Ajustar seletores específicos se necessário
4. Expandir para os próximos 20 leiloeiros

---

## Suporte

Em caso de dúvidas, verifique:
- `BASE_DE_CONHECIMENTO_ERROS_E_FIXES.md`
- `padrao_scrapers_complexos.md`
- `CONTEXT_SYNC_MASTER.md`
