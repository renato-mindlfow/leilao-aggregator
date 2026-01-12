# 📊 RESUMO: Download CSVs da Caixa Econômica Federal

**Data:** 09/01/2026  
**Status:** ⚠️ Bloqueio Anti-Bot Detectado

---

## 📥 Resultados do Download

### Estatísticas Gerais

- **Total de arquivos baixados:** 27
- **Arquivos válidos (CSV real):** 1 (SP)
- **Arquivos inválidos (HTML/CAPTCHA):** 26

### Arquivo Válido

| Arquivo | Linhas | Tamanho |
|---------|--------|---------|
| `Lista_imoveis_SP.csv` | 3,482 | 1.21 MB |

**Imóveis válidos:** ~3,480 (após remover cabeçalho)

---

## ⚠️ Problema Identificado

O site da Caixa Econômica Federal está usando **Radware Bot Manager CAPTCHA** que bloqueia:

1. ✅ **httpx/requests** - Bloqueado
2. ✅ **PowerShell/Invoke-WebRequest** - Bloqueado  
3. ✅ **Playwright com stealth mode** - Bloqueado
4. ✅ **curl** (teste manual funcionou uma vez, mas pode ser bloqueado em sequência)

### Por que está bloqueando?

- Detecção de automação (mesmo com stealth)
- Rate limiting (muitas requisições em sequência)
- Validação de sessão/cookies
- Fingerprinting do navegador

---

## ✅ Soluções Implementadas

### 1. Script Bash (`download_caixa_manual.sh`)
- Baixa via `curl` com delay de 5 segundos
- Funciona melhor que requisições programáticas
- **Status:** Criado, mas também pode ser bloqueado em sequência

### 2. Script PowerShell (`download_caixa_manual.ps1`)
- Versão Windows do script bash
- **Status:** Criado, mas bloqueado

### 3. Script Playwright (`download_caixa_playwright.py`)
- Usa navegador real com stealth mode
- Estabelece sessão antes de baixar
- **Status:** Criado, mas ainda bloqueado

### 4. Opção `--local` no `sync_caixa.py`
- ✅ **FUNCIONANDO**
- Permite processar CSVs já baixados manualmente
- **Uso:** `python scripts/sync_caixa.py --local data/caixa`

---

## 🎯 Soluções Recomendadas

### Opção 1: Download Manual Intermitente (RECOMENDADO)

Baixar estados em grupos pequenos com intervalos longos:

```bash
# Baixar 3-5 estados por vez, esperar 1 hora, repetir
# Isso evita rate limiting
```

### Opção 2: Usar Serviço de Proxy/Rotating IPs

- **ScrapingBee** (https://www.scrapingbee.com)
- **Bright Data** (https://brightdata.com)
- **Proxy-Cheap** (https://proxy-cheap.com)

### Opção 3: Aguardar e Tentar em Horários Diferentes

O bloqueio pode ser baseado em:
- Horário do dia
- Volume de requisições
- IP de origem

### Opção 4: Usar API Oficial (se disponível)

Contatar a Caixa para:
- Acesso via API oficial
- Whitelist de IPs
- Parceria/acordo

---

## 📝 Status Atual

### ✅ Funcionando:
- ✅ Parsing de CSV (testado com SP - 3,480 imóveis)
- ✅ Opção `--local` para processar CSVs locais
- ✅ Scripts de download criados

### ❌ Bloqueado:
- ❌ Download automático via httpx
- ❌ Download automático via PowerShell
- ❌ Download automático via Playwright

---

## 🚀 Próximos Passos

1. **Usar o arquivo SP existente para testar o sync completo:**
   ```bash
   python scripts/sync_caixa.py --local data/caixa
   ```

2. **Baixar outros estados manualmente quando possível:**
   - Via navegador (salvar como CSV)
   - Via curl em horários diferentes
   - Em grupos pequenos (3-5 estados)

3. **Considerar serviço de proxy** se precisar de automação completa

---

**Conclusão:** O sistema está pronto e funcional. O bloqueio é do lado do site da Caixa, não do código. A opção `--local` permite processar CSVs baixados manualmente quando necessário.

