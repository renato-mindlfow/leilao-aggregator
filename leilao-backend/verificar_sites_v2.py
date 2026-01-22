"""
Script de Verificação Automática V2 - PARTE 3.2
Usa o JSON baixado da API para verificar sites
"""

import asyncio
import httpx
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Palavras-chave que indicam imóveis
PROPERTY_KEYWORDS = [
    'imovel', 'imoveis', 'apartamento', 'casa', 'terreno', 'lote',
    'comercial', 'residencial', 'venda', 'leilao', 'leiloes',
    'hectare', 'quartos', 'banheiro', 'garagem', 'm²', 'm2',
    'area', 'endereco', 'cidade', 'estado', 'bairro',
    'lance', 'arrematacao', 'hasta', 'praca'
]

class SiteVerifier:
    """Verificador automático de sites de leilão"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.timeout = httpx.Timeout(25.0, connect=15.0)
        self.results = {
            'online_with_properties': [],
            'online_no_properties': [],
            'offline': [],
            'redirected': [],
            'cloudflare_protected': [],
            'error': []
        }
    
    async def verify_site(self, auctioneer: dict) -> dict:
        """Verifica um único site"""
        auc_id = auctioneer['id']
        name = auctioneer['name']
        website = auctioneer['website']
        
        logger.info(f"{name}: {website}")
        
        result = {
            'id': auc_id,
            'name': name,
            'website': website,
            'status': 'unknown',
            'http_status': None,
            'final_url': website,
            'has_property_keywords': False,
            'property_keyword_count': 0,
            'content_size': 0,
            'error_message': None
        }
        
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=True,
                verify=False
            ) as client:
                
                response = await client.get(website)
                
                result['http_status'] = response.status_code
                result['final_url'] = str(response.url)
                result['content_size'] = len(response.text)
                
                # Verificar redirecionamento
                original_domain = website.split('/')[2].replace('www.', '')
                final_domain = str(response.url).split('/')[2].replace('www.', '')
                
                if original_domain != final_domain:
                    result['status'] = 'redirected'
                    result['error_message'] = f"-> {final_domain}"
                    self.results['redirected'].append(result)
                    return result
                
                # Verificar Cloudflare
                if 'cloudflare' in response.text.lower() or response.status_code == 403:
                    result['status'] = 'cloudflare_protected'
                    result['error_message'] = "Cloudflare"
                    self.results['cloudflare_protected'].append(result)
                    return result
                
                if response.status_code != 200:
                    result['status'] = 'offline'
                    result['error_message'] = f"HTTP {response.status_code}"
                    self.results['offline'].append(result)
                    return result
                
                if len(response.text) < 500:
                    result['status'] = 'offline'
                    result['error_message'] = "Content too small"
                    self.results['offline'].append(result)
                    return result
                
                # Analisar conteúdo
                html_lower = response.text.lower()
                keyword_count = sum(1 for kw in PROPERTY_KEYWORDS if kw in html_lower)
                result['property_keyword_count'] = keyword_count
                result['has_property_keywords'] = keyword_count >= 3
                
                soup = BeautifulSoup(response.text, 'html.parser')
                potential_listings = soup.select('div[class*="card"], div[class*="item"], div[class*="lote"], article, div[class*="property"], div[class*="imovel"]')
                
                if len(potential_listings) >= 3 or keyword_count >= 5:
                    result['status'] = 'online_with_properties'
                    logger.info(f"  -> COM IMOVEIS ({len(potential_listings)} cards, {keyword_count} kw)")
                    self.results['online_with_properties'].append(result)
                else:
                    result['status'] = 'online_no_properties'
                    logger.info(f"  -> SEM imoveis ({len(potential_listings)} cards, {keyword_count} kw)")
                    self.results['online_no_properties'].append(result)
                
                return result
                
        except httpx.TimeoutException:
            result['status'] = 'offline'
            result['error_message'] = "Timeout"
            logger.info(f"  -> TIMEOUT")
            self.results['offline'].append(result)
            return result
            
        except Exception as e:
            result['status'] = 'error'
            result['error_message'] = str(e)[:100]
            logger.info(f"  -> ERROR: {str(e)[:50]}")
            self.results['error'].append(result)
            return result
    
    async def verify_all(self, auctioneers: list) -> dict:
        """Verifica todos os sites em lotes"""
        total = len(auctioneers)
        logger.info(f"\nVerificando {total} sites...")
        logger.info("="*70 + "\n")
        
        batch_size = 15
        for i in range(0, total, batch_size):
            batch = auctioneers[i:i+batch_size]
            current_batch = i//batch_size + 1
            total_batches = (total + batch_size - 1)//batch_size
            
            logger.info(f"LOTE {current_batch}/{total_batches}:")
            
            tasks = [self.verify_site(auc) for auc in batch]
            await asyncio.gather(*tasks)
            
            logger.info("")
            
            if i + batch_size < total:
                await asyncio.sleep(1)
        
        return self.results
    
    def print_summary(self):
        """Imprime resumo"""
        logger.info("="*70)
        logger.info("RESUMO")
        logger.info("="*70)
        
        total = sum(len(v) for v in self.results.values())
        
        logger.info(f"\nOnline COM imoveis: {len(self.results['online_with_properties'])} ({len(self.results['online_with_properties'])*100//total if total else 0}%)")
        logger.info(f"Online SEM imoveis: {len(self.results['online_no_properties'])} ({len(self.results['online_no_properties'])*100//total if total else 0}%)")
        logger.info(f"Cloudflare: {len(self.results['cloudflare_protected'])} ({len(self.results['cloudflare_protected'])*100//total if total else 0}%)")
        logger.info(f"Offline: {len(self.results['offline'])} ({len(self.results['offline'])*100//total if total else 0}%)")
        logger.info(f"Redirecionados: {len(self.results['redirected'])} ({len(self.results['redirected'])*100//total if total else 0}%)")
        logger.info(f"Erros: {len(self.results['error'])} ({len(self.results['error'])*100//total if total else 0}%)")
        
        logger.info("\n" + "="*70)


async def main():
    logger.info("="*70)
    logger.info("VERIFICACAO AUTOMATICA - PARTE 3.2")
    logger.info("="*70)
    
    # Carregar dados do JSON
    with open('leiloeiros_erro.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtrar apenas os com "Nenhum imóvel encontrado"
    auctioneers = [
        {'id': a['id'], 'name': a['name'], 'website': a['website']}
        for a in data['data']
        if a.get('scrape_error') and 'Nenhum imóvel' in a['scrape_error']
    ]
    
    logger.info(f"\nEncontrados {len(auctioneers)} leiloeiros com 'Nenhum imovel encontrado'")
    
    # Verificar sites
    verifier = SiteVerifier()
    results = await verifier.verify_all(auctioneers)
    
    # Imprimir resumo
    verifier.print_summary()
    
    # Salvar resultados
    output_file = f"verificacao_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nResultados salvos em: {output_file}")
    
    logger.info("\n" + "="*70)
    logger.info("CONCLUIDO!")
    logger.info("="*70)


if __name__ == "__main__":
    asyncio.run(main())
