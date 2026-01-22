"""
Playwright Integrated Scraper - Extrai e salva imóveis no banco
Versão integrada que persiste dados reais
"""

import asyncio
import logging
import hashlib
import uuid
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urljoin
import os

from app.models.property import Property
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class PlaywrightIntegratedScraper:
    """Scraper com Playwright Stealth que extrai e salva imóveis no banco"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # Setup Supabase
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    async def _setup_browser(self):
        """Setup Playwright com configuração stealth"""
        if self.playwright:
            return
            
        self.playwright = await async_playwright().start()
        
        # Launch browser com argumentos stealth
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        # Criar contexto com headers realistas
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )
        
        self.page = await context.new_page()
        
        # Injetar scripts stealth
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
            window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {}};
        """)
        
        logger.info("Playwright Stealth configurado")
        
    async def _close_browser(self):
        """Fecha o browser"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
        except Exception as e:
            logger.debug(f"Erro ao fechar browser: {e}")
    
    async def _scroll_page(self):
        """Scroll na página para carregar conteúdo lazy"""
        try:
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 100;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if(totalHeight >= scrollHeight){
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            await asyncio.sleep(1)
        except Exception as e:
            logger.debug(f"Erro ao fazer scroll: {e}")
    
    def _extract_properties_from_html(self, html: str, base_url: str, auctioneer_id: str, auctioneer_name: str) -> List[Dict]:
        """Extrai dados de imóveis do HTML - VERSÃO MELHORADA"""
        soup = BeautifulSoup(html, 'html.parser')
        properties = []
        
        # ESTRATÉGIA 1: Procurar links diretos para lotes/imóveis
        direct_links = soup.find_all('a', href=lambda x: x and any(
            kw in x.lower() for kw in ['lote', 'imovel', 'property', 'item', 'detalhes', 'detail']
        ))
        
        if direct_links:
            logger.info(f"✅ ESTRATÉGIA 1: Encontrados {len(direct_links)} links diretos")
            for link in direct_links[:100]:  # Limitar a 100
                try:
                    # Pegar o card pai (se existir)
                    card = link.find_parent(['div', 'article', 'li', 'tr'])
                    if not card:
                        card = link
                    
                    # Extrair título do link ou card
                    title = None
                    # Tentar atributos do link
                    if link.get('title'):
                        title = link.get('title').strip()
                    elif link.get('aria-label'):
                        title = link.get('aria-label').strip()
                    elif link.get_text(strip=True):
                        title = link.get_text(strip=True)
                    
                    # Tentar headers no card pai
                    if not title and card:
                        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            header = card.find(tag)
                            if header:
                                title = header.get_text(strip=True)
                                break
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # Limitar tamanho do título
                    title = title[:500]
                    
                    # URL
                    source_url = urljoin(base_url, link.get('href'))
                    
                    # Extrair outros dados do card
                    card_text = card.get_text() if card else ''
                    
                    # Preço
                    price = self._extract_price(card_text)
                    
                    # Localização
                    location = self._extract_location(card_text)
                    city, state = self._extract_city_state(location)
                    
                    # Imagem
                    img = card.find('img', src=True) if card else None
                    image_url = urljoin(base_url, img.get('src')) if img else None
                    
                    # Área
                    area = self._extract_area(card_text)
                    
                    # Gerar ID único
                    prop_id = self._generate_property_id(auctioneer_id, source_url, title)
                    
                    properties.append({
                        'id': prop_id,
                        'title': title,
                        'source_url': source_url,
                        'auction_value': price,
                        'city': city or 'Não Informado',
                        'state': state or 'NI',
                        'image_url': image_url,
                        'area': area,
                        'auctioneer_id': auctioneer_id,
                        'category': 'Outros',
                        'auction_type': 'Outros',
                        'scraped_at': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.debug(f"Erro ao extrair link direto: {e}")
                    continue
        
        # ESTRATÉGIA 2: Buscar por cards/containers se não encontrou links suficientes
        if len(properties) < 5:
            logger.info(f"⚠️ ESTRATÉGIA 2: Apenas {len(properties)} links diretos, tentando cards genéricos...")
            
            card_selectors = [
                'div[class*="lote"]',
                'div[class*="imovel"]',
                'div[class*="property"]',
                'article[class*="item"]',
                'article[class*="card"]',
                'div[class*="product"]',
                'div[class*="listing"]',
                'li[class*="item"]',
                'div[id*="lote"]',
                'div[id*="item"]'
            ]
            
            all_cards = []
            for selector in card_selectors:
                cards = soup.select(selector)
                if cards:
                    logger.info(f"  - {selector}: {len(cards)} encontrados")
                    all_cards.extend(cards)
            
            # Deduplicate
            unique_cards = list({id(card): card for card in all_cards}.values())
            logger.info(f"  Total: {len(unique_cards)} cards únicos")
            
            for i, card in enumerate(unique_cards[:100]):
                try:
                    # Extrair título (mais flexível)
                    title = None
                    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b']:
                        elem = card.find(tag)
                        if elem:
                            text = elem.get_text(strip=True)
                            if len(text) > 3:
                                title = text[:500]
                                break
                    
                    # Se não achou header, pegar primeiro link com texto
                    if not title:
                        link = card.find('a', href=True)
                        if link and link.get_text(strip=True):
                            title = link.get_text(strip=True)[:500]
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # URL
                    link = card.find('a', href=True)
                    source_url = urljoin(base_url, link.get('href')) if link else base_url
                    
                    # Outros dados
                    card_text = card.get_text()
                    price = self._extract_price(card_text)
                    location = self._extract_location(card_text)
                    city, state = self._extract_city_state(location)
                    
                    img = card.find('img', src=True)
                    image_url = urljoin(base_url, img.get('src')) if img else None
                    
                    area = self._extract_area(card_text)
                    
                    prop_id = self._generate_property_id(auctioneer_id, source_url, title)
                    
                    properties.append({
                        'id': prop_id,
                        'title': title,
                        'source_url': source_url,
                        'auction_value': price,
                        'city': city or 'Não Informado',
                        'state': state or 'NI',
                        'image_url': image_url,
                        'area': area,
                        'auctioneer_id': auctioneer_id,
                        'category': 'Outros',
                        'auction_type': 'Outros',
                        'scraped_at': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.debug(f"Erro ao extrair card {i}: {e}")
                    continue
        
        # Deduplicate por ID
        unique_props = {p['id']: p for p in properties}.values()
        properties = list(unique_props)
        
        logger.info(f"✅ TOTAL EXTRAÍDO: {len(properties)} imóveis válidos")
        return properties
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extrai preço do texto"""
        try:
            # Procurar padrões como R$ 100.000,00
            match = re.search(r'R\$?\s*[\d.]+,\d{2}', text)
            if match:
                price_str = match.group()
                cleaned = re.sub(r'[R$\s]', '', price_str)
                cleaned = cleaned.replace('.', '').replace(',', '.')
                return float(cleaned)
        except:
            pass
        return None
    
    def _extract_location(self, text: str) -> str:
        """Extrai localização do texto"""
        # Procurar padrões de cidade - Estado
        match = re.search(r'([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç\s]+)\s*[-/]\s*([A-Z]{2})', text)
        if match:
            return f"{match.group(1).strip()} - {match.group(2)}"
        return ""
    
    def _extract_city_state(self, location: str) -> tuple:
        """Extrai cidade e estado da localização"""
        if not location:
            return None, None
        
        parts = location.split('-')
        if len(parts) == 2:
            city = parts[0].strip()
            state = parts[1].strip()[:2]
            return city, state
        return None, None
    
    def _extract_area(self, text: str) -> Optional[float]:
        """Extrai área em m²"""
        try:
            match = re.search(r'([\d.,]+)\s*m[²2]', text, re.IGNORECASE)
            if match:
                area_str = match.group(1).replace('.', '').replace(',', '.')
                return float(area_str)
        except:
            pass
        return None
    
    def _generate_property_id(self, auctioneer_id: str, url: str, title: str) -> str:
        """Gera ID único para o imóvel"""
        unique_string = f"{auctioneer_id}_{url}_{title}"
        hash_value = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        return f"{auctioneer_id}_{hash_value}"
    
    async def scrape_and_save_auctioneer(self, auctioneer_id: str, auctioneer_name: str, website: str) -> Dict:
        """
        Scrape um leiloeiro e salva os imóveis no banco
        
        Returns:
            Dict com status, quantidade de imóveis, etc.
        """
        try:
            await self._setup_browser()
            
            logger.info(f"[{auctioneer_name}] Acessando {website}")
            
            # Navegar com retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.page.goto(website, wait_until='networkidle', timeout=60000)
                    break
                except PlaywrightTimeoutError:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Timeout na tentativa {attempt + 1}, tentando novamente...")
                    await asyncio.sleep(2)
            
            # Aguardar carregamento
            await asyncio.sleep(5)
            
            # Scroll para lazy content
            await self._scroll_page()
            
            # Obter HTML
            html = await self.page.content()
            
            # Verificar Cloudflare
            if 'cloudflare' in html.lower() and 'checking your browser' in html.lower():
                logger.warning("Cloudflare challenge detectado, aguardando...")
                await asyncio.sleep(10)
                html = await self.page.content()
            
            # Extrair propriedades
            properties = self._extract_properties_from_html(html, website, auctioneer_id, auctioneer_name)
            
            if not properties:
                logger.warning(f"[{auctioneer_name}] Nenhum imóvel extraído")
                # Atualizar status
                self.supabase.table('auctioneers').update({
                    'scrape_status': 'no_properties',
                    'scrape_error': 'Nenhum imóvel encontrado com Playwright',
                    'last_scrape': datetime.now().isoformat(),
                    'property_count': 0
                }).eq('id', auctioneer_id).execute()
                
                return {
                    'success': True,
                    'auctioneer_id': auctioneer_id,
                    'auctioneer_name': auctioneer_name,
                    'properties_found': 0,
                    'properties_saved': 0,
                    'bypassed_cloudflare': True
                }
            
            # Salvar no banco de dados
            saved_count = 0
            for prop in properties:
                try:
                    self.supabase.table('properties').upsert(prop).execute()
                    saved_count += 1
                except Exception as e:
                    logger.debug(f"Erro ao salvar imóvel {prop['id']}: {e}")
            
            # Atualizar status do leiloeiro
            self.supabase.table('auctioneers').update({
                'scrape_status': 'success',
                'scrape_error': None,
                'last_scrape': datetime.now().isoformat(),
                'property_count': saved_count
            }).eq('id', auctioneer_id).execute()
            
            logger.info(f"[{auctioneer_name}] ✅ {saved_count} imóveis salvos no banco")
            
            return {
                'success': True,
                'auctioneer_id': auctioneer_id,
                'auctioneer_name': auctioneer_name,
                'properties_found': len(properties),
                'properties_saved': saved_count,
                'bypassed_cloudflare': True
            }
            
        except Exception as e:
            logger.error(f"[{auctioneer_name}] Erro: {e}")
            
            # Atualizar com erro
            self.supabase.table('auctioneers').update({
                'scrape_status': 'error',
                'scrape_error': f'Playwright error: {str(e)}',
                'last_scrape': datetime.now().isoformat()
            }).eq('id', auctioneer_id).execute()
            
            return {
                'success': False,
                'auctioneer_id': auctioneer_id,
                'auctioneer_name': auctioneer_name,
                'error': str(e),
                'bypassed_cloudflare': False
            }
        finally:
            await self._close_browser()
