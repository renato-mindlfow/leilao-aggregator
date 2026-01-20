#!/usr/bin/env python3
"""EXTRATOR TIER 3: ScrapingBee - Para sites com CloudFlare forte ou proteção avançada"""
import asyncio, httpx, json, os, re, sys, codecs
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging

load_dotenv()

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("logs/extracao_fase2/tier3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")

class ExtratorTier3:
    def __init__(self):
        if not SCRAPINGBEE_API_KEY:
            raise ValueError("SCRAPINGBEE_API_KEY não configurada no .env")
        self.api_key, self.api_url = SCRAPINGBEE_API_KEY, "https://app.scrapingbee.com/api/v1/"
        self.resultados, self.falhas, self.creditos_usados = [], [], 0
        
    async def extrair_site(self, dominio: str, config_paginacao: Optional[Dict] = None) -> Dict:
        url_base = f"https://www.{dominio}"
        url_imoveis = self._construir_url_imoveis(url_base, dominio)
        logger.info(f"🔍 Extraindo (ScrapingBee): {dominio}")
        
        resultado = {"dominio": dominio, "url_base": url_base, "timestamp": datetime.now().isoformat(),
                    "tier": "TIER_3_SCRAPINGBEE", "sucesso": False, "imoveis": [],
                    "total_imoveis": 0, "creditos_usados": 0, "erro": None}
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                params = {"api_key": self.api_key, "url": url_imoveis, "render_js": "true",
                         "premium_proxy": "true", "country_code": "br", "wait": "5000", "block_ads": "true"}
                
                response = await client.get(self.api_url, params=params)
                self.creditos_usados += 25
                resultado["creditos_usados"] = 25
                
                if response.status_code == 200:
                    html = response.text
                    imoveis = self._extrair_imoveis_html(html, url_imoveis)
                    resultado["imoveis"], resultado["total_imoveis"] = imoveis, len(imoveis)
                    resultado["sucesso"] = len(imoveis) > 0
                    logger.info(f"   ✅ {len(imoveis)} imóveis extraídos")
                else:
                    resultado["erro"] = f"ScrapingBee HTTP {response.status_code}"
                    logger.error(f"   ❌ Erro: HTTP {response.status_code}")
        except Exception as e:
            resultado["erro"] = str(e)[:200]
            logger.error(f"   ❌ Erro: {e}")
        
        return resultado
    
    def _construir_url_imoveis(self, url_base: str, dominio: str) -> str:
        urls_conhecidas = {"leje.com.br": "/leiloes/imoveis", "biasileiloes.com.br": "/imoveis",
                          "milanleiloes.com.br": "/leiloes", "leiloes.com.br": "/imoveis"}
        return url_base + urls_conhecidas.get(dominio, "/imoveis")
    
    def _extrair_imoveis_html(self, html: str, url_origem: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        imoveis = []
        seletores = ['a[href*="/imovel/"]', 'a[href*="/lote/"]', 'a[href*="/detalhes/"]',
                    '.property-card', '.imovel-card']
        
        for seletor in seletores:
            cards = soup.select(seletor)
            if cards:
                for card in cards:
                    imovel = self._extrair_dados_card(card, url_origem)
                    if imovel: imoveis.append(imovel)
                break
        
        urls_vistas = set()
        return [i for i in imoveis if i.get("url") and not (i["url"] in urls_vistas or urls_vistas.add(i["url"]))]
    
    def _extrair_dados_card(self, card, url_origem: str) -> Optional[Dict]:
        dados = {"url_origem": url_origem, "extraido_em": datetime.now().isoformat(),
                "tier": "TIER_3_SCRAPINGBEE"}
        
        if card.name == 'a': href = card.get('href', '')
        else:
            link = card.find('a')
            href = link.get('href', '') if link else ''
        
        if href:
            if not href.startswith('http'):
                from urllib.parse import urljoin
                href = urljoin(url_origem, href)
            dados["url"] = href
        else: return None
        
        texto = card.get_text(strip=True)
        dados["texto_card"] = texto[:500] if texto else None
        
        preco_match = re.search(r'R\$\s*([\d.,]+)', texto or '')
        if preco_match:
            try: dados["preco"] = float(preco_match.group(1).replace('.', '').replace(',', '.'))
            except: pass
        
        return dados
    
    async def processar_lista(self, dominios: List[str], config_paginacao: Dict = None):
        logger.info(f"\n{'='*60}\n🚀 TIER 3: Processando {len(dominios)} sites com ScrapingBee")
        logger.info(f"⚠️ Estimativa de créditos: {len(dominios) * 25}\n{'='*60}\n")
        
        for i, dominio in enumerate(dominios, 1):
            logger.info(f"\n[{i}/{len(dominios)}] {'-'*40}")
            config = config_paginacao.get(dominio) if config_paginacao else None
            resultado = await self.extrair_site(dominio, config)
            if resultado["sucesso"]: self.resultados.append(resultado)
            else: self.falhas.append(resultado)
            await asyncio.sleep(2)
        
        await self._salvar_resultados()
    
    async def _salvar_resultados(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = OUTPUT_DIR / f"tier3_resultados_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({"tier": "TIER_3_SCRAPINGBEE", "timestamp": datetime.now().isoformat(),
                      "total_sites": len(self.resultados) + len(self.falhas),
                      "sucesso": len(self.resultados), "falhas": len(self.falhas),
                      "creditos_totais_usados": self.creditos_usados,
                      "total_imoveis": sum(r["total_imoveis"] for r in self.resultados),
                      "resultados": self.resultados, "falhas_detalhes": self.falhas},
                     f, ensure_ascii=False, indent=2)
        logger.info(f"\n📁 Resultados salvos: {json_file}")
        logger.info(f"💰 Créditos ScrapingBee usados: {self.creditos_usados}")

async def main():
    config_path = Path("config/roteamento_sites.json")
    if not config_path.exists():
        logger.error(f"❌ Arquivo de roteamento não encontrado")
        return
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    sites_tier3 = config.get("TIER_3_SCRAPINGBEE", {}).get("sites", [])
    config_paginacao = config.get("PAGINACAO", {}).get("sites", {})
    logger.info(f"📋 Sites TIER 3 carregados: {len(sites_tier3)}")
    extrator = ExtratorTier3()
    await extrator.processar_lista(sites_tier3, config_paginacao)

if __name__ == "__main__":
    asyncio.run(main())
