# 🔍 DIAGNÓSTICO COMPLETO: GitHub Actions Workflows

**Data:** 2026-01-06  
**Objetivo:** Verificar todos os workflows e identificar problemas

---

## 📋 WORKFLOWS ENCONTRADOS

Foram identificados **4 workflows** no diretório `.github/workflows/`:

### 1. **daily-maintenance.yml**
- **Trigger:** 
  - Schedule: `0 7 * * *` (4h BRT / 7h UTC - diariamente)
  - Manual: `workflow_dispatch`
- **Função:** Executa manutenção diária do banco de dados
- **Secrets necessários:**
  - `DATABASE_URL` ✅
  - `SUPABASE_URL` ✅
  - `SUPABASE_KEY` ✅
- **Status:** ✅ Configurado corretamente
- **Observações:** 
  - Instala dependências do sistema (`libpq-dev`)
  - Instala Python dependencies via `requirements.txt`
  - Instala Playwright browsers
  - Executa `scripts/daily_maintenance.py`

---

### 2. **daily-sync.yml**
- **Trigger:**
  - Schedule: `0 9 * * *` (6h BRT / 9h UTC - diariamente)
  - Manual: `workflow_dispatch`
- **Função:** Sincroniza dados via API
- **Secrets necessários:**
  - `API_URL` ⚠️ (não documentado em GITHUB_SECRETS_SETUP.md)
- **Status:** ⚠️ Pode falhar se `API_URL` não estiver configurado
- **Observações:**
  - Faz POST para `/api/sync/start`
  - Monitora status por até 1 hora
  - Usa `curl` e `jq` (jq precisa estar instalado no runner)

---

### 3. **deploy.yml** ⚠️ **ESTE É O QUE ESTÁ FALHANDO**
- **Trigger:**
  - **Push para branch `main`** ✅ (dispara automaticamente)
  - Manual: `workflow_dispatch`
- **Função:** Deploy automático para Fly.io
- **Secrets necessários:**
  - `FLY_API_TOKEN` ⚠️ **CRÍTICO - Provavelmente não configurado ou inválido**
- **Status:** ❌ **FALHANDO** (Deploy to Fly.io #10)
- **Observações:**
  - Usa `superfly/flyctl-actions/setup-flyctl@master`
  - Executa `flyctl deploy --remote-only` no diretório `leilao-backend`
  - Requer `fly.toml` no diretório `leilao-backend` ✅ (arquivo existe)
  - **Problema provável:** `FLY_API_TOKEN` não configurado ou token inválido/expirado

---

### 4. **scraping-diario.yml**
- **Trigger:**
  - Schedule: `0 7 * * *` (4h BRT / 7h UTC - diariamente)
  - Manual: `workflow_dispatch`
- **Função:** Executa scraping diário de todos os sites
- **Secrets necessários:**
  - `SUPABASE_URL` ✅
  - `SUPABASE_KEY` ✅
- **Status:** ✅ Configurado corretamente
- **Observações:**
  - Instala dependências do sistema para Playwright
  - Instala Python dependencies
  - Executa `scripts/run_all_scrapers.py`
  - Executa `scripts/consolidate_and_update_configs.py`
  - Faz commit automático dos resultados (pode falhar se não tiver permissões)

---

## ❌ WORKFLOW QUE FALHOU: **deploy.yml**

### Problema Identificado

**Workflow:** `Deploy to Fly.io #10`  
**Arquivo:** `.github/workflows/deploy.yml`

### Possíveis Causas:

1. **🔴 Secret `FLY_API_TOKEN` não configurado**
   - O secret pode não existir no GitHub
   - Acesse: Settings → Secrets and variables → Actions
   - Verifique se `FLY_API_TOKEN` está presente

2. **🔴 Token inválido ou expirado**
   - O token pode ter sido revogado
   - O token pode ter expirado
   - O token pode não ter permissões suficientes

3. **🔴 Problema com o Fly.io CLI**
   - A action `superfly/flyctl-actions/setup-flyctl@master` pode ter problemas
   - O comando `flyctl deploy --remote-only` pode estar falhando

4. **🔴 Problema com o arquivo `fly.toml`**
   - O arquivo existe ✅, mas pode ter configurações incorretas
   - Pode estar faltando configurações necessárias

5. **🔴 Problema de permissões no repositório**
   - O workflow pode não ter permissão para fazer deploy
   - Pode precisar de permissões específicas no Fly.io

---

## 🔧 O QUE PRECISA SER CORRIGIDO

### Ação Imediata Necessária:

1. **Verificar Secret `FLY_API_TOKEN`:**
   ```
   - Acesse: https://github.com/renato-mindlfow/leilao-aggregator/settings/secrets/actions
   - Verifique se `FLY_API_TOKEN` existe
   - Se não existir, crie:
     a. Obtenha o token em: https://fly.io/user/personal_access_tokens
     b. Adicione como secret no GitHub
   ```

2. **Verificar logs do erro:**
   ```
   - Acesse: https://github.com/renato-mindlfow/leilao-aggregator/actions/runs/[ID_DO_RUN]
   - Copie a mensagem de erro completa
   - Identifique em qual step falhou
   ```

3. **Verificar configuração do Fly.io:**
   ```
   - Verificar se o app existe no Fly.io
   - Verificar se o fly.toml está correto
   - Testar deploy manual: flyctl deploy --remote-only
   ```

4. **Atualizar documentação:**
   - Adicionar `FLY_API_TOKEN` e `API_URL` ao `GITHUB_SECRETS_SETUP.md`

---

## 📊 RESUMO DE SECRETS NECESSÁRIOS

### Secrets Obrigatórios (por workflow):

| Secret | Workflows que usam | Status |
|--------|-------------------|--------|
| `DATABASE_URL` | daily-maintenance.yml | ✅ Documentado |
| `SUPABASE_URL` | daily-maintenance.yml, scraping-diario.yml | ✅ Documentado |
| `SUPABASE_KEY` | daily-maintenance.yml, scraping-diario.yml | ✅ Documentado |
| `FLY_API_TOKEN` | deploy.yml | ❌ **NÃO DOCUMENTADO** |
| `API_URL` | daily-sync.yml | ❌ **NÃO DOCUMENTADO** |

---

## 🎯 WORKFLOWS QUE RODAM EM "PUSH"

Apenas **1 workflow** está configurado para rodar em `push`:

- ✅ **deploy.yml** - Roda em `push` para branch `main`

**Observação:** Isso significa que **TODA vez que houver push para `main`**, o deploy será tentado. Se o `FLY_API_TOKEN` não estiver configurado, **todos os pushes falharão**.

---

## 📝 RECOMENDAÇÕES

1. **Urgente:** Configurar `FLY_API_TOKEN` no GitHub Secrets
2. **Urgente:** Verificar logs do erro #10 para identificar causa exata
3. **Importante:** Adicionar `FLY_API_TOKEN` e `API_URL` à documentação
4. **Opcional:** Considerar adicionar verificação de secrets antes do deploy
5. **Opcional:** Adicionar step de validação do `fly.toml` antes do deploy

---

## ✅ CONCLUSÃO

- **Total de workflows:** 4
- **Workflows com problemas:** 1 (deploy.yml)
- **Workflows configurados para push:** 1 (deploy.yml)
- **Secrets faltando documentação:** 2 (FLY_API_TOKEN, API_URL)

**Próximo passo:** Verificar e configurar o secret `FLY_API_TOKEN` no GitHub.

