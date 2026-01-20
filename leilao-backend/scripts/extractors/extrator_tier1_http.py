#!/usr/bin/env python3
"""
EXTRATOR TIER 1: HTTP Simples
Para sites que funcionam sem JavaScript ou proteção anti-bot
"""

import asyncio
import httpx
import json
import re
import sys
import codecs
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import logging

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Diretórios
OUTPUT_DIR = Path("logs/extracao_fase2/tier1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ExtratorTier1:
    """Extrator HTTP simples para sites sem proteção."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.resultados: List[Dict] = []
        self.falhas: List[Dict] = []
        
    async def extrair_site(self, dominio: str, config_paginacao: Optional[Dict] = None) -> Dict:
        """Extrai imóveis de um site."""
        
        url_base = f"https://www.{dominio}"
        logger.info(f"🔍 Extraindo: {dominio}")
        
        resultado = {
            "dominio": dominio,
            "url_base": url_base,
            "timestamp": datetime.now().isoformat(),
            "sucesso": False,
            "imoveis": [],
            "total_imoveis": 0,
            "paginas_processadas": 0,
            "erro": None
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=30.0, 
                follow_redirects=True, 
                headers=self.headers
            ) as client:
                
                # Determinar URLs a processar
                urls = self._gerar_urls(url_base, dominio, config_paginacao)
                
                for url in urls:
                    try:
                        response = await client.get(url)
                        
                        if response.status_code == 200:
                            imoveis = self._extrair_imoveis_html(response.text, url)
                            resultado["imoveis"].extend(imoveis)
                            resultado["paginas_processadas"] += 1
                            logger.info(f"   ✅ {url}: {len(imoveis)} imóveis")
                        else:
                            logger.warning(f"   ⚠️ {url}: HTTP {response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"   ❌ {url}: {e}")
                    
                    # Pausa entre requisições
                    await asyncio.sleep(1)
                
                resultado["total_imoveis"] = len(resultado["imoveis"])
                resultado["sucesso"] = resultado["total_imoveis"] > 0
                
        except Exception as e:
            resultado["erro"] = str(e)
            logger.error(f"❌ Erro em {dominio}: {e}")
        
        return resultado
    
    def _gerar_urls(self, url_base: str, dominio: str, config: Optional[Dict]) -> List[str]:
        """Gera lista de URLs a processar baseado na configuração de paginação."""
        
        urls = []
        
        # Tentar URLs comuns de imóveis
        paths_imoveis = [
            "/imoveis",
            "/leiloes/imoveis",
            "/leilao-de-imoveis",
            "/?tipo=imoveis",
            "/busca?categoria=imoveis",
        ]
        
        # Se temos configuração de paginação
        if config and config.get("tipo") == "NUMERIC":
            pattern = config.get("url_pattern", "/imoveis?page={page}")
            total = config.get("total_paginas", 5)
            
            for page in range(1, total + 1):
                url = url_base + pattern.format(page=page)
                urls.append(url)
        else:
            # Sem paginação conhecida, tentar paths comuns
            for path in paths_imoveis:
                urls.append(url_base + path)
        
        return urls
    
    def _extrair_imoveis_html(self, html: str, url_origem: str) -> List[Dict]:
        """Extrai dados de imóveis do HTML."""
        
        soup = BeautifulSoup(html, 'html.parser')
        imoveis = []
        
        # Seletores comuns para cards de imóveis
        seletores_cards = [
            'a[href*="/imovel/"]',
            'a[href*="/imoveis/"]',
            'a[href*="/lote/"]',
            'a[href*="/detalhes/"]',
            '.property-card',
            '.imovel-card',
            '.card-imovel',
            '[class*="property"]',
            '[class*="imovel"]',
        ]
        
        cards_encontrados = []
        for seletor in seletores_cards:
            cards = soup.select(seletor)
            if cards:
                cards_encontrados.extend(cards)
                break
        
        # Remover duplicatas
        urls_vistas = set()
        
        for card in cards_encontrados:
            try:
                imovel = self._extrair_dados_card(card, url_origem)
                if imovel and imovel.get("url") not in urls_vistas:
                    urls_vistas.add(imovel.get("url"))
                    imoveis.append(imovel)
            except Exception as e:
                logger.debug(f"Erro ao extrair card: {e}")
        
        return imoveis
    
    def _extrair_dados_card(self, card, url_origem: str) -> Optional[Dict]:
        """Extrai dados de um card de imóvel."""
        
        dados = {
            "url_origem": url_origem,
            "extraido_em": datetime.now().isoformat(),
        }
        
        # URL do imóvel
        if card.name == 'a':
            href = card.get('href', '')
        else:
            link = card.find('a')
            href = link.get('href', '') if link else ''
        
        if href:
            if not href.startswith('http'):
                # URL relativa
                from urllib.parse import urljoin
                href = urljoin(url_origem, href)
            dados["url"] = href
        else:
            return None
        
        # Título
        titulo_elem = card.find(['h1', 'h2', 'h3', 'h4', '.titulo', '.title'])
        if titulo_elem:
            dados["titulo"] = titulo_elem.get_text(strip=True)
        
        # Preço
        texto_card = card.get_text()
        preco_match = re.search(r'R\$\s*([\d.,]+)', texto_card)
        if preco_match:
            preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
            try:
                dados["preco"] = float(preco_str)
            except:
                pass
        
        # Localização
        loc_patterns = [
            r'([A-Za-zÀ-ú\s]+)\s*[-/]\s*([A-Z]{2})',  # Cidade - UF
            r'([A-Z]{2})\s*[-/]\s*([A-Za-zÀ-ú\s]+)',  # UF - Cidade
        ]
        for pattern in loc_patterns:
            match = re.search(pattern, texto_card)
            if match:
                dados["localizacao"] = match.group(0)
                break
        
        # Imagem
        img = card.find('img')
        if img:
            src = img.get('src') or img.get('data-src')
            if src and not 'logo' in src.lower():
                dados["imagem"] = src
        
        return dados
    
    async def processar_lista(self, dominios: List[str], config_paginacao: Dict = None):
        """Processa lista de domínios."""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 TIER 1: Processando {len(dominios)} sites com HTTP simples")
        logger.info(f"{'='*60}\n")
        
        for i, dominio in enumerate(dominios, 1):
            logger.info(f"\n[{i}/{len(dominios)}] {'-'*40}")
            
            config = config_paginacao.get(dominio) if config_paginacao else None
            resultado = await self.extrair_site(dominio, config)
            
            if resultado["sucesso"]:
                self.resultados.append(resultado)
                logger.info(f"   ✅ Sucesso: {resultado['total_imoveis']} imóveis")
            else:
                self.falhas.append(resultado)
                logger.warning(f"   ⚠️ Falha: {resultado.get('erro', 'Nenhum imóvel encontrado')}")
            
            # Pausa entre sites
            await asyncio.sleep(2)
        
        # Salvar resultados
        await self._salvar_resultados()
    
    async def _salvar_resultados(self):
        """Salva resultados em arquivos."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON com todos os resultados
        json_file = OUTPUT_DIR / f"tier1_resultados_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "tier": "TIER_1_HTTP",
                "timestamp": datetime.now().isoformat(),
                "total_sites": len(self.resultados) + len(self.falhas),
                "sucesso": len(self.resultados),
                "falhas": len(self.falhas),
                "total_imoveis": sum(r["total_imoveis"] for r in self.resultados),
                "resultados": self.resultados,
                "falhas_detalhes": self.falhas
            }, f, ensure_ascii=False, indent=2)
        
        # Lista de imóveis consolidada
        todos_imoveis = []
        for r in self.resultados:
            todos_imoveis.extend(r["imoveis"])
        
        imoveis_file = OUTPUT_DIR / f"tier1_imoveis_{timestamp}.json"
        with open(imoveis_file, 'w', encoding='utf-8') as f:
            json.dump(todos_imoveis, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📁 Resultados salvos:")
        logger.info(f"   {json_file}")
        logger.info(f"   {imoveis_file}")
        logger.info(f"\n📊 Resumo:")
        logger.info(f"   Sites com sucesso: {len(self.resultados)}")
        logger.info(f"   Sites com falha: {len(self.falhas)}")
        logger.info(f"   Total de imóveis: {len(todos_imoveis)}")


async def main():
    """Função principal."""
    
    # Carregar configuração de roteamento
    config_path = Path("config/roteamento_sites.json")
    
    if not config_path.exists():
        logger.error(f"❌ Arquivo de roteamento não encontrado: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Obter lista de sites TIER 1
    sites_tier1 = config.get("TIER_1_HTTP", {}).get("sites", [])
    config_paginacao = config.get("PAGINACAO", {}).get("sites", {})
    
    logger.info(f"📋 Sites TIER 1 carregados: {len(sites_tier1)}")
    
    # Executar extração
    extrator = ExtratorTier1()
    await extrator.processar_lista(sites_tier1, config_paginacao)


if __name__ == "__main__":
    asyncio.run(main())
