# TAREFA AUTÔNOMA: Diagnóstico e Correção de Scrapers LeiloHub

**Data:** 2025-01-18
**Executor:** Claude Code no Cursor
**Modo:** AUTÔNOMO - Execute sem parar para perguntar

---

## CONTEXTO

O LeiloHub tem 289 leiloeiros cadastrados, mas apenas 28 (10%) estão funcionando. 
94% dos imóveis vêm da Caixa Econômica Federal (CSV), não dos scrapers.

**Problema Principal:** Scrapers não estão extraindo dados corretamente.

---

## FASE 1: DIAGNÓSTICO (Execute Primeiro)

### 1.1 Verificar Estrutura do Projeto

```bash
# Navegar para o projeto
cd C:\LeiloHub\leilao-aggregator

# Listar estrutura do backend
ls -la leilao-backend/app/scrapers/
ls -la leilao-backend/scripts/
```

### 1.2 Verificar Estado dos Leiloeiros no Banco

```bash
# Criar script de diagnóstico que NÃO usa emojis (evitar UnicodeEncodeError)
cd leilao-backend
```

Crie o arquivo `scripts/diagnostico_scrapers_v2.py`:

```python
"""
Diagnostico de scrapers - versao sem emojis para Windows
"""
import os
import sys
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

# Verificar variaveis
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

print("=" * 60)
print("DIAGNOSTICO DE SCRAPERS - LEILOHUB")
print("=" * 60)

# Verificar configuracao
print("\n[1] VERIFICANDO CONFIGURACAO")
print(f"  SUPABASE_URL: {'OK' if SUPABASE_URL else 'FALTANDO'}")
print(f"  SUPABASE_KEY: {'OK' if SUPABASE_KEY else 'FALTANDO'}")
print(f"  DATABASE_URL: {'OK' if DATABASE_URL else 'FALTANDO'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n[ERRO] Variaveis Supabase nao configuradas!")
    print("Adicione ao .env:")
    print("  SUPABASE_URL=https://xxx.supabase.co")
    print("  SUPABASE_KEY=eyJ...")
    sys.exit(1)

# Conectar ao Supabase
try:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("  Conexao Supabase: OK")
except Exception as e:
    print(f"  Conexao Supabase: ERRO - {e}")
    sys.exit(1)

# Consultar auctioneers
print("\n[2] CONSULTANDO LEILOEIROS")
try:
    result = supabase.table("auctioneers").select("*").execute()
    auctioneers = result.data
    print(f"  Total de leiloeiros: {len(auctioneers)}")
    
    # Contar por status
    status_count = {}
    for a in auctioneers:
        status = a.get("scrape_status", "unknown")
        status_count[status] = status_count.get(status, 0) + 1
    
    print("\n  Status dos scrapers:")
    for status, count in sorted(status_count.items()):
        print(f"    {status}: {count}")
    
except Exception as e:
    print(f"  ERRO ao consultar: {e}")
    sys.exit(1)

# Consultar propriedades
print("\n[3] CONSULTANDO PROPRIEDADES")
try:
    # Total
    result = supabase.table("properties").select("id", count="exact").execute()
    total = result.count
    print(f"  Total de imoveis: {total}")
    
    # Por fonte
    result = supabase.table("properties").select("source").execute()
    sources = {}
    for p in result.data:
        src = p.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    
    print("\n  Imoveis por fonte:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1])[:10]:
        pct = (count / total * 100) if total > 0 else 0
        print(f"    {src}: {count} ({pct:.1f}%)")
    
except Exception as e:
    print(f"  ERRO ao consultar: {e}")

# Listar leiloeiros com erro
print("\n[4] LEILOEIROS COM ERRO")
try:
    result = supabase.table("auctioneers").select("name,website,scrape_status,scrape_error").eq("scrape_status", "error").limit(20).execute()
    
    if result.data:
        for a in result.data[:10]:
            print(f"  - {a.get('name', 'N/A')}")
            print(f"    Website: {a.get('website', 'N/A')}")
            print(f"    Erro: {a.get('scrape_error', 'N/A')[:100]}...")
            print()
    else:
        print("  Nenhum leiloeiro com erro encontrado")
        
except Exception as e:
    print(f"  ERRO: {e}")

# Listar leiloeiros pendentes
print("\n[5] LEILOEIROS PENDENTES (nunca executados)")
try:
    result = supabase.table("auctioneers").select("name,website").eq("scrape_status", "pending").limit(20).execute()
    
    if result.data:
        print(f"  Total pendentes: {len(result.data)} (mostrando 10)")
        for a in result.data[:10]:
            print(f"  - {a.get('name', 'N/A')}: {a.get('website', 'N/A')}")
    else:
        print("  Nenhum leiloeiro pendente")
        
except Exception as e:
    print(f"  ERRO: {e}")

print("\n" + "=" * 60)
print("FIM DO DIAGNOSTICO")
print("=" * 60)
```

### 1.3 Executar Diagnóstico

```bash
cd leilao-backend
python scripts/diagnostico_scrapers_v2.py
```

---

## FASE 2: IDENTIFICAR PROBLEMAS ESPECÍFICOS

### 2.1 Verificar Scrapers Existentes

```bash
# Listar todos os scrapers
find . -name "*scraper*.py" -type f

# Verificar imports e dependências
grep -r "from app.scrapers" --include="*.py" .
```

