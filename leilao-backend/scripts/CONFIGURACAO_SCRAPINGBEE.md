# 🔑 Configuração do ScrapingBee no Projeto

## 📍 Onde o ScrapingBee está configurado

### 1. **Arquivo Principal: `app/utils/fetcher.py`**
   - Classe: `MultiLayerFetcher`
   - Linha 46: `self.scrapingbee_api_key = scrapingbee_api_key or os.getenv("SCRAPINGBEE_API_KEY")`
   - Usado como **Camada 3** de fallback para bypass de proteções anti-bot

### 2. **Script de Download Caixa: `scripts/download_caixa_scrapingbee.py`**
   - Linha 16: `SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")`
   - Carrega via `load_dotenv()` se disponível

### 3. **Deploy Script: `scripts/deploy.sh`**
   - Linhas 38-40: Configura secret no Fly.io se presente no `.env`

## 🔍 Status Atual

**❌ API Key NÃO encontrada localmente:**
- Arquivo `.env` existe mas não contém `SCRAPINGBEE_API_KEY`
- Variável de ambiente não está configurada

## ✅ Como Configurar

### Opção 1: Arquivo `.env` (Recomendado para desenvolvimento)

Edite `leilao-aggregator-git/leilao-backend/.env` e adicione:

```env
SCRAPINGBEE_API_KEY=sua-chave-aqui
```

### Opção 2: Variável de Ambiente (Windows PowerShell)

```powershell
$env:SCRAPINGBEE_API_KEY="sua-chave-aqui"
```

### Opção 3: Variável de Ambiente (Linux/Mac)

```bash
export SCRAPINGBEE_API_KEY="sua-chave-aqui"
```

### Opção 4: Fly.io Secrets (Produção)

Se a API key estiver configurada no Fly.io como secret, ela estará disponível em produção, mas não localmente.

Para verificar secrets do Fly.io:
```bash
flyctl secrets list --app leilao-backend-solitary-haze-9882
```

Para configurar:
```bash
flyctl secrets set SCRAPINGBEE_API_KEY="sua-chave" --app leilao-backend-solitary-haze-9882
```

## 🧪 Teste

Após configurar, teste com:

```bash
cd leilao-aggregator-git/leilao-backend
python scripts/download_caixa_scrapingbee.py
```

## 📝 Notas

- O projeto usa `python-dotenv` para carregar `.env` automaticamente
- A API key é usada em múltiplos lugares:
  - `fetcher.py` (camada 3 de fallback)
  - `download_caixa_scrapingbee.py` (download de CSVs da Caixa)
- Se não configurada, o sistema continua funcionando mas sem acesso ao ScrapingBee

