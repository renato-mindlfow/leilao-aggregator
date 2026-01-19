#!/usr/bin/env python3
"""
Teste do LLMEnhancedScraper após melhorias do diagnóstico.
Valida se as correções resolveram os problemas identificados.
"""

import sys
import os
import asyncio
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.llm_enhanced_scraper import LLMEnhancedScraper

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Sites que falharam no diagnóstico
SITES_TESTE = [
    {
        "id": "megaleiloes",
        "name": "Mega Leilões",
        "url": "https://www.megaleiloes.com.br/imoveis",
        "problema_anterior": "Conteúdo visível mas LLM não extraiu"
    },
    {
        "id": "portalzuk",
        "name": "Portal Zuk",
        "url": "https://www.portalzuk.com.br/leilao-de-imoveis",
        "problema_anterior": "Imagens ofuscadas + popup"
    },
    {
        "id": "sold",
        "name": "Sold",
        "url": "https://www.sold.com.br/",
        "problema_anterior": "Conteúdo perfeito mas LLM não extraiu"
    },
]


async def testar_site(site: dict) -> dict:
    """Testa scraper melhorado em um site."""
    print(f"\n{'='*70}")
    print(f"🔧 TESTANDO: {site['name']}")
    print(f"   URL: {site['url']}")
    print(f"   Problema Anterior: {site['problema_anterior']}")
    print('='*70)
    
    resultado = {
        "site": site["name"],
        "url": site["url"],
        "sucesso": False,
        "imoveis_encontrados": 0,
        "tempo_execucao": 0,
        "erro": None,
    }
    
    try:
        inicio = datetime.now()
        
        scraper = LLMEnhancedScraper(headless=True)
        
        print("\n[1/3] Iniciando extração com LLMEnhancedScraper melhorado...")
        properties = await scraper.scrape_url(
            url=site["url"],
            auctioneer_id=site["id"],
            auctioneer_name=site["name"]
        )
        
        tempo = (datetime.now() - inicio).total_seconds()
        
        print(f"[2/3] Extração concluída em {tempo:.1f}s")
        print(f"[3/3] Imóveis encontrados: {len(properties)}")
        
        resultado["sucesso"] = len(properties) > 0
        resultado["imoveis_encontrados"] = len(properties)
        resultado["tempo_execucao"] = tempo
        
        # Mostrar primeiros 3 imóveis como amostra
        if properties:
            print("\n📋 AMOSTRA DOS IMÓVEIS EXTRAÍDOS:")
            for i, prop in enumerate(properties[:3], 1):
                print(f"\n   Imóvel {i}:")
                print(f"   - Título: {prop.get('title', 'N/A')}")
                print(f"   - Endereço: {prop.get('address', 'N/A')}")
                print(f"   - Cidade/Estado: {prop.get('city', 'N/A')}/{prop.get('state', 'N/A')}")
                print(f"   - Tipo: {prop.get('category', 'N/A')}")
                print(f"   - Valor: R$ {prop.get('first_auction_value', 0):,.2f}")
                print(f"   - Área: {prop.get('area_total', 'N/A')} m²")
            
            if len(properties) > 3:
                print(f"\n   ... e mais {len(properties) - 3} imóveis")
                
            # Salvar resultado completo em JSON
            output_dir = "logs/scraper_audit/testes"
            os.makedirs(output_dir, exist_ok=True)
            output_file = f"{output_dir}/{site['id']}_resultado.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(properties, f, indent=2, ensure_ascii=False)
            
            print(f"\n   ✅ Resultado completo salvo em: {output_file}")
        else:
            print("\n   ❌ NENHUM IMÓVEL ENCONTRADO")
            print("   Possíveis causas:")
            print("   - Página não carregou corretamente")
            print("   - LLM não identificou padrão de imóveis")
            print("   - Site requer navegação específica")
        
    except Exception as e:
        print(f"\n   ❌ ERRO: {str(e)}")
        resultado["erro"] = str(e)
        import traceback
        traceback.print_exc()
    
    return resultado


async def main():
    print("="*70)
    print("🔬 TESTE DO LLMEnhancedScraper MELHORADO")
    print("="*70)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sites a testar: {len(SITES_TESTE)}")
    print("\nMelhorias aplicadas:")
    print("✓ Limite de texto aumentado de 15k para 80k chars")
    print("✓ Scroll mais agressivo (15000px vs 5000px)")
    print("✓ Fechamento automático de popups")
    print("✓ Prompt do LLM melhorado com exemplos")
    print("✓ Max tokens aumentado de 4k para 8k")
    
    resultados = []
    
    for site in SITES_TESTE:
        resultado = await testar_site(site)
        resultados.append(resultado)
        await asyncio.sleep(2)  # Pausa entre sites
    
    # Resumo final
    print("\n" + "="*70)
    print("📊 RESUMO DOS TESTES")
    print("="*70)
    
    total_sucesso = sum(1 for r in resultados if r["sucesso"])
    total_imoveis = sum(r["imoveis_encontrados"] for r in resultados)
    
    for r in resultados:
        status = "✅ SUCESSO" if r["sucesso"] else "❌ FALHA"
        print(f"\n{status} - {r['site']}")
        print(f"   Imóveis: {r['imoveis_encontrados']}")
        print(f"   Tempo: {r['tempo_execucao']:.1f}s")
        if r.get("erro"):
            print(f"   Erro: {r['erro'][:100]}")
    
    print("\n" + "="*70)
    print(f"Taxa de Sucesso: {total_sucesso}/{len(SITES_TESTE)} sites ({100*total_sucesso/len(SITES_TESTE):.0f}%)")
    print(f"Total de Imóveis: {total_imoveis}")
    print("="*70)
    
    # Salvar resumo
    resumo_path = "logs/scraper_audit/testes/RESUMO_TESTES.json"
    with open(resumo_path, 'w', encoding='utf-8') as f:
        json.dump({
            "data": datetime.now().isoformat(),
            "melhorias_aplicadas": [
                "Limite de texto: 15k → 80k chars",
                "Scroll: 5000px → 15000px",
                "Popup closing adicionado",
                "Prompt melhorado",
                "Max tokens: 4k → 8k"
            ],
            "resultados": resultados,
            "resumo": {
                "sites_testados": len(SITES_TESTE),
                "sites_sucesso": total_sucesso,
                "taxa_sucesso": f"{100*total_sucesso/len(SITES_TESTE):.0f}%",
                "total_imoveis": total_imoveis
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nResumo salvo em: {resumo_path}")


if __name__ == "__main__":
    asyncio.run(main())
