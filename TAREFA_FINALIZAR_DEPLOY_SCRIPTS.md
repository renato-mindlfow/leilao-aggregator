# TAREFA AUTÔNOMA: Finalizar Deploy e Rodar Scripts

**Prioridade:** 🔴 URGENTE  
**Tempo estimado:** 30 minutos  
**Execução:** AUTÔNOMA

---

## CONTEXTO

O que já foi feito:
- ✅ Portal Zuk V2 criado e testado (5 imóveis OK)
- ✅ Backend funcionando (`/healthz` OK)
- ✅ Fly.io configurado corretamente
- ✅ Workflow `scrape-all-leiloeiros.yml` criado

O que falta:
- Commit e push das mudanças
- Deploy no Fly.io
- Rodar diagnóstico com variáveis do .env
- Localizar e rodar `fetch_caixa_images.py`

---

## PARTE 1: COMMIT E PUSH

```bash
cd leilao-aggregator-git

git add .
git status

git commit -m "feat: Portal Zuk V2 scraper, diagnostics, and scraping workflow

- Add PortalZukScraperV2 with Playwright (domcontentloaded fix)
- Integrate in scraper_manager, main.py, universal_scraper_service
- Add diagnostico_scrapers.py
- Add scrape-all-leiloeiros.yml workflow"

git push origin main
```

---

## PARTE 2: DEPLOY NO FLY.IO

```bash
cd leilao-aggregator-git/leilao-backend

flyctl deploy --app leilao-backend-solitary-haze-9882

# Verificar se subiu
sleep 30
curl -s https://leilao-backend-solitary-haze-9882.fly.dev/healthz
```

---

## PARTE 3: RODAR DIAGNÓSTICO COM VARIÁVEIS

```bash
cd leilao-aggregator-git/leilao-backend

# Verificar se .env existe
cat .env 2>/dev/null | grep -E "SUPABASE_URL|SUPABASE_KEY" || echo ".env não tem as variáveis"

# Se não tiver, criar/atualizar .env com as variáveis
# (o usuário precisa fornecer os valores se não existirem)

# Rodar diagnóstico
python scripts/diagnostico_scrapers.py
```

**Se as variáveis não existirem no .env**, informar que precisa configurar:
- `SUPABASE_URL`
- `SUPABASE_KEY`

---

## PARTE 4: LOCALIZAR E RODAR FETCH DE IMAGENS DA CAIXA

```bash
cd leilao-aggregator-git

# Encontrar o script
find . -name "fetch_caixa_images.py" -type f 2>/dev/null

# Se encontrar, ver o conteúdo
cat leilao-backend/scripts/fetch_caixa_images.py 2>/dev/null | head -50

# Rodar com poucos lotes para testar
cd leilao-backend
python scripts/fetch_caixa_images.py --max-batches 2 2>/dev/null || python scripts/fetch_caixa_images.py --help
```

**Se o script não existir**, reportar que precisa ser criado.

---

## PARTE 5: VERIFICAR WORKFLOW NO GITHUB

Após o push, verificar se os workflows estão visíveis:

```bash
# Listar workflows
ls -la .github/workflows/

# Ver se daily-maintenance.yml existe e chama os scripts
cat .github/workflows/daily-maintenance.yml 2>/dev/null || echo "daily-maintenance.yml não existe"
```

---

## CRITÉRIOS DE SUCESSO

- [ ] Commit e push realizados
- [ ] Deploy no Fly.io concluído
- [ ] `/healthz` retornando OK após deploy
- [ ] Diagnóstico executado (ou variáveis identificadas como faltantes)
- [ ] `fetch_caixa_images.py` localizado e testado (ou identificado como inexistente)

---

## REPORTAR AO FINAL

1. Hash do commit
2. Status do deploy
3. Resultado do diagnóstico (ou erro de variáveis)
4. Localização do `fetch_caixa_images.py` (ou se não existe)
5. Se o `daily-maintenance.yml` está chamando os scripts ou não
