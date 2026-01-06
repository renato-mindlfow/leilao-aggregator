"""
Script para acessar site de leiloeiro e listar títulos dos leilões ativos
"""
import asyncio
import httpx
import logging
from bs4 import BeautifulSoup
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def listar_leiloes_ativos(url: str):
    """Acessa o site e lista os títulos dos leilões ativos"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        logger.info(f"Acessando {url}...")
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Erro ao acessar site: Status {response.status_code}")
                return []
            
            html = response.text
            logger.info(f"HTML recebido: {len(html)} caracteres")
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Tentar encontrar títulos de leilões
            # Estratégias comuns para encontrar títulos de leilões
            titulos = []
            
            # 1. Procurar por elementos com classes comuns de cards/listas de leilões
            selectors = [
                'h2', 'h3', 'h4',  # Títulos
                '.titulo', '.title', '.card-title', '.item-title',
                '.leilao-titulo', '.lote-titulo', '.property-title',
                'a[href*="leilao"]', 'a[href*="lote"]', 'a[href*="imovel"]',
                '.card h2', '.card h3', '.item h2', '.item h3',
                '[class*="titulo"]', '[class*="title"]', '[class*="leilao"]'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 10 and len(text) < 200:  # Filtrar textos muito curtos ou longos
                        # Verificar se parece ser um título de leilão
                        if any(keyword in text.lower() for keyword in ['leilão', 'lote', 'imóvel', 'casa', 'apartamento', 'terreno', 'comercial']):
                            titulos.append(text)
            
            # Remover duplicatas mantendo ordem
            titulos_unicos = []
            seen = set()
            for titulo in titulos:
                if titulo not in seen:
                    titulos_unicos.append(titulo)
                    seen.add(titulo)
            
            # Se não encontrou muitos, tentar estratégia mais ampla
            if len(titulos_unicos) < 3:
                logger.info("Poucos títulos encontrados, tentando estratégia mais ampla...")
                # Procurar todos os links que podem ser leilões
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if text and len(text) > 10 and len(text) < 200:
                        if any(keyword in href.lower() or keyword in text.lower() 
                               for keyword in ['leilao', 'lote', 'imovel', 'property', 'auction']):
                            titulos_unicos.append(text)
                            if len(titulos_unicos) >= 20:  # Limitar para não ficar muito grande
                                break
            
            # Remover duplicatas novamente
            titulos_finais = []
            seen = set()
            for titulo in titulos_unicos:
                if titulo not in seen:
                    titulos_finais.append(titulo)
                    seen.add(titulo)
            
            return titulos_finais
            
    except Exception as e:
        logger.error(f"Erro ao processar site: {e}")
        import traceback
        traceback.print_exc()
        return []

async def main():
    # Site mencionado no diagnóstico
    url = "https://www.turanileiloes.com.br/imoveis"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"LISTANDO LEILÕES ATIVOS")
    logger.info(f"Site: {url}")
    logger.info("="*60)
    
    titulos = await listar_leiloes_ativos(url)
    
    if titulos:
        logger.info(f"\n✅ Encontrados {len(titulos)} leilões ativos:\n")
        for i, titulo in enumerate(titulos, 1):
            logger.info(f"{i}. {titulo}")
    else:
        logger.warning("\n⚠️ Nenhum título de leilão encontrado. O site pode ter estrutura diferente.")
        logger.info("\nTentando acessar a homepage...")
        # Tentar homepage
        titulos_home = await listar_leiloes_ativos("https://www.turanileiloes.com.br")
        if titulos_home:
            logger.info(f"\n✅ Encontrados {len(titulos_home)} itens na homepage:\n")
            for i, titulo in enumerate(titulos_home[:20], 1):  # Limitar a 20
                logger.info(f"{i}. {titulo}")

if __name__ == "__main__":
    asyncio.run(main())

