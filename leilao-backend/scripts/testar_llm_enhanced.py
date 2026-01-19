#!/usr/bin/env python3
"""
Teste do LLMEnhancedScraper
Alternativa ao Crawl4AI que funciona no Windows sem dependência lxml
"""

import sys
import os
import io
import asyncio
from datetime import datetime

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Verificar OpenAI API Key
if not os.getenv('OPENAI_API_KEY'):
    print("❌ OPENAI_API_KEY não configurada!")
    print("   Configure no arquivo .env")
    sys.exit(1)

try:
    from app.services.llm_enhanced_scraper import LLMEnhancedScraper, LLM_ENHANCED_AVAILABLE
    
    if not LLM_ENHANCED_AVAILABLE:
        print("❌ Playwright não está instalado!")
        print("\nPara instalar:")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Erro ao importar LLMEnhancedScraper: {e}")
    print("\nVerifique se as dependências estão instaladas:")
    print("  pip install playwright beautifulsoup4 openai")
    print("  playwright install chromium")
    sys.exit(1)

# Leiloeiros para teste (URLs mais leves e específicas)
LEILOEIROS_TESTE = [
    {"url": "https://www.portalzukerman.com.br/busca?categoriaId=1", "id": "portalzuk", "nome": "Portal Zukerman"},
    {"url": "https://www.sold.com.br/leiloes?categoria=imoveis", "id": "sold", "nome": "Sold Leilões"},
    {"url": "https://www.flexleiloes.com.br/auctions?property_type=imovel", "id": "flexleiloes", "nome": "Flex Leilões"},
    {"url": "https://www.vivaleiloes.com.br/busca?tipoBem=1", "id": "vivaleiloes", "nome": "Viva Leilões"},
    {"url": "https://www.lancejudicial.com.br/busca?tipo=imovel", "id": "lancejudicial", "nome": "Lance Judicial"},
]


async def testar_leiloeiro(leiloeiro: dict) -> dict:
    """Testa um leiloeiro específico."""
    url = leiloeiro["url"]
    aid = leiloeiro["id"]
    nome = leiloeiro["nome"]
    
    print(f"\n{'='*70}")
    print(f"🏠 Testando: {nome}")
    print(f"   URL: {url}")
    print('='*70)
    
    inicio = datetime.now()
    scraper = None
    
    try:
        scraper = LLMEnhancedScraper(headless=True)
        properties = await scraper.scrape_url(url, aid, nome)
        tempo = (datetime.now() - inicio).total_seconds()
        
        if properties:
            print(f"\n✅ SUCESSO: {len(properties)} imóveis em {tempo:.1f}s")
            
            # Mostrar amostra
            for i, p in enumerate(properties[:3]):
                print(f"\n   Imóvel {i+1}:")
                titulo = p.get('title', 'N/A')
                if len(titulo) > 50:
                    titulo = titulo[:50] + '...'
                print(f"   - Título: {titulo}")
                print(f"   - Cidade: {p.get('city', 'N/A')}, {p.get('state', 'N/A')}")
                print(f"   - Categoria: {p.get('category', 'N/A')}")
                valor = p.get('first_auction_value') or p.get('evaluation_value')
                if valor:
                    print(f"   - Valor: R$ {valor:,.2f}")
                else:
                    print(f"   - Valor: N/A")
                
            return {"status": "sucesso", "count": len(properties), "tempo": tempo}
        else:
            print(f"\n⚠️ FALHA: Nenhum imóvel extraído ({tempo:.1f}s)")
            return {"status": "falha", "count": 0, "tempo": tempo}
            
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        erro_msg = str(e)
        if len(erro_msg) > 100:
            erro_msg = erro_msg[:100] + '...'
        print(f"\n❌ ERRO: {erro_msg} ({tempo:.1f}s)")
        return {"status": "erro", "error": str(e), "tempo": tempo}


async def main():
    print("="*70)
    print("TESTE: LLM ENHANCED SCRAPER (Alternativa ao Crawl4AI)")
    print("="*70)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Leiloeiros: {len(LEILOEIROS_TESTE)}")
    print("\n⏳ Este teste pode levar alguns minutos...")
    print("   (Cada leiloeiro leva ~30-60s devido ao Playwright + LLM)")
    
    resultados = []
    
    for leiloeiro in LEILOEIROS_TESTE:
        resultado = await testar_leiloeiro(leiloeiro)
        resultado["leiloeiro"] = leiloeiro["id"]
        resultado["nome"] = leiloeiro["nome"]
        resultados.append(resultado)
    
    # Resumo final
    print("\n" + "="*70)
    print("RESUMO FINAL")
    print("="*70)
    
    sucessos = sum(1 for r in resultados if r["status"] == "sucesso")
    falhas = sum(1 for r in resultados if r["status"] == "falha")
    erros = sum(1 for r in resultados if r["status"] == "erro")
    total_imoveis = sum(r.get("count", 0) for r in resultados)
    tempo_total = sum(r.get("tempo", 0) for r in resultados)
    
    print(f"\n📊 Resultados:")
    print(f"   ✅ Sucesso: {sucessos}/{len(LEILOEIROS_TESTE)} ({100*sucessos/len(LEILOEIROS_TESTE):.1f}%)")
    print(f"   ⚠️  Falha: {falhas}")
    print(f"   ❌ Erro: {erros}")
    print(f"   🏠 Total imóveis: {total_imoveis}")
    print(f"   ⏱️  Tempo total: {tempo_total:.1f}s")
    
    print("\n📋 Detalhes por leiloeiro:")
    for r in resultados:
        status_icon = "✅" if r["status"] == "sucesso" else "⚠️" if r["status"] == "falha" else "❌"
        print(f"   {status_icon} {r['nome']}: {r.get('count', 0)} imóveis ({r.get('tempo', 0):.1f}s)")
        if r["status"] == "erro" and "error" in r:
            erro = r["error"]
            if len(erro) > 60:
                erro = erro[:60] + "..."
            print(f"       Erro: {erro}")
    
    # Critério de sucesso
    taxa = 100 * sucessos / len(LEILOEIROS_TESTE)
    print("\n" + "="*70)
    if taxa >= 60:
        print(f"🎉 SUCESSO! Taxa de {taxa:.1f}% >= 60%")
        print("   O LLMEnhancedScraper está funcionando!")
        print("   Pode ser usado como fallback universal no ScraperManager.")
    else:
        print(f"⚠️  Taxa de {taxa:.1f}% < 60%")
        print("   Pode ser necessário ajustar prompts ou verificar configuração.")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
