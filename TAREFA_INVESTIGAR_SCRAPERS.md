# TAREFA AUTÔNOMA: Investigar e Corrigir Scrapers - FASE 1

**Data:** 2025-01-18
**Executor:** Cursor Agent
**Modo:** AUTÔNOMO - Execute sem parar para perguntar

---

## CONTEXTO

Diagnóstico revelou problemas sérios:
- 501 leiloeiros cadastrados
- Apenas 22 (4%) com status "success"
- 133 (27%) com erro
- 333 (66%) pendentes (nunca executados)
- 50.486 imóveis no banco, mas distribuição de `source` estranha

**Problema Principal:** A maioria dos imóveis parece não ter `source` preenchido corretamente.

---

## OBJETIVO

Entender por que:
1. 94% dos imóveis não têm fonte identificada
2. Scrapers retornam 0 imóveis
3. Grandes leiloeiros (Megaleiloes, Portalzuk, Sodresantoro) estão pendentes

---

## FASE 1: Analisar Distribuição de Sources

Crie o arquivo `leilao-backend/scripts/analisar_sources.py`:

```python
"""
Analisa distribuicao de sources e auctioneer_id nas properties
"""
import os
import sys

# Encoding para Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERRO: SUPABASE_URL ou SUPABASE_KEY nao configurados")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("ANALISE DE SOURCES E AUCTIONEER_ID")
print("=" * 60)

# 1. Total de imoveis
print("\n[1] TOTAL DE IMOVEIS")
result = supabase.table("properties").select("id", count="exact").execute()
total = result.count
print(f"  Total: {total}")

# 2. Distribuicao por SOURCE
print("\n[2] DISTRIBUICAO POR SOURCE")
# Buscar em batches para não estourar limite
all_sources = {}
offset = 0
batch_size = 1000

while True:
    result = supabase.table("properties").select("source").range(offset, offset + batch_size - 1).execute()
    if not result.data:
        break
    
    for p in result.data:
        src = p.get("source") or "NULL/VAZIO"
        all_sources[src] = all_sources.get(src, 0) + 1
    
    offset += batch_size
    if len(result.data) < batch_size:
        break
    
    # Limitar a 10 batches para teste
    if offset >= 10000:
        print(f"  (Amostra limitada a {offset} registros)")
        break

print(f"  Sources encontrados: {len(all_sources)}")
print("\n  Top 20 sources:")
for src, count in sorted(all_sources.items(), key=lambda x: -x[1])[:20]:
    pct = (count / sum(all_sources.values())) * 100
    print(f"    {src}: {count} ({pct:.1f}%)")

# 3. Distribuicao por AUCTIONEER_ID
print("\n[3] DISTRIBUICAO POR AUCTIONEER_ID")
all_auctioneers = {}
offset = 0

while True:
    result = supabase.table("properties").select("auctioneer_id").range(offset, offset + batch_size - 1).execute()
    if not result.data:
        break
    
    for p in result.data:
        aid = p.get("auctioneer_id") or "NULL/VAZIO"
        all_auctioneers[aid] = all_auctioneers.get(aid, 0) + 1
    
    offset += batch_size
    if len(result.data) < batch_size:
        break
    
    if offset >= 10000:
        print(f"  (Amostra limitada a {offset} registros)")
        break

print(f"  Auctioneer IDs encontrados: {len(all_auctioneers)}")
print("\n  Top 20 auctioneer_id:")
for aid, count in sorted(all_auctioneers.items(), key=lambda x: -x[1])[:20]:
    pct = (count / sum(all_auctioneers.values())) * 100
    print(f"    {aid}: {count} ({pct:.1f}%)")

# 4. Verificar imoveis sem source E sem auctioneer_id
print("\n[4] IMOVEIS SEM IDENTIFICACAO")
result = supabase.table("properties").select("id,title,source_url").is_("source", "null").is_("auctioneer_id", "null").limit(10).execute()
print(f"  Imoveis sem source E sem auctioneer_id: {len(result.data)} (amostra)")
if result.data:
    print("\n  Exemplos:")
    for p in result.data[:5]:
        print(f"    - {p.get('title', 'N/A')[:50]}")
        print(f"      URL: {p.get('source_url', 'N/A')[:80]}")

print("\n" + "=" * 60)
print("FIM DA ANALISE")
print("=" * 60)
```

Execute:
```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts/analisar_sources.py
```

---

## FASE 2: Verificar Estrutura dos Scrapers

Execute estes comandos para entender a arquitetura:

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# 1. Listar todos os scrapers
Write-Host "=== SCRAPERS DISPONIVEIS ===" -ForegroundColor Yellow
Get-ChildItem -Path "app/scrapers" -Filter "*.py" | Select-Object Name

# 2. Ver scraper_manager (como scrapers sao orquestrados)
Write-Host "`n=== SCRAPER MANAGER (primeiras 80 linhas) ===" -ForegroundColor Yellow
Get-Content "app/scrapers/scraper_manager.py" | Select-Object -First 80

