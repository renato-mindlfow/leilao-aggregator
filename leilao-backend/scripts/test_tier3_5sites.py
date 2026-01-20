#!/usr/bin/env python3
"""TESTE TIER 3: ScrapingBee com 5 sites selecionados"""
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

# 5 SITES PARA TESTE
SITES_TESTE = [
    "megaleiloes.com.br",      # Controle - funcionou no TIER 2
    "fidalgoleiloes.com.br",   # CloudFlare
    "bestleiloes.com.br",      # CloudFlare
    "granadoleiloes.com.br",   # CloudFlare
    "lottileiloes.com.br"      # CloudFlare
]

class ExtratorTier3Teste:
    def __init__(self):
        if not SCRAPINGBEE_API_KEY:
            raise ValueError("SCRAPINGBEE_API_KEY não configurada no .env")
        self.api_key = SCRAPINGBEE_API_KEY
        self.api_url = "https://app.scrapingbee.com/api/v1/"
        self.resultados = []
        self.falhas = []
        self.creditos_usados = 0
        
        # SELETORES ROBUSTOS DO TIER 2 (16 seletores que funcionaram)
        self.seletores_cards = [
            'a[href*="/imovel"]',
            'a[href*="/lote"]',
            'a[href*="/leilao"]',
            'a[href*="/detalhes"]',
            'a[href*="/imoveis/"]',
            '.property-card a',
            '.imovel-card a',
            '.card-imovel a',
            'article a',
            '.listing-item a',
            '.product-item a',
            'div[class*="property"] a',
            'div[class*="imovel"] a',
            'div[class*="card"] a[href*="imovel"]',
            'div[class*="list"] a[href*="imovel"]',
            'a.card-link'
        ]
        
    async def extrair_site(self, dominio: str) -> Dict:
        url_base = f"https://www.{dominio}"
        url_imoveis = self._construir_url_imoveis(url_base, dominio)
        
        logger.info(f"🔍 Extraindo (ScrapingBee): {dominio}")
        logger.info(f"   URL: {url_imoveis}")
        
        resultado = {
            "dominio": dominio,
            "url_base": url_base,
            "url_testada": url_imoveis,
            "timestamp": datetime.now().isoformat(),
            "tier": "TIER_3_SCRAPINGBEE_TESTE",
            "sucesso": False,
            "imoveis": [],
            "total_imoveis": 0,
            "creditos_usados": 0,
            "erro": None,
            "seletor_usado": None,
            "html_size": 0
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                params = {
                    "api_key": self.api_key,
                    "url": url_imoveis,
                    "render_js": "true",
                    "premium_proxy": "true",
                    "country_code": "br",
                    "wait": "5000",
                    "block_ads": "true"
                }
                
                logger.info(f"   🔄 Chamando ScrapingBee...")
                response = await client.get(self.api_url, params=params)
                self.creditos_usados += 25
                resultado["creditos_usados"] = 25
                
                logger.info(f"   📡 HTTP Status: {response.status_code}")
                
                if response.status_code == 200:
                    html = response.text
                    resultado["html_size"] = len(html)
                    logger.info(f"   📄 HTML recebido: {len(html):,} chars")
                    
                    # Verificar se tem CloudFlare challenge
                    if "cf-browser-verification" in html.lower() or "checking your browser" in html.lower():
                        logger.warning(f"   ⚠️ CloudFlare challenge ainda presente no HTML!")
                    
                    imoveis, seletor = self._extrair_imoveis_html(html, url_imoveis)
                    resultado["imoveis"] = imoveis
                    resultado["total_imoveis"] = len(imoveis)
                    resultado["seletor_usado"] = seletor
                    resultado["sucesso"] = len(imoveis) > 0
                    
                    if len(imoveis) > 0:
                        logger.info(f"   ✅ Sucesso: {len(imoveis)} imóveis")
                        logger.info(f"   🎯 Seletor usado: {seletor}")
                    else:
                        logger.warning(f"   ⚠️ Nenhum imóvel encontrado")
                else:
                    resultado["erro"] = f"ScrapingBee HTTP {response.status_code}"
                    logger.error(f"   ❌ Erro: HTTP {response.status_code}")
                    
        except Exception as e:
            resultado["erro"] = str(e)[:500]
            logger.error(f"   ❌ Erro: {e}")
        
        return resultado
    
    def _construir_url_imoveis(self, url_base: str, dominio: str) -> str:
        # URLs conhecidas específicas
        urls_conhecidas = {
            "megaleiloes.com.br": "/imoveis",
            "sold.com.br": "/leiloes/imoveis",
            "leje.com.br": "/leiloes/imoveis",
            "biasileiloes.com.br": "/imoveis",
            "milanleiloes.com.br": "/leiloes"
        }
        return url_base + urls_conhecidas.get(dominio, "/imoveis")
    
    def _extrair_imoveis_html(self, html: str, url_origem: str) -> tuple[List[Dict], Optional[str]]:
        soup = BeautifulSoup(html, 'html.parser')
        imoveis = []
        seletor_usado = None
        
        # Testar cada seletor até encontrar matches
        for seletor in self.seletores_cards:
            cards = soup.select(seletor)
            if cards:
                logger.info(f"      ✅ {len(cards)} elementos encontrados com seletor: {seletor}")
                seletor_usado = seletor
                
                for card in cards:
                    imovel = self._extrair_dados_card(card, url_origem)
                    if imovel:
                        imoveis.append(imovel)
                
                if imoveis:
                    break
        
        # Deduplicar por URL
        urls_vistas = set()
        imoveis_unicos = []
        for i in imoveis:
            if i.get("url") and i["url"] not in urls_vistas:
                urls_vistas.add(i["url"])
                imoveis_unicos.append(i)
        
        return imoveis_unicos, seletor_usado
    
    def _extrair_dados_card(self, card, url_origem: str) -> Optional[Dict]:
        dados = {
            "url_origem": url_origem,
            "extraido_em": datetime.now().isoformat(),
            "tier": "TIER_3_SCRAPINGBEE_TESTE"
        }
        
        # Extrair href
        if card.name == 'a':
            href = card.get('href', '')
        else:
            link = card.find('a')
            href = link.get('href', '') if link else ''
        
        # Filtro flexível de URL (igual TIER 2 corrigido)
        if href and len(href) > 1 and href != '#':
            if not href.startswith('http'):
                from urllib.parse import urljoin
                href = urljoin(url_origem, href)
            dados["url"] = href
        else:
            return None
        
        # Extrair texto
        texto = card.get_text(strip=True)
        dados["texto_card"] = texto[:500] if texto else None
        
        # Extrair preço
        preco_match = re.search(r'R\$\s*([\d.,]+)', texto or '')
        if preco_match:
            try:
                dados["preco"] = float(preco_match.group(1).replace('.', '').replace(',', '.'))
            except:
                pass
        
        return dados
    
    async def processar_teste(self):
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 TESTE TIER 3: {len(SITES_TESTE)} sites")
        logger.info(f"💰 Créditos estimados: {len(SITES_TESTE) * 25} (máx)")
        logger.info(f"{'='*60}\n")
        
        for i, dominio in enumerate(SITES_TESTE, 1):
            logger.info(f"\n[{i}/{len(SITES_TESTE)}] {'-'*40}")
            resultado = await self.extrair_site(dominio)
            
            if resultado["sucesso"]:
                self.resultados.append(resultado)
            else:
                self.falhas.append(resultado)
            
            # Pausa entre requisições
            await asyncio.sleep(3)
        
        await self._salvar_resultados()
        self._exibir_relatorio()
    
    async def _salvar_resultados(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = OUTPUT_DIR / f"teste_tier3_5sites_{timestamp}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "tier": "TIER_3_SCRAPINGBEE_TESTE",
                "timestamp": datetime.now().isoformat(),
                "sites_testados": SITES_TESTE,
                "total_sites": len(SITES_TESTE),
                "sucesso": len(self.resultados),
                "falhas": len(self.falhas),
                "creditos_totais_usados": self.creditos_usados,
                "total_imoveis": sum(r["total_imoveis"] for r in self.resultados),
                "resultados": self.resultados,
                "falhas_detalhes": self.falhas
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📁 Resultados salvos: {json_file}")
    
    def _exibir_relatorio(self):
        total = len(SITES_TESTE)
        sucessos = len(self.resultados)
        falhas = len(self.falhas)
        taxa = (sucessos / total * 100) if total > 0 else 0
        total_imoveis = sum(r["total_imoveis"] for r in self.resultados)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 RELATÓRIO DO TESTE TIER 3")
        logger.info(f"{'='*60}")
        logger.info(f"Sites testados: {total}")
        logger.info(f"Sucessos: {sucessos}")
        logger.info(f"Falhas: {falhas}")
        logger.info(f"Taxa de sucesso: {taxa:.1f}%")
        logger.info(f"Total de imóveis: {total_imoveis}")
        logger.info(f"Créditos usados: {self.creditos_usados}")
        logger.info(f"{'='*60}\n")
        
        if self.resultados:
            logger.info(f"✅ SITES COM SUCESSO:")
            for r in self.resultados:
                logger.info(f"   {r['dominio']}: {r['total_imoveis']} imóveis ({r['seletor_usado']})")
        
        if self.falhas:
            logger.info(f"\n❌ SITES COM FALHA:")
            for f in self.falhas:
                erro = f.get('erro') or 'Nenhum imóvel encontrado'
                logger.info(f"   {f['dominio']}: {erro}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 RECOMENDAÇÃO:")
        logger.info(f"{'='*60}")
        
        if taxa >= 60:
            logger.info(f"✅ Taxa de {taxa:.1f}% é BOA!")
            logger.info(f"✅ APROVAR execução completa dos 77 sites")
            logger.info(f"✅ Custo total: ~$19-20 USD")
            logger.info(f"✅ Retorno esperado: 5.000-10.000 imóveis")
        elif taxa >= 40:
            logger.info(f"⚠️ Taxa de {taxa:.1f}% é RAZOÁVEL")
            logger.info(f"⚠️ Considere executar, mas com expectativas ajustadas")
            logger.info(f"⚠️ Retorno esperado: 2.000-5.000 imóveis")
        else:
            logger.info(f"❌ Taxa de {taxa:.1f}% é BAIXA")
            logger.info(f"❌ NÃO RECOMENDADO executar completo")
            logger.info(f"❌ Investigar seletores e paths antes de continuar")
        
        logger.info(f"{'='*60}\n")

async def main():
    if not SCRAPINGBEE_API_KEY:
        logger.error("❌ SCRAPINGBEE_API_KEY não configurada no .env")
        logger.error("   Configure no arquivo leilao-backend/.env")
        return
    
    extrator = ExtratorTier3Teste()
    await extrator.processar_teste()

if __name__ == "__main__":
    asyncio.run(main())
