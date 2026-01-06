"""
Script para executar scraping completo dos 5 gigantes
e apresentar tabela final com resultados
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'leilao-backend'))

from TAREFA_SCRAPING_COMPLETO_GIGANTES import GIGANTES, GiganteScraper

# Limites corretos para cada site
LIMITES = {
    "sold": 143,
    "portalzuk": 949,
    "megaleiloes": 600,
    "sodresantoro": 28,
    "lancejudicial": 500,  # Limite temporário até investigar
}

async def executar_scraping_completo():
    """Executa scraping completo de todos os gigantes."""
    
    resultados = []
    
    print("="*80)
    print("SCRAPING COMPLETO DOS 5 GIGANTES")
    print("="*80)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for config in GIGANTES:
        site_id = config["id"]
        site_name = config["name"]
        limite = LIMITES.get(site_id)
        
        print("\n" + "="*80)
        print(f"[{site_id.upper()}] {site_name}")
        print("="*80)
        
        # Ajustar max_items se houver limite definido
        if limite:
            config["max_items"] = limite + 50  # Margem de segurança
            print(f"Limite configurado: {limite} imóveis")
        
        try:
            scraper = GiganteScraper(config)
            
            # Executar scraping
            max_properties = limite + 50 if limite else 1000
            resultado = await scraper.scrape(max_properties=max_properties)
            
            # Coletar estatísticas
            total_extraido = resultado["total_properties"]
            total_disponivel = None
            
            # Tentar obter total disponível da API (para sites com API)
            if config.get("method") == "api" and resultado.get("api_total"):
                total_disponivel = resultado["api_total"]
            elif limite:
                total_disponivel = limite
            else:
                # Tentar estimar baseado no número de páginas processadas
                if resultado["pages_scraped"] > 0:
                    items_per_page = config.get("items_per_page", 20)
                    total_disponivel = resultado["pages_scraped"] * items_per_page
            
            status = "[OK] SUCESSO" if resultado["success"] else "[ERRO] FALHOU"
            if resultado["errors"]:
                status += f" ({len(resultado['errors'])} erros)"
            
            resultados.append({
                "site": site_name,
                "disponivel": total_disponivel if total_disponivel else "?",
                "extraido": total_extraido,
                "status": status,
                "paginas": resultado["pages_scraped"],
                "erros": len(resultado["errors"]),
            })
            
            print(f"\n[RESULTADO] {status}")
            print(f"  Extraídos: {total_extraido}")
            if total_disponivel:
                print(f"  Disponível: {total_disponivel}")
            print(f"  Páginas: {resultado['pages_scraped']}")
            
        except Exception as e:
            print(f"\n[ERRO CRÍTICO] {str(e)}")
            resultados.append({
                "site": site_name,
                "disponivel": "?",
                "extraido": 0,
                "status": f"❌ ERRO: {str(e)[:50]}",
                "paginas": 0,
                "erros": 1,
            })
    
    # Apresentar tabela final
    print("\n\n" + "="*80)
    print("TABELA FINAL - RESULTADOS DO SCRAPING")
    print("="*80)
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Cabeçalho
    print(f"{'Site':<20} | {'Disponível':<12} | {'Extraídos':<12} | {'Status':<30}")
    print("-" * 80)
    
    # Linhas
    for r in resultados:
        disponivel = str(r["disponivel"]) if r["disponivel"] != "?" else "?"
        extraido = str(r["extraido"])
        status = r["status"]
        
        print(f"{r['site']:<20} | {disponivel:<12} | {extraido:<12} | {status:<30}")
    
    print("\n" + "="*80)
    
    # Resumo
    total_extraido = sum(r["extraido"] for r in resultados)
    total_erros = sum(r["erros"] for r in resultados)
    
    print(f"\nRESUMO:")
    print(f"  Total de imóveis extraídos: {total_extraido}")
    print(f"  Total de erros: {total_erros}")
    print(f"  Sites processados: {len(resultados)}")
    
    return resultados

if __name__ == "__main__":
    resultados = asyncio.run(executar_scraping_completo())
