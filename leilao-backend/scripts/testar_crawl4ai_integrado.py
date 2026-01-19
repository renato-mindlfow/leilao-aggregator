"""
Testa o módulo Crawl4AI integrado ao projeto principal.
Deve reproduzir os 95% de sucesso do leilohub-scraper-final.

Execução:
    cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
    python scripts\testar_crawl4ai_integrado.py
"""
import os
import sys
import io

# Configurar encoding UTF-8 para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("TESTE: CRAWL4AI INTEGRADO AO PROJETO PRINCIPAL")
print("=" * 70)

# Verificar dependências
print("\n[1] Verificando dependências...")
try:
    from app.services.crawl4ai_scraper import Crawl4AIScraper, scrape_with_crawl4ai, CRAWL4AI_AVAILABLE
    print("  ✓ crawl4ai_scraper importado")
    
    if not CRAWL4AI_AVAILABLE:
        print("  ✗ Crawl4AI não está disponível. Verifique a instalação.")
        print("\nPara instalar:")
        print("  pip install crawl4ai")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)
    else:
        print("  ✓ Crawl4AI disponível")
    
except ImportError as e:
    print(f"  ✗ Erro ao importar: {e}")
    sys.exit(1)

# Verificar OPENAI_API_KEY
if not os.getenv("OPENAI_API_KEY"):
    print("\n  ✗ OPENAI_API_KEY não configurada no .env")
    sys.exit(1)
else:
    print("  ✓ OPENAI_API_KEY configurada")

# Testar em 5 leiloeiros
LEILOEIROS_TESTE = [
    {"nome": "Mega Leilões", "url": "https://www.megaleiloes.com.br", "id": "megaleiloes"},
    {"nome": "Sold Leilões", "url": "https://www.sold.com.br", "id": "sold"},
    {"nome": "Flex Leilões", "url": "https://www.flexleiloes.com.br", "id": "flexleiloes"},
    {"nome": "Viva Leilões", "url": "https://www.vivaleiloes.com.br", "id": "vivaleiloes"},
    {"nome": "Lance Judicial", "url": "https://www.lancejudicial.com.br", "id": "lancejudicial"},
]

print(f"\n[2] Testando {len(LEILOEIROS_TESTE)} leiloeiros...")
print("    (Isso pode levar alguns minutos...)\n")

resultados = []
for leiloeiro in LEILOEIROS_TESTE:
    print(f"  [{leiloeiro['nome']}] {leiloeiro['url']}")
    
    try:
        imoveis = scrape_with_crawl4ai(
            url=leiloeiro['url'],
            auctioneer_id=leiloeiro['id'],
            auctioneer_name=leiloeiro['nome']
        )
        
        if imoveis:
            print(f"    ✓ {len(imoveis)} imóveis extraídos")
            # Mostrar exemplo
            if imoveis[0].get('title'):
                print(f"    Exemplo: {imoveis[0]['title'][:60]}...")
            resultados.append({"nome": leiloeiro['nome'], "sucesso": True, "qtd": len(imoveis)})
        else:
            print(f"    ✗ Nenhum imóvel extraído")
            resultados.append({"nome": leiloeiro['nome'], "sucesso": False, "qtd": 0})
            
    except Exception as e:
        print(f"    ✗ Erro: {e}")
        resultados.append({"nome": leiloeiro['nome'], "sucesso": False, "qtd": 0, "erro": str(e)})

# Resumo
print("\n" + "=" * 70)
print("RESUMO")
print("=" * 70)

sucessos = sum(1 for r in resultados if r['sucesso'])
total_imoveis = sum(r['qtd'] for r in resultados)

print(f"\nTaxa de sucesso: {sucessos}/{len(LEILOEIROS_TESTE)} ({sucessos/len(LEILOEIROS_TESTE)*100:.0f}%)")
print(f"Total de imóveis: {total_imoveis}")

for r in resultados:
    status = "✓" if r['sucesso'] else "✗"
    qtd_str = f"{r['qtd']} imóveis" if r['sucesso'] else "0 imóveis"
    print(f"  {status} {r['nome']}: {qtd_str}")
    if 'erro' in r:
        print(f"      Erro: {r['erro'][:80]}...")

print()
if sucessos >= 4:
    print("✓ INTEGRAÇÃO BEM SUCEDIDA! (>= 80% sucesso)")
elif sucessos >= 3:
    print("⚠ INTEGRAÇÃO PARCIAL (>= 60% sucesso)")
else:
    print("✗ VERIFICAR PROBLEMAS (< 60% sucesso)")
