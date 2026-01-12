import asyncio
import httpx
import sys
from datetime import datetime

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

LEILOEIROS_ERRO = [
    ("Portal Zuk", "https://www.portalzuk.com.br/leilao-de-imoveis"),
    ("Leilão VIP", "https://www.leilaovip.com.br"),
    ("Frazão Leilões", "https://www.frazaoleiloes.com.br"),
    ("Biasi Leilões", "https://www.biasileiloes.com.br"),
    ("Leilões Gold", "https://www.leiloesgold.com.br"),
    ("Web Leilões", "https://www.webleiloes.com.br"),
    ("Lance no Leilão", "https://www.lancenoleilao.com.br"),
    ("JE Leilões", "https://www.jeleiloes.com.br"),
    ("Leilão Brasil", "https://www.leilaobrasil.com.br"),
    ("Topo Leilões", "https://www.topoleiloes.com.br"),
]

async def diagnosticar(nome, url):
    resultado = {"nome": nome, "url": url, "status": "desconhecido", "detalhes": []}
    
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            resultado["status_code"] = response.status_code
            resultado["tamanho"] = len(response.text)
            
            # Verificar Cloudflare
            if "cloudflare" in response.text.lower() or "cf-ray" in str(response.headers).lower():
                resultado["cloudflare"] = True
                resultado["detalhes"].append("⚠️ Cloudflare detectado - precisa Playwright")
            else:
                resultado["cloudflare"] = False
            
            # Verificar conteúdo
            keywords = ["imóvel", "imovel", "leilão", "leilao", "lance", "lote"]
            found = [k for k in keywords if k in response.text.lower()]
            resultado["keywords"] = found
            
            if response.status_code == 200 and len(found) > 0:
                resultado["status"] = "✅ Online e funcional"
            elif response.status_code == 200:
                resultado["status"] = "⚠️ Online mas sem conteúdo de imóveis"
            else:
                resultado["status"] = f"❌ HTTP {response.status_code}"
                
    except Exception as e:
        resultado["status"] = f"❌ Erro: {str(e)[:50]}"
    
    return resultado

async def main():
    print(f"\n{'='*60}")
    print(f"DIAGNÓSTICO DE LEILOEIROS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")
    
    resultados = []
    for nome, url in LEILOEIROS_ERRO:
        print(f"Verificando: {nome}...")
        resultado = await diagnosticar(nome, url)
        resultados.append(resultado)
        
        print(f"  {resultado['status']}")
        if resultado.get('cloudflare'):
            print(f"  ⚠️ Cloudflare detectado")
        print()
        
        await asyncio.sleep(2)
    
    # Resumo
    print(f"\n{'='*60}")
    print("RESUMO")
    print(f"{'='*60}")
    
    online = [r for r in resultados if "✅" in r["status"]]
    cloudflare = [r for r in resultados if r.get("cloudflare")]
    offline = [r for r in resultados if "❌" in r["status"]]
    
    print(f"✅ Online e funcional: {len(online)}")
    print(f"⚠️ Com Cloudflare: {len(cloudflare)}")
    print(f"❌ Offline/Erro: {len(offline)}")
    
    return resultados

if __name__ == "__main__":
    asyncio.run(main())
