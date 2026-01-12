# 🚀 Instruções de Instalação - Scraper TOP 10 + GitHub Actions

## 📁 Arquivos Criados

| Arquivo | Destino | Descrição |
|---------|---------|-----------|
| `SCRAPER_TOP10_CORRIGIDO.py` | `leilao-backend/scripts/` | Script corrigido com seletores específicos |
| `scrape-top10-leiloeiros.yml` | `.github/workflows/` | Workflow GitHub Actions |

---

## ✅ Correções Aplicadas

### Seletores Corrigidos:

| Leiloeiro | Antes | Depois | Status |
|-----------|-------|--------|--------|
| ARG Leilões | ✅ OK | ✅ OK | Funcionando |
| Realiza Leilões | ✅ OK | ✅ OK | Funcionando |
| Isaias Leilões | `/imoveis` | `/` + `a[href*='/leilao/']` | **CORRIGIDO** |
| Leilões Ceruli | `/` | `/` + `a[href*='/leilao/']` | **CORRIGIDO** |
| MGL | `/leiloes` | `/` + `a[href*='/leilao/']` | **CORRIGIDO** |
| Demais | Genérico | Múltiplos seletores alternativos | **MELHORADO** |

---

## 📋 Passo a Passo

### 1. Copiar o Script Corrigido

```powershell
# Copiar para pasta de scripts
copy SCRAPER_TOP10_CORRIGIDO.py C:\LeiloHub\leilao-aggregator-git\leilao-backend\scripts\
```

### 2. Testar Localmente (Recomendado)

```powershell
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# Testar apenas 3 leiloeiros primeiro
python scripts/SCRAPER_TOP10_CORRIGIDO.py --limit 3

# Se funcionar, rodar todos os 10
python scripts/SCRAPER_TOP10_CORRIGIDO.py --limit 10
```

### 3. Instalar Workflow GitHub Actions

```powershell
# Criar pasta se não existir
mkdir -p C:\LeiloHub\leilao-aggregator-git\.github\workflows

# Copiar workflow
copy scrape-top10-leiloeiros.yml C:\LeiloHub\leilao-aggregator-git\.github\workflows\
```

### 4. Configurar Secrets no GitHub

1. Acesse: `https://github.com/SEU_USUARIO/leilao-aggregator/settings/secrets/actions`
2. Adicione o secret:
   - **Name:** `DATABASE_URL`
   - **Value:** `postgresql://postgres.nawbptwbmdgrkbpbwxzl:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres`

### 5. Fazer Push

```powershell
cd C:\LeiloHub\leilao-aggregator-git

git add .
git commit -m "feat: add TOP 10 scraper with corrected selectors + GitHub Actions"
git push origin main
```

### 6. Verificar Workflow

1. Acesse: `https://github.com/SEU_USUARIO/leilao-aggregator/actions`
2. Veja o workflow "Scrape TOP 10 Leiloeiros + Universal"
3. Clique em "Run workflow" para executar manualmente

---

## ⏰ Agendamento Automático

O workflow executa automaticamente:
- **06:00 BRT** (manhã)
- **18:00 BRT** (noite)

---

## 🔧 Execução Manual

No GitHub Actions, você pode escolher:

| Opção | Descrição |
|-------|-----------|
| `all` | TOP 10 + Universal Scraper + Caixa |
| `top10` | Apenas TOP 10 leiloeiros |
| `universal` | Apenas Universal Scraper |

---

## 📊 O Que o Workflow Faz

```
1. scrape-top10 (Job 1)
   ├── Instala Playwright + Chromium
   ├── Executa SCRAPER_TOP10_CORRIGIDO.py
   ├── Salva resultados no Supabase
   └── Gera JSON com resultados

2. scrape-universal (Job 2)
   ├── Processa demais 481 leiloeiros
   └── Usa Universal Scraper existente

3. sync-caixa (Job 3)
   └── Sincroniza dados da Caixa Econômica

4. report (Job 4)
   └── Gera relatório consolidado
```

---

## 📈 Impacto Esperado

| Fonte | Imóveis Atuais | Imóveis Esperados |
|-------|---------------|-------------------|
| Caixa Econômica | ~28.000 | ~28.000 |
| TOP 10 Leiloeiros | 59 (teste) | ~3.900 |
| Universal Scraper | ~23.000 | ~27.000 |
| **TOTAL** | ~51.000 | **~59.000** |

**Crescimento esperado: +15%**

---

## ❓ Troubleshooting

### "Playwright não encontrado"
```bash
pip install playwright
playwright install chromium
```

### "DATABASE_URL não configurada"
- Verifique se o secret está configurado no GitHub
- Localmente: crie arquivo `.env` com a variável

### "0 propriedades encontradas"
- Verifique os logs do workflow
- O site pode ter mudado estrutura
- Execute com `--headless false` localmente para debug

---

## 📞 Próximos Passos

Após instalar e testar:

1. ✅ Verificar se todos os 10 leiloeiros estão coletando dados
2. ✅ Monitorar execuções automáticas por 2-3 dias
3. 📋 Expandir para os próximos 20 leiloeiros (medium tier)
4. 🔧 Ajustar seletores conforme necessário

---

**Criado em:** 12/01/2026  
**Versão:** 2.0 (Corrigida)