### 2.2 Analisar Scraper Manager

```bash
# Localizar e examinar scraper_manager
cat app/scrapers/scraper_manager.py | head -100
```

### 2.3 Verificar Universal Scraper

```bash
# Ver estrutura do universal scraper
cat app/services/universal_scraper.py | head -150
```

---

## FASE 3: TESTAR SCRAPERS INDIVIDUALMENTE

### 3.1 Criar Script de Teste Unitário

Crie `scripts/testar_scraper_individual.py`:

```python
"""
Testa um scraper individual para diagnostico
Uso: python scripts/testar_scraper_individual.py <website_url>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def testar_scraper(url: str):
    print(f"Testando scraper para: {url}")
    print("-" * 60)
    
    try:
        # Tentar importar universal scraper
        from app.services.universal_scraper import UniversalScraperService
        
        scraper = UniversalScraperService()
        
        # Tentar scrape
        result = scraper.scrape_url(url, max_properties=3)
        
        print(f"Resultado: {len(result) if result else 0} imoveis")
        
        if result:
            for i, prop in enumerate(result[:3]):
                print(f"\nImovel {i+1}:")
                print(f"  Titulo: {prop.get('title', 'N/A')[:50]}")
                print(f"  Cidade: {prop.get('city', 'N/A')}")
                print(f"  Estado: {prop.get('state', 'N/A')}")
                print(f"  Preco: {prop.get('price', 'N/A')}")
                print(f"  URL: {prop.get('source_url', 'N/A')[:80]}")
        else:
            print("Nenhum imovel extraido!")
            
    except ImportError as e:
        print(f"Erro de import: {e}")
        print("Tentando scraper generico...")
        
        try:
            from app.scrapers.generic_scraper import GenericScraper
            scraper = GenericScraper()
            result = scraper.scrape(url, max_properties=3)
            print(f"Resultado (generico): {len(result) if result else 0} imoveis")
        except Exception as e2:
            print(f"Erro no scraper generico: {e2}")
            
    except Exception as e:
        print(f"Erro durante scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Testar com URL conhecida
        test_urls = [
            "https://www.megaleiloes.com.br",
            "https://www.sodresantoro.com.br",
            "https://www.lfreiloes.com.br",
        ]
        for url in test_urls:
            testar_scraper(url)
            print("\n" + "=" * 60 + "\n")
    else:
        testar_scraper(sys.argv[1])
```

### 3.2 Executar Testes

```bash
python scripts/testar_scraper_individual.py
```

---

## FASE 4: CORREÇÕES NECESSÁRIAS

### 4.1 Corrigir Encoding (Windows)

Se houver erros de encoding, adicione no início dos scripts:

```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

### 4.2 Garantir .env Local

Crie/atualize `leilao-backend/.env`:

```env
# Supabase
SUPABASE_URL=https://nawbptwbmdgrkbpbwxzl.supabase.co
SUPABASE_KEY=<sua_service_key_aqui>

# Database (para Fly.io usar pooler)
DATABASE_URL=postgresql://postgres.nawbptwbmdgrkbpbwxzl:<senha>@aws-1-sa-east-1.pooler.supabase.com:6543/postgres

# OpenAI (para extração com IA)
OPENAI_API_KEY=<sua_key_aqui>

# ScrapingBee (opcional, para sites bloqueados)
SCRAPINGBEE_API_KEY=<sua_key_aqui>
```

### 4.3 Normalização de Dados

Verificar se `normalize_property_data()` está sendo chamado:

```bash
grep -r "normalize" --include="*.py" app/
```

Se não estiver, adicionar chamada após extração de cada propriedade.

---

## FASE 5: EXECUTAR SCRAPING DE TESTE

### 5.1 Testar 3 Leiloeiros Conhecidos

```bash
# Testar Mega Leilões
python scripts/testar_scraper_individual.py "https://www.megaleiloes.com.br"

# Testar Sodré Santoro
python scripts/testar_scraper_individual.py "https://www.sodresantoro.com.br"

# Testar LF Leilões
python scripts/testar_scraper_individual.py "https://www.lfreiloes.com.br"
```

---

## CRITÉRIOS DE SUCESSO

- [ ] Diagnóstico executa sem erros de encoding
- [ ] Conexão com Supabase OK
- [ ] Identificados leiloeiros com erro vs pendentes
- [ ] Pelo menos 1 scraper testado com sucesso
- [ ] Dados extraídos seguem formato padronizado
- [ ] Title Case aplicado em city e category

---

## INSTRUÇÕES PARA CLAUDE CODE

1. Execute FASE 1 completa primeiro
2. Documente todos os erros encontrados
3. Execute FASE 2 para entender estrutura
4. Execute FASE 3 para testar scrapers
5. Aplique correções da FASE 4 conforme necessário
6. Reporte resultados com:
   - Quantos leiloeiros funcionam
   - Quais erros mais comuns
   - Correções aplicadas
   - Próximos passos recomendados

**MODO AUTÔNOMO:** Execute sem parar para perguntar. Documente descobertas em um arquivo `RELATORIO_DIAGNOSTICO.md`.

---

## REFERÊNCIAS

- `BASE_DE_CONHECIMENTO_ERROS_E_FIXES.md` - Erros conhecidos
- `ARQUITETURA_TECNICA_E_INFRA.md` - Camadas de fallback
- `padrao_scrapers_complexos.md` - Padrão Playwright
