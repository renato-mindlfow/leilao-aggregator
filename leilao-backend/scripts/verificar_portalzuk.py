"""
Script para verificar se o site Portal Zukerman carrega ou tem bloqueio
"""
import asyncio
import httpx
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verificar_site():
    """Verifica se o site Portal Zukerman carrega"""
    
    url = "https://www.portalzuk.com.br/imoveis"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com/',
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"VERIFICANDO SITE PORTAL ZUKERMAN")
    logger.info(f"URL: {url}")
    logger.info("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Content Length: {len(response.text)} caracteres")
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Verificar se há bloqueio
            page_text = soup.get_text().lower()
            
            bloqueios = [
                'navegador incompatível',
                'browser incompatible',
                'acesso negado',
                'access denied',
                'cloudflare',
                'captcha',
            ]
            
            bloqueio_encontrado = False
            for bloqueio in bloqueios:
                if bloqueio in page_text:
                    logger.error(f"❌ BLOQUEIO DETECTADO: '{bloqueio}'")
                    bloqueio_encontrado = True
                    break
            
            if not bloqueio_encontrado:
                logger.info("✅ Nenhum bloqueio detectado")
            
            # Verificar se há conteúdo de imóveis
            indicadores = [
                soup.find_all('a', href=lambda x: x and ('imovel' in str(x).lower() or 'leilao' in str(x).lower())),
                soup.find_all(['div', 'article'], class_=lambda x: x and any(kw in str(x).lower() for kw in ['card', 'item', 'property', 'imovel'])),
            ]
            
            total_elementos = sum(len(items) for items in indicadores if items)
            
            if total_elementos > 0:
                logger.info(f"✅ Conteúdo de imóveis detectado: {total_elementos} elementos")
                
                # Verificar estrutura
                links_imoveis = soup.find_all('a', href=lambda x: x and 'imovel' in str(x).lower())
                logger.info(f"   Links de imóveis encontrados: {len(links_imoveis)}")
                
                if links_imoveis:
                    logger.info(f"   Primeiro link: {links_imoveis[0].get('href', 'N/A')[:80]}")
                
                return {
                    'status': 'sucesso',
                    'bloqueio': bloqueio_encontrado,
                    'elementos_encontrados': total_elementos,
                    'links_imoveis': len(links_imoveis),
                    'html': html[:5000]  # Primeiros 5000 caracteres para análise
                }
            else:
                # Verificar se é SPA
                app_div = soup.find('div', id='app')
                if app_div:
                    logger.warning("⚠️ SPA detectado - conteúdo carregado via JavaScript")
                    return {
                        'status': 'spa',
                        'bloqueio': bloqueio_encontrado,
                        'html': html[:5000]
                    }
                else:
                    logger.warning("⚠️ Conteúdo não identificado")
                    return {
                        'status': 'indeterminado',
                        'bloqueio': bloqueio_encontrado,
                        'html': html[:5000]
                    }
                    
    except Exception as e:
        logger.error(f"❌ ERRO ao acessar site: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'erro',
            'erro': str(e)
        }

if __name__ == "__main__":
    resultado = asyncio.run(verificar_site())
    
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    print(f"Status: {resultado.get('status')}")
    print(f"Bloqueio: {resultado.get('bloqueio', False)}")
    if 'elementos_encontrados' in resultado:
        print(f"Elementos encontrados: {resultado.get('elementos_encontrados')}")

