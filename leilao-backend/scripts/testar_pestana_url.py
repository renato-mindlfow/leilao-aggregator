"""
Script para testar acesso à URL específica de imóveis do Pestana
"""
import asyncio
import httpx
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def testar_url_pestana():
    """Testa acesso à URL de imóveis do Pestana"""
    
    url = "https://www.pestanaleiloes.com.br/procurar-bens?tipoBem=462"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.pestanaleiloes.com.br/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTANDO ACESSO À URL DO PESTANA")
    logger.info(f"URL: {url}")
    logger.info("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Content Length: {len(response.text)} caracteres")
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Verificar se há mensagem de navegador incompatível
            page_text = soup.get_text().lower()
            
            if 'navegador incompatível' in page_text or 'browser' in page_text and 'incompatível' in page_text:
                logger.error("\n❌ RESULTADO: Mensagem de 'Navegador Incompatível' detectada")
                logger.info("\nDetalhes:")
                # Procurar pela mensagem exata
                incompativel_div = soup.find('div', id='compatibility-container')
                if incompativel_div:
                    logger.info(f"  - Container de incompatibilidade encontrado")
                    logger.info(f"  - Mensagem: {incompativel_div.get_text(strip=True)[:200]}")
                
                # Verificar se há div com classe notification-page
                notification = soup.find('div', class_=lambda x: x and 'notification' in str(x).lower())
                if notification:
                    logger.info(f"  - Página de notificação encontrada")
                    logger.info(f"  - Título: {notification.find('p', class_=lambda x: x and 'title' in str(x).lower())}")
                
                return {
                    'status': 'bloqueado',
                    'mensagem': 'Navegador Incompatível',
                    'conteudo_visivel': False
                }
            
            # Verificar se há conteúdo de imóveis
            # Procurar por elementos que indicam lista de imóveis
            indicadores_imoveis = [
                soup.find_all('a', href=lambda x: x and '/agenda-de-leiloes/' in str(x)),
                soup.find_all('div', class_=lambda x: x and any(kw in str(x).lower() for kw in ['card', 'item', 'lote', 'imovel'])),
                soup.find_all('article'),
                soup.find_all('section'),
            ]
            
            total_elementos = sum(len(items) for items in indicadores_imoveis if items)
            
            if total_elementos > 0:
                logger.info(f"\n✅ RESULTADO: Possível conteúdo de imóveis detectado")
                logger.info(f"  - Elementos encontrados: {total_elementos}")
                
                # Contar links de leilões
                links_leiloes = soup.find_all('a', href=lambda x: x and '/agenda-de-leiloes/' in str(x))
                logger.info(f"  - Links de leilões: {len(links_leiloes)}")
                
                if links_leiloes:
                    logger.info(f"  - Primeiro link: {links_leiloes[0].get('href', 'N/A')[:80]}")
                
                return {
                    'status': 'sucesso',
                    'mensagem': 'Conteúdo de imóveis detectado',
                    'conteudo_visivel': True,
                    'elementos_encontrados': total_elementos,
                    'links_leiloes': len(links_leiloes)
                }
            else:
                # Verificar se é apenas HTML vazio (SPA)
                app_div = soup.find('div', id='app')
                if app_div and not app_div.get_text(strip=True):
                    logger.warning("\n⚠️ RESULTADO: HTML vazio - SPA requer JavaScript")
                    logger.info("  - Div #app encontrada mas vazia")
                    logger.info("  - Conteúdo precisa ser renderizado via JavaScript")
                    
                    return {
                        'status': 'spa_vazio',
                        'mensagem': 'HTML vazio - requer JavaScript',
                        'conteudo_visivel': False,
                        'requer_javascript': True
                    }
                else:
                    logger.warning("\n⚠️ RESULTADO: Conteúdo não identificado")
                    logger.info("  - Não foi possível identificar se há imóveis ou bloqueio")
                    
                    # Salvar HTML para análise
                    with open('leilao-backend/scripts/pestana_test.html', 'w', encoding='utf-8') as f:
                        f.write(html)
                    logger.info("  - HTML salvo em pestana_test.html para análise manual")
                    
                    return {
                        'status': 'indeterminado',
                        'mensagem': 'Conteúdo não identificado',
                        'conteudo_visivel': False
                    }
                    
    except Exception as e:
        logger.error(f"\n❌ ERRO ao acessar URL: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'erro',
            'mensagem': str(e),
            'conteudo_visivel': False
        }

async def main():
    resultado = await testar_url_pestana()
    
    print("\n" + "="*60)
    print("RESUMO DO TESTE")
    print("="*60)
    print(f"Status: {resultado.get('status')}")
    print(f"Mensagem: {resultado.get('mensagem')}")
    print(f"Conteúdo visível: {resultado.get('conteudo_visivel', False)}")
    
    if resultado.get('status') == 'bloqueado':
        print("\n[X] CONCLUSAO: Site bloqueou acesso - aparece 'Navegador Incompativel'")
        print("   E necessario usar Selenium/Playwright para bypass")
    elif resultado.get('status') == 'spa_vazio':
        print("\n[!] CONCLUSAO: HTML vazio - site e SPA que requer JavaScript")
        print("   E necessario usar Selenium/Playwright para renderizar conteudo")
    elif resultado.get('status') == 'sucesso':
        print("\n[OK] CONCLUSAO: Conteudo de imoveis detectado na pagina")
        print(f"   {resultado.get('links_leiloes', 0)} links de leiloes encontrados")
    else:
        print("\n[!] CONCLUSAO: Nao foi possivel determinar o status")
        print("   Verifique o arquivo pestana_test.html para analise manual")

if __name__ == "__main__":
    asyncio.run(main())