# 3. Ver universal_scraper (se existir)
Write-Host "`n=== UNIVERSAL SCRAPER ===" -ForegroundColor Yellow
if (Test-Path "app/services/universal_scraper.py") {
    Get-Content "app/services/universal_scraper.py" | Select-Object -First 80
} else {
    Write-Host "Arquivo nao encontrado"
}

# 4. Ver como main.py chama os scrapers
Write-Host "`n=== MAIN.PY - Endpoints de scraping ===" -ForegroundColor Yellow
Select-String -Path "app/main.py" -Pattern "scrape|scraper" -SimpleMatch | Select-Object LineNumber, Line
```

---

## FASE 3: Testar Scraper Específico com Logs

Crie `leilao-backend/scripts/testar_megaleiloes_detalhado.py`:

```python
"""
Teste detalhado do scraper Megaleiloes
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("=" * 60)
print("TESTE DETALHADO - MEGALEILOES")
print("=" * 60)

# 1. Verificar credenciais
print("\n[1] VERIFICANDO CREDENCIAIS")
openai_key = os.getenv("OPENAI_API_KEY")
scrapingbee_key = os.getenv("SCRAPINGBEE_API_KEY")
print(f"  OPENAI_API_KEY: {'OK' if openai_key else 'FALTANDO'}")
print(f"  SCRAPINGBEE_API_KEY: {'OK' if scrapingbee_key else 'FALTANDO'}")

# 2. Tentar importar scrapers
print("\n[2] IMPORTANDO SCRAPERS")
try:
    from app.scrapers.scraper_manager import ScraperManager
    print("  ScraperManager: OK")
except ImportError as e:
    print(f"  ScraperManager: ERRO - {e}")

try:
    from app.services.universal_scraper import UniversalScraperService
    print("  UniversalScraperService: OK")
except ImportError as e:
    print(f"  UniversalScraperService: ERRO - {e}")

# 3. Listar scrapers disponiveis
print("\n[3] SCRAPERS REGISTRADOS")
try:
    manager = ScraperManager()
    if hasattr(manager, 'scrapers'):
        print(f"  Total: {len(manager.scrapers)}")
        for name in list(manager.scrapers.keys())[:10]:
            print(f"    - {name}")
    elif hasattr(manager, 'get_available_scrapers'):
        scrapers = manager.get_available_scrapers()
        print(f"  Total: {len(scrapers)}")
        for s in scrapers[:10]:
            print(f"    - {s}")
    else:
        print("  Estrutura do manager desconhecida")
        print(f"  Atributos: {dir(manager)}")
except Exception as e:
    print(f"  ERRO: {e}")

# 4. Testar scrape do Megaleiloes
print("\n[4] TESTANDO SCRAPE - MEGALEILOES")
url = "https://www.megaleiloes.com.br/"

try:
    # Tentar via UniversalScraperService
    scraper = UniversalScraperService()
    print(f"  URL: {url}")
    print("  Iniciando scrape (pode demorar)...")
    
    result = scraper.scrape_url(url, max_properties=3)
    
    print(f"  Resultado: {len(result) if result else 0} imoveis")
    
    if result:
        for i, prop in enumerate(result[:3]):
            print(f"\n  Imovel {i+1}:")
            print(f"    Titulo: {prop.get('title', 'N/A')[:50]}")
            print(f"    Cidade: {prop.get('city', 'N/A')}")
            print(f"    Estado: {prop.get('state', 'N/A')}")
            print(f"    Preco: {prop.get('price', 'N/A')}")
            print(f"    Source: {prop.get('source', 'N/A')}")
    else:
        print("  NENHUM IMOVEL EXTRAIDO!")
        
except Exception as e:
    print(f"  ERRO durante scrape: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("FIM DO TESTE")
print("=" * 60)
```

Execute:
```bash
python scripts/testar_megaleiloes_detalhado.py
```

---

## FASE 4: Documentar Descobertas

Crie o arquivo `INVESTIGACAO_SCRAPERS.md` na raiz do projeto com:

1. Resultado da análise de sources
2. Estrutura dos scrapers encontrada
3. Resultado do teste do Megaleiloes
4. Problemas identificados
5. Próximos passos recomendados

---

## CRITÉRIOS DE SUCESSO

- [ ] Script `analisar_sources.py` executado
- [ ] Estrutura dos scrapers documentada
- [ ] Teste do Megaleiloes executado
- [ ] `INVESTIGACAO_SCRAPERS.md` criado com descobertas
- [ ] Identificado o motivo dos 0 imóveis

---

## INSTRUÇÕES PARA O CURSOR AGENT

1. Execute FASE 1 primeiro e analise resultado
2. Execute FASE 2 para entender arquitetura
3. Execute FASE 3 para testar scraper real
4. Documente TUDO em `INVESTIGACAO_SCRAPERS.md`
5. Se encontrar erros, tente corrigi-los
6. Se precisar de credenciais, elas estão em `.env`

**MODO AUTÔNOMO:** Não pare para perguntar. Execute tudo e documente.
