"""
Script de Diagnóstico Automatizado para Leiloeiros
Testa diferentes camadas de acesso (Fetch → Headers → ScrapingBee → Playwright)
"""

import asyncio
import httpx
import os
from playwright.async_api import async_playwright
from datetime import datetime

# Tentar carregar de .env se disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")

async def diagnosticar(nome, url):
    """Diagnostica um leiloeiro testando diferentes camadas de acesso."""
    print(f"\n{'='*60}")
    print(f"DIAGNOSTICANDO: {nome}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    resultados = {
        'nome': nome,
        'url': url,
        'layer1_fetch': False,
        'layer1_status': None,
        'layer1_size': 0,
        'layer1_cloudflare': False,
        'layer2_headers': False,
        'layer3_scrapingbee': False,
        'layer4_playwright': False,
        'keywords_encontradas': [],
        'links_imoveis': 0,
        'erros': []
    }
    
    # Teste 1: Layer 1 - Fetch direto
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            resultados['layer1_status'] = response.status_code
            resultados['layer1_size'] = len(response.text)
            resultados['layer1_fetch'] = True
            
            print(f"\n[Layer 1 - Fetch Direto]")
            print(f"  Status: {response.status_code}")
            print(f"  Tamanho: {len(response.text)} bytes")
            
            # Verificar Cloudflare
            if 'cloudflare' in response.text.lower() or 'cf-ray' in str(response.headers).lower():
                resultados['layer1_cloudflare'] = True
                print(f"  [AVISO] CLOUDFLARE DETECTADO")
            
            # Verificar se tem conteúdo de imóveis
            keywords = ['imovel', 'imovel', 'leilao', 'leilao', 'lance', 'arrematacao', 'lote', 'item']
            found = [k for k in keywords if k in response.text.lower()]
            resultados['keywords_encontradas'] = found
            print(f"  Keywords encontradas: {found}")
            
    except Exception as e:
        resultados['erros'].append(f"Layer 1: {str(e)}")
        print(f"\n[Layer 1 - Fetch Direto]")
        print(f"  [ERRO] Erro: {e}")
    
    # Teste 2: Layer 2 - Headers avançados
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            })
            resultados['layer2_headers'] = True
            print(f"\n[Layer 2 - Headers Avancados]")
            print(f"  Status: {response.status_code}")
            print(f"  Tamanho: {len(response.text)} bytes")
            
    except Exception as e:
        resultados['erros'].append(f"Layer 2: {str(e)}")
        print(f"\n[Layer 2 - Headers Avancados]")
        print(f"  [ERRO] Erro: {e}")
    
    # Teste 3: Layer 3 - ScrapingBee (se API key disponível)
    if SCRAPINGBEE_API_KEY:
        try:
            params = {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': url,
                'render_js': 'false',
                'premium_proxy': 'true',
                'country_code': 'br',
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    "https://app.scrapingbee.com/api/v1/",
                    params=params
                )
                resultados['layer3_scrapingbee'] = response.status_code == 200
                print(f"\n[Layer 3 - ScrapingBee]")
                print(f"  Status: {response.status_code}")
                print(f"  Tamanho: {len(response.text)} bytes")
                
        except Exception as e:
            resultados['erros'].append(f"Layer 3: {str(e)}")
            print(f"\n[Layer 3 - ScrapingBee]")
            print(f"  [ERRO] Erro: {e}")
    else:
        print(f"\n[Layer 3 - ScrapingBee]")
        print(f"  [SKIP] SCRAPINGBEE_API_KEY nao configurada")
    
    # Teste 4: Layer 4 - Playwright + Stealth
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Injetar scripts de stealth
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            content = await page.content()
            resultados['layer4_playwright'] = True
            print(f"\n[Layer 4 - Playwright + Stealth]")
            print(f"  Carregado com sucesso")
            print(f"  Tamanho: {len(content)} bytes")
            
            # Procurar links de imóveis
            links = await page.query_selector_all('a[href*="imovel"], a[href*="lote"], a[href*="item"], a[href*="leilao"], a[href*="property"]')
            resultados['links_imoveis'] = len(links)
            print(f"  Links de imóveis encontrados: {len(links)}")
            
            await browser.close()
            
    except Exception as e:
        resultados['erros'].append(f"Layer 4: {str(e)}")
        print(f"\n[Layer 4 - Playwright + Stealth]")
        print(f"  [ERRO] Erro: {e}")
    
    print(f"\n{'='*60}\n")
    return resultados


# Lista de leiloeiros para diagnosticar (TOP 15 com erro)
LEILOEIROS = [
    ("Portal Zuk", "https://www.portalzuk.com.br/imoveis"),
    ("Leilão VIP", "https://www.leilaovip.com.br/imoveis"),
    ("Frazão Leilões", "https://www.frazaoleiloes.com.br/imoveis"),
    ("Biasi Leilões", "https://www.biasileiloes.com.br/imoveis"),
    ("Leilões Gold", "https://www.leiloesgold.com.br/imoveis"),
    ("Web Leilões", "https://www.webleiloes.com.br/imoveis"),
    ("Lance no Leilão", "https://www.lancenoleilao.com.br/imoveis"),
    ("JE Leilões", "https://www.jeleiloes.com.br/imoveis"),
    ("Leilão Brasil", "https://www.leilaobrasil.com.br/imoveis"),
    ("Topo Leilões", "https://www.topoleiloes.com.br/imoveis"),
    ("Destak Leilões", "https://www.destakleiloes.com.br/imoveis"),
    ("Alliance Leilões", "https://www.allianceleiloes.com.br/imoveis"),
    ("Legis Leilões", "https://www.legisleiloes.com.br/imoveis"),
    ("Franco Leilões", "https://www.francoleiloes.com.br/imoveis"),
    ("Freitas Leiloeiro", "https://www.freitasleiloeiro.com.br/imoveis"),
]


async def main():
    """Executa diagnóstico de todos os leiloeiros."""
    print("=" * 60)
    print("DIAGNÓSTICO AUTOMATIZADO DE LEILOEIROS")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    resultados_todos = []
    
    for i, (nome, url) in enumerate(LEILOEIROS, 1):
        print(f"\n[{i}/{len(LEILOEIROS)}] Processando {nome}...")
        resultado = await diagnosticar(nome, url)
        resultados_todos.append(resultado)
        
        # Rate limiting: 5 segundos entre requisições
        if i < len(LEILOEIROS):
            await asyncio.sleep(5)
    
    # Salvar resultados em JSON
    import json
    from pathlib import Path
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = logs_dir / f"diagnostico_leiloeiros_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(resultados_todos, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"DIAGNÓSTICO CONCLUÍDO")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Resultados salvos em: {output_file}")
    print("=" * 60)
    
    # Resumo
    print("\nRESUMO:")
    print("-" * 60)
    for resultado in resultados_todos:
        status = "[OK]" if (resultado['layer1_fetch'] or resultado['layer4_playwright']) else "[ERRO]"
        print(f"{status} {resultado['nome']}: Layer1={resultado['layer1_fetch']}, Layer4={resultado['layer4_playwright']}, Links={resultado['links_imoveis']}")


if __name__ == "__main__":
    asyncio.run(main())

