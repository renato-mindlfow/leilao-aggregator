"""
Script de Verificação Automática - PARTE 3.2
Verifica os 122 sites com erro "Nenhum imóvel encontrado"
"""

import asyncio
import httpx
import psycopg
from psycopg.rows import dict_row
import os
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeiloHub2025Pass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres")

# Palavras-chave que indicam imóveis
PROPERTY_KEYWORDS = [
    'imovel', 'imoveis', 'apartamento', 'casa', 'terreno', 'lote',
    'comercial', 'residencial', 'venda', 'leilao', 'leilões',
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
        self.timeout = httpx.Timeout(30.0, connect=15.0)
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
        
        logger.info(f"Verificando {name} ({auc_id}): {website}")
        
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
                
                # Tentar acessar o site
                response = await client.get(website)
                
                result['http_status'] = response.status_code
                result['final_url'] = str(response.url)
                result['content_size'] = len(response.text)
                
                # Verificar se foi redirecionado para outro domínio
                original_domain = website.split('/')[2].replace('www.', '')
                final_domain = str(response.url).split('/')[2].replace('www.', '')
                
                if original_domain != final_domain:
                    result['status'] = 'redirected'
                    result['error_message'] = f"Redirecionado para {final_domain}"
                    logger.warning(f"  REDIRECIONADO: {original_domain} -> {final_domain}")
                    self.results['redirected'].append(result)
                    return result
                
                # Verificar Cloudflare
                if 'cloudflare' in response.text.lower() or response.status_code == 403:
                    result['status'] = 'cloudflare_protected'
                    result['error_message'] = "Protegido por Cloudflare"
                    logger.warning(f"  CLOUDFLARE DETECTADO")
                    self.results['cloudflare_protected'].append(result)
                    return result
                
                # Verificar se retornou HTML válido
                if response.status_code != 200:
                    result['status'] = 'offline'
                    result['error_message'] = f"HTTP {response.status_code}"
                    logger.error(f"  OFFLINE: HTTP {response.status_code}")
                    self.results['offline'].append(result)
                    return result
                
                if len(response.text) < 500:
                    result['status'] = 'offline'
                    result['error_message'] = "Conteúdo muito pequeno"
                    logger.error(f"  OFFLINE: Conteúdo pequeno ({len(response.text)} bytes)")
                    self.results['offline'].append(result)
                    return result
                
                # Analisar conteúdo HTML
                html_lower = response.text.lower()
                
                # Contar palavras-chave de imóveis
                keyword_count = sum(1 for kw in PROPERTY_KEYWORDS if kw in html_lower)
                result['property_keyword_count'] = keyword_count
                result['has_property_keywords'] = keyword_count >= 3
                
                # Tentar encontrar estruturas de listagem
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Procurar por cards/items de imóveis
                potential_listings = soup.select('div[class*="card"], div[class*="item"], div[class*="lote"], article, div[class*="property"], div[class*="imovel"]')
                
                if len(potential_listings) >= 3 or keyword_count >= 5:
                    result['status'] = 'online_with_properties'
                    logger.info(f"  ONLINE COM IMOVEIS: {len(potential_listings)} cards, {keyword_count} keywords")
                    self.results['online_with_properties'].append(result)
                else:
                    result['status'] = 'online_no_properties'
                    logger.warning(f"  ONLINE SEM IMOVEIS: {len(potential_listings)} cards, {keyword_count} keywords")
                    self.results['online_no_properties'].append(result)
                
                return result
                
        except httpx.TimeoutException:
            result['status'] = 'offline'
            result['error_message'] = "Timeout"
            logger.error(f"  TIMEOUT")
            self.results['offline'].append(result)
            return result
            
        except httpx.ConnectError:
            result['status'] = 'offline'
            result['error_message'] = "Não foi possível conectar"
            logger.error(f"  ERRO DE CONEXAO")
            self.results['offline'].append(result)
            return result
            
        except Exception as e:
            result['status'] = 'error'
            result['error_message'] = str(e)[:200]
            logger.error(f"  ERRO: {e}")
            self.results['error'].append(result)
            return result
    
    async def verify_all(self, auctioneers: list) -> dict:
        """Verifica todos os sites em lotes"""
        total = len(auctioneers)
        logger.info(f"\nIniciando verificação de {total} sites...")
        logger.info("="*80)
        
        # Processar em lotes de 10 para não sobrecarregar
        batch_size = 10
        for i in range(0, total, batch_size):
            batch = auctioneers[i:i+batch_size]
            logger.info(f"\nProcessando lote {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
            
            tasks = [self.verify_site(auc) for auc in batch]
            await asyncio.gather(*tasks)
            
            # Aguardar entre lotes para ser educado com os servidores
            if i + batch_size < total:
                await asyncio.sleep(2)
        
        return self.results
    
    def print_summary(self):
        """Imprime resumo dos resultados"""
        logger.info("\n" + "="*80)
        logger.info("RESUMO DA VERIFICACAO")
        logger.info("="*80)
        
        logger.info(f"\nOnline COM imóveis: {len(self.results['online_with_properties'])}")
        for r in self.results['online_with_properties'][:5]:
            logger.info(f"  - {r['name']}: {r['property_keyword_count']} keywords")
        if len(self.results['online_with_properties']) > 5:
            logger.info(f"  ... e mais {len(self.results['online_with_properties']) - 5}")
        
        logger.info(f"\nOnline SEM imóveis: {len(self.results['online_no_properties'])}")
        for r in self.results['online_no_properties'][:5]:
            logger.info(f"  - {r['name']}")
        if len(self.results['online_no_properties']) > 5:
            logger.info(f"  ... e mais {len(self.results['online_no_properties']) - 5}")
        
        logger.info(f"\nOffline/Inacessível: {len(self.results['offline'])}")
        for r in self.results['offline'][:5]:
            logger.info(f"  - {r['name']}: {r['error_message']}")
        if len(self.results['offline']) > 5:
            logger.info(f"  ... e mais {len(self.results['offline']) - 5}")
        
        logger.info(f"\nRedirecionados: {len(self.results['redirected'])}")
        for r in self.results['redirected'][:3]:
            logger.info(f"  - {r['name']}: {r['error_message']}")
        
        logger.info(f"\nProtegidos por Cloudflare: {len(self.results['cloudflare_protected'])}")
        for r in self.results['cloudflare_protected'][:3]:
            logger.info(f"  - {r['name']}")
        
        logger.info(f"\nErros: {len(self.results['error'])}")
        for r in self.results['error'][:3]:
            logger.info(f"  - {r['name']}: {r['error_message']}")
        
        logger.info("\n" + "="*80)


async def main():
    """Função principal"""
    logger.info("="*80)
    logger.info("VERIFICACAO AUTOMATICA DE SITES - PARTE 3.2")
    logger.info("="*80)
    
    # Buscar leiloeiros com erro "Nenhum imóvel encontrado"
    logger.info("\nBuscando leiloeiros com erro 'Nenhum imovel encontrado'...")
    
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, website
                    FROM auctioneers
                    WHERE scrape_status = 'error'
                    AND scrape_error LIKE '%Nenhum imóvel%'
                    ORDER BY name
                """)
                
                auctioneers = [dict(row) for row in cur.fetchall()]
                logger.info(f"Encontrados {len(auctioneers)} leiloeiros para verificar")
    
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco: {e}")
        logger.info("\nUsando lista local para teste...")
        # Se não conseguir conectar, usar lista de exemplo
        auctioneers = [
            {'id': '179', 'name': 'Abaleiloes', 'website': 'https://www.abaleiloes.com.br'},
            {'id': '104', 'name': 'Agenciadeleiloes', 'website': 'https://www.agenciadeleiloes.com.br'},
        ]
    
    if not auctioneers:
        logger.warning("Nenhum leiloeiro encontrado!")
        return
    
    # Verificar sites
    verifier = SiteVerifier()
    results = await verifier.verify_all(auctioneers)
    
    # Imprimir resumo
    verifier.print_summary()
    
    # Salvar resultados em arquivo
    output_file = f"verificacao_sites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nResultados salvos em: {output_file}")
    
    # Gerar recomendações
    logger.info("\n" + "="*80)
    logger.info("RECOMENDACOES")
    logger.info("="*80)
    
    if results['online_with_properties']:
        logger.info(f"\n1. Sites com imóveis ({len(results['online_with_properties'])}): RE-SCRAPE com configuração melhorada")
    
    if results['cloudflare_protected']:
        logger.info(f"\n2. Sites protegidos ({len(results['cloudflare_protected'])}): Usar Playwright/Playwright Stealth")
    
    if results['redirected']:
        logger.info(f"\n3. Sites redirecionados ({len(results['redirected'])}): Atualizar URL no banco")
    
    if results['online_no_properties']:
        logger.info(f"\n4. Sites sem imóveis ({len(results['online_no_properties'])}): Marcar como 'no_properties_available'")
    
    if results['offline']:
        logger.info(f"\n5. Sites offline ({len(results['offline'])}): Marcar como 'disabled'")
    
    logger.info("\n" + "="*80)
    logger.info("VERIFICACAO CONCLUIDA!")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
