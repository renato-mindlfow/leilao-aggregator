import asyncio
import httpx
import sys
from datetime import datetime

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

NOVOS_LEILOEIROS = [
    ("GP Leilões", "https://www.gpleiloes.com.br", 1036),
    ("ARG Leilões", "https://www.argleiloes.com.br", 599),
    ("Realiza Leilões", "https://www.realizaleiloes.com.br", 598),
    ("Comprei", "https://www.comprei.com.br", 597),
    ("Baldissera", "https://www.baldisseraleiloeiros.com.br", 572),
    ("Mega Leilões", "https://www.megaleiloes.com.br", 500),
    ("Sodré Santoro", "https://www.sodresantoro.com.br", 450),
    ("Superbid", "https://www.superbid.net", 400),
]

async def verificar_site(nome, url, imoveis_esperados):
    resultado = {
        "nome": nome, 
        "url": url, 
        "imoveis_esperados": imoveis_esperados,
        "status": "desconhecido"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            resultado["status_code"] = response.status_code
            resultado["tamanho"] = len(response.text)
            
            # Detectar tipo de site
            if "cloudflare" in response.text.lower():
                resultado["tipo"] = "Cloudflare - precisa Playwright"
            elif "react" in response.text.lower() or "angular" in response.text.lower():
                resultado["tipo"] = "SPA - precisa Playwright"
            else:
                resultado["tipo"] = "HTML estático - scraper genérico OK"
            
            # Procurar página de imóveis
            urls_imoveis = []
            for path in ["/imoveis", "/leiloes", "/leilao-de-imoveis", "/catalogo"]:
                try:
                    resp = await client.get(url.rstrip("/") + path, headers={
                        "User-Agent": "Mozilla/5.0"
                    })
                    if resp.status_code == 200 and len(resp.text) > 1000:
                        urls_imoveis.append(path)
                except:
                    pass
            
            resultado["paginas_imoveis"] = urls_imoveis
            resultado["status"] = "✅ Acessível" if response.status_code == 200 else f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        resultado["status"] = f"❌ Erro: {str(e)[:50]}"
    
    return resultado

async def main():
    print(f"\n{'='*60}")
    print(f"PESQUISA DE NOVOS LEILOEIROS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")
    
    resultados = []
    for nome, url, imoveis in NOVOS_LEILOEIROS:
        print(f"Verificando: {nome} (~{imoveis} imóveis)...")
        resultado = await verificar_site(nome, url, imoveis)
        resultados.append(resultado)
        
        print(f"  {resultado['status']}")
        print(f"  Tipo: {resultado.get('tipo', 'N/A')}")
        if resultado.get('paginas_imoveis'):
            print(f"  Páginas: {resultado['paginas_imoveis']}")
        print()
        
        await asyncio.sleep(3)
    
    # Resumo e recomendações
    print(f"\n{'='*60}")
    print("RECOMENDAÇÕES DE IMPLEMENTAÇÃO")
    print(f"{'='*60}\n")
    
    for r in resultados:
        if "✅" in r["status"]:
            print(f"📌 {r['nome']} ({r['imoveis_esperados']} imóveis)")
            print(f"   URL: {r['url']}")
            print(f"   Tipo: {r.get('tipo', 'N/A')}")
            print(f"   Ação: {'Criar scraper Playwright' if 'Playwright' in r.get('tipo', '') else 'Usar scraper genérico'}")
            print()
    
    return resultados

if __name__ == "__main__":
    asyncio.run(main())

