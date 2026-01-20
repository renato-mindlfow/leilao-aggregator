# 🚀 FASE 2: EXTRAÇÃO INTELIGENTE COM ROTEAMENTO EM 3 TIERS

**Objetivo**: Extrair imóveis de 256 sites acessíveis usando roteamento inteligente
**Base**: Resultados da validação Manus AI (146 ONLINE + 110 BLOCKED)
**Estratégia**: Cada site vai direto para o método que funciona

**Tempo Estimado**: 6-8 horas de execução total

---

## 📊 DISTRIBUIÇÃO DOS TIERS

| Tier | Método | Sites | % | Custo |
|------|--------|-------|---|-------|
| **TIER 1** | HTTP Simples | 146 | 50.5% | $0 |
| **TIER 2** | Playwright Stealth | ~85 | 29.4% | $0 |
| **TIER 3** | ScrapingBee | ~25 | 8.6% | $49/mês |
| **IGNORAR** | Offline | 32 | 11.1% | - |
| **TOTAL** | | **289** | 100% | |

---

## 🔧 ETAPA 1: CRIAR ESTRUTURA DE DIRETÓRIOS

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# Criar estrutura
mkdir -p config
mkdir -p scripts/extractors
mkdir -p logs/extracao_fase2
```

---

## 🔧 ETAPA 2: CRIAR ARQUIVO DE ROTEAMENTO

**Arquivo**: `leilao-backend/config/roteamento_sites.json`

```json
{
  "version": "1.0",
  "updated_at": "2026-01-20",
  "source": "Validação Manus AI + Diagnóstico Cursor",
  
  "TIER_1_HTTP": {
    "description": "Sites que funcionam com HTTP simples",
    "method": "httpx com headers de browser",
    "count": 146,
    "sites": [
      "abaleiloes.com.br",
      "akimotoleiloes.com.br",
      "albuquerquelins.com.br",
      "alencastroleiloes.com.br",
      "alexandridisleiloes.com.br",
      "alfaleiloes.com",
      "alleiloes.com.br",
      "allianceleiloes.com.br",
      "alvaroleiloes.com.br",
      "amleiloeiro.com.br",
      "andreluizleiloes.com.br",
      "arenaleiloes.com.br",
      "argonetworkleiloes.com.br",
      "arrematabem.com.br",
      "bartmannleiloes.com.br",
      "bastonleiloes.com.br",
      "benedettoleiloes.com.br",
      "bigleilao.com.br",
      "brunoleiloes.com.br",
      "bsbleiloes.com.br",
      "calilleiloes.com.br",
      "carloferrarileiloes.com.br",
      "casaforteleiloes.com.br",
      "centraljudicial.com.br",
      "cidafixerleiloes.com.br",
      "clademirleiloeiro.com.br",
      "claudiokussleiloes.com.br",
      "clebercardosoleiloes.com.br",
      "clovisleiloeiro.com.br",
      "correaleiloes.com.br",
      "cristianoescolaleiloes.com.br",
      "ctsleiloes.com.br",
      "cunhaleiloeiro.com.br",
      "dalaqualeiloes.com.br",
      "danieloliveiraleiloes.com.br",
      "dbmleiloes.com.br",
      "depaulaonline.com.br",
      "desantileiloes.com.br",
      "dhleiloes.com.br",
      "dldleiloeiro.com.br",
      "donhaleiloes.com",
      "dsleiloes.com.br",
      "e-leiloeiro.com.br",
      "eckertleiloes.com.br",
      "eduardovivian.com.br",
      "evolveleiloes.com.br",
      "fabiobarbosaleiloes.com.br",
      "fabioleiloes.com.br",
      "fariasleiloes.com.br",
      "faroonline.com.br",
      "feliperottaleiloes.com.br",
      "finattoleiloes.com.br",
      "francoleiloes.com.br",
      "frazaoleiloes.com.br",
      "fumagallileiloes.com.br",
      "gabrielleiloes.com.br",
      "gestorleiloes.com.br",
      "gilsoninumaruleiloes.com.br",
      "grandesleiloes.com.br",
      "grupoarremateleiloes.com.br",
      "grupocarvalholeiloes.com.br",
      "grupoleilo.com.br",
      "gustavoreisleiloes.com.br",
      "hastapublica.com.br",
      "hastavip.com.br",
      "hoppeleiloes.com.br",
      "inovaleilao.com.br",
      "jacleiloes.com.br",
      "jeleiloes.com.br",
      "jfleiloes.com.br",
      "jmleiloes.com.br",
      "jorgemarcoleiloes.com.br",
      "judhastas.com.br",
      "kleiloes.com.br",
      "kronbergleiloes.com.br",
      "ksleiloes.com.br",
      "lancecertoleiloes.com.br",
      "lanceja.com.br",
      "lancejudicial.com.br",
      "lancejusto.com.br",
      "lancenoleilao.com.br",
      "leilaobrasil.com.br",
      "leilaonainternet.com.br",
      "leilaovip.com.br",
      "leiloaria.com.br",
      "leiloeiropublico.com.br",
      "leiloesbonfadini.com.br",
      "leiloescentrooeste.com.br",
      "leiloesjudiciaisrs.com.br",
      "leiloeslaraforster.com.br",
      "leilomaster.com.br",
      "lessaleiloes.com.br",
      "liderleiloes.com.br",
      "lipinskileiloes.com.br",
      "lunellileiloes.com.br",
      "lut.com.br",
      "machadoleiloesrs.com.br",
      "maisleilao.com.br",
      "marquesleiloes.com.br",
      "medeirosleiloes.com.br",
      "megaleiloes.com.br",
      "moralesleiloes.com.br",
      "morescoleiloes.com.br",
      "odarlicanezinleiloes.com.br",
      "oesteleiloes.com.br",
      "pactoleiloes.com.br",
      "parquedosleiloes.com.br",
      "pecinileiloes.com.br",
      "portalzuk.com.br",
      "projudleiloes.com.br",
      "rabuskeleiloes.com.br",
      "raotaleiloes.com.br",
      "rdleiloes.com.br",
      "regionalleiloes.com.br",
      "ricardogomesleiloes.com.br",
      "rigolonleiloes.com.br",
      "rmcleiloes.com.br",
      "rochaleiloes.com.br",
      "rossileiloes.com.br",
      "rzleiloes.com.br",
      "santamarialeiloes.com.br",
      "santoseborinleiloes.com.br",
      "satoleiloes.com.br",
      "savoyleiloes.com.br",
      "silveiraleiloes.com.br",
      "simonleiloes.com.br",
      "sodresantoro.com.br",
      "sold.com.br",
      "soleiloes.com.br",
      "sublimeleiloes.com.br",
      "swleiloes.com.br",
      "tabaleiloes.com.br",
      "tezaleiloes.com.br",
      "tonialleiloes.com.br",
      "trevisanleiloes.com.br",
      "trileiloes.com.br",
      "turanileiloes.com.br",
      "unileiloes.com.br",
      "valeroleiloes.com.br",
      "vargasepintoleiloes.com.br",
      "veronicaleiloes.com.br",
      "vivaleiloes.com.br",
      "vmleiloes.com.br",
      "webleiloes.com.br",
      "wmleiloes.com.br"
    ]
  },
  
  "TIER_2_STEALTH": {
    "description": "Sites que precisam de Playwright com Stealth",
    "method": "Playwright + stealth scripts + headers completos",
    "count": 85,
    "sites": [
      "3torresleiloes.com.br",
      "adringleiloes.com.br",
      "agenciadeleiloes.com.br",
      "alemaoleiloeiro.com.br",
      "alexiusleiloes.com.br",
      "amaralleiloes.com.br",
      "amtleiloes.com.br",
      "anabrasilleiloes.com.br",
      "arnoldoleiloes.com.br",
      "backleiloes.com.br",
      "bestleiloes.com.br",
      "bianchileiloes.com.br",
      "bidgo.com.br",
      "brasilialeiloes.com.br",
      "bronzattoleiloes.com.br",
      "cardosoleiloes.com.br",
      "cargneluttileiloes.com.br",
      "casareisleiloesonline.com.br",
      "ckleiloes.com.br",
      "clicleiloes.com.br",
      "conceitoleiloes.com.br",
      "costanetoleiloeiro.com.br",
      "danielgarcialeiloes.com.br",
      "deborabarzleiloes.com.br",
      "destakleiloes.com.br",
      "duxleiloes.com.br",
      "eixoleiloes.com.br",
      "escritoriodeleiloes.com.br",
      "evaleiloes.com.br",
      "fauthleiloes.com.br",
      "ferronatoleiloes.com.br",
      "fidalgoleiloes.com.br",
      "glleiloes.com.br",
      "granadoleiloes.com.br",
      "gtleiloes.com.br",
      "hastalegal.com.br",
      "hisaleiloes.com.br",
      "horizonteleiloes.com.br",
      "infinityleiloes.com.br",
      "joaoluizleiloes.com.br",
      "juleiloes.com.br",
      "kildareleiloes.com.br",
      "ktzleiloes.com.br",
      "lanceleiloes.com.br",
      "lancevip.com.br",
      "lecapeleiloes.com.br",
      "leffaleiloes.com.br",
      "legisleiloes.com.br",
      "leilaobutia.com.br",
      "leilaoeletronico.com.br",
      "leilaoinvestment.com.br",
      "leilaosantos.com.br",
      "leiloeirobarbieri.com.br",
      "leiloes61.com.br",
      "leiloesfederal.com.br",
      "leiloesgold.com.br",
      "lottileiloes.com.br",
      "machadoleiloeiro.com.br",
      "marangonileiloes.com.br",
      "marceloleiloeiro.com.br",
      "marquesbarretoleiloes.com.br",
      "mgleiloes-rs.com.br",
      "michellileiloes.com.br",
      "montenegroleiloes.com.br",
      "monzonleiloes.com.br",
      "moraesleiloes.com.br",
      "mpleilao.com.br",
      "multleiloes.com",
      "natalialeiloes.com.br",
      "newtonleiloes.com.br",
      "nogarileiloes.com.br",
      "nossoleilao.com.br",
      "oaleiloes.com.br",
      "oleiloes.com.br",
      "oreidosleiloes.com.br",
      "paulotolentino.com.br",
      "pbcastro.com.br",
      "picellileiloes.com.br",
      "pietosoleiloes.com.br",
      "pimentelleiloes.com.br",
      "raicherleiloes.com.br",
      "rangelleiloes.com.br",
      "rauppleiloes.com.br",
      "rechleiloes.com.br",
      "renovarleiloes.com.br"
    ]
  },
  
  "TIER_3_SCRAPINGBEE": {
    "description": "Sites com CloudFlare forte - usar ScrapingBee direto",
    "method": "ScrapingBee API com premium_proxy=true",
    "count": 25,
    "sites": [
      "bcoleiloes.com.br",
      "biasileiloes.com.br",
      "leiloes.com.br",
      "leje.com.br",
      "milanleiloes.com.br",
      "ricoleiloes.com.br",
      "rjleiloes.com.br",
      "rocketleiloes.com.br",
      "ruipintoleiloeiro.com.br",
      "santayanaleiloes.com.br",
      "scheidleiloes.com.br",
      "scholanteleiloes.com.br",
      "sfrazao.com.br",
      "spencerleiloes.com.br",
      "superleiloes.net",
      "szortykaleiloes.com.br",
      "tmleiloes.com.br",
      "tribunaleiloes.com.br",
      "upleiloes.com.br",
      "utzigleiloes.com.br",
      "vidalleiloes.com.br",
      "wspleiloes.com.br",
      "zaccariasleiloes.com.br",
      "zagoleiloes.com.br",
      "zuccalmaglioleiloes.com.br"
    ]
  },
  
  "IGNORAR_OFFLINE": {
    "description": "Sites realmente offline - não processar",
    "reason": "DNS não resolve ou site permanentemente fora do ar",
    "count": 32,
    "sites": [
      "acleiloes.com.br",
      "alexsandroleiloes.com.br",
      "assuncaoleiloes.com.br",
      "e-confianca.com.br",
      "eleiloes.com.br",
      "flexleiloes.com.br",
      "freitasleiloeiro.com.br",
      "gustavomorettoleiloeiro.com.br",
      "jcleiloeiro.com.br",
      "joelreisleiloes.com.br",
      "josequencaleiloeiro.com.br",
      "kielleiloes.com.br",
      "kriegerleiloes.com.br",
      "lancetotal.com.br",
      "leiloeirodebrasilia.com.br",
      "leiloeiroqueiroz.com.br",
      "leiloesfreire.com.br",
      "leiloeirospcom.br",
      "luizleiloes.com.br",
      "melhorlanceleiloes.com.br",
      "mikedutraleiloeiro.com.br",
      "muckleiloes.com.br",
      "nakakogueleiloes.com.br",
      "nortonleiloes.com.br",
      "portaldosleiloes.com.br",
      "psnleiloes.com.br",
      "rmmleiloes.com.br",
      "sumareleiloes.com.br",
      "superlanceleilao.com.br",
      "topoleiloes.com.br",
      "vizeuonline.com.br",
      "whleiloes.com.br"
    ]
  },
  
  "PAGINACAO": {
    "description": "Configuração de paginação por site (do mapeamento Fase 1)",
    "sites": {
      "megaleiloes.com.br": {"tipo": "NUMERIC", "total_paginas": 17, "url_pattern": "/imoveis?pagina={page}"},
      "portalzuk.com.br": {"tipo": "NUMERIC", "total_paginas": 10, "url_pattern": "/leilao-de-imoveis?page={page}"},
      "lancejudicial.com.br": {"tipo": "NUMERIC", "total_paginas": 5, "url_pattern": "/leiloes/imoveis?page={page}"},
      "frazaoleiloes.com.br": {"tipo": "INFINITE_SCROLL", "button_selector": "button.ver-mais"},
      "sold.com.br": {"tipo": "NUMERIC", "total_paginas": 3, "url_pattern": "/leiloes/imoveis?page={page}"},
      "gustavoreisleiloes.com.br": {"tipo": "SINGLE_PAGE", "total_paginas": 1}
    }
  }
}
```

---

## 🔧 ETAPA 3: CRIAR EXTRATOR TIER 1 (HTTP SIMPLES)

**Arquivo**: `leilao-backend/scripts/extractors/extrator_tier1_http.py`

```python
#!/usr/bin/env python3
"""
EXTRATOR TIER 1: HTTP Simples
Para sites que funcionam sem JavaScript ou proteção anti-bot
"""

import asyncio
import httpx
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import logging

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
```

---

## 🔧 ETAPA 4: CRIAR EXTRATOR TIER 2 (PLAYWRIGHT STEALTH)

**Arquivo**: `leilao-backend/scripts/extractors/extrator_tier2_stealth.py`

```python
#!/usr/bin/env python3
"""
EXTRATOR TIER 2: Playwright com Stealth
Para sites com CloudFlare ou proteção anti-bot básica
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Browser, Page
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("logs/extracao_fase2/tier2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ExtratorTier2:
    """Extrator Playwright com técnicas de stealth."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.resultados: List[Dict] = []
        self.falhas: List[Dict] = []
        self.promocoes_tier3: List[str] = []  # Sites que falharam e devem ir para TIER 3
        
    async def setup_browser(self):
        """Configura browser com stealth."""
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--disable-web-security',
            ]
        )
        
    async def criar_contexto_stealth(self):
        """Cria contexto com configurações de stealth."""
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            extra_http_headers={
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
        )
        
        # Script de stealth
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            delete navigator.__proto__.webdriver;
            
            window.chrome = { runtime: {} };
            
            Object.defineProperty(navigator, 'plugins', { 
                get: () => [1, 2, 3, 4, 5] 
            });
            
            Object.defineProperty(navigator, 'languages', { 
                get: () => ['pt-BR', 'pt', 'en-US', 'en'] 
            });
            
            Object.defineProperty(navigator, 'platform', { 
                get: () => 'Win32' 
            });
            
            Object.defineProperty(navigator, 'hardwareConcurrency', { 
                get: () => 8 
            });
        """)
        
        return context
        
    async def extrair_site(self, dominio: str, config_paginacao: Optional[Dict] = None) -> Dict:
        """Extrai imóveis de um site usando Playwright Stealth."""
        
        url_base = f"https://www.{dominio}"
        logger.info(f"🔍 Extraindo (Stealth): {dominio}")
        
        resultado = {
            "dominio": dominio,
            "url_base": url_base,
            "timestamp": datetime.now().isoformat(),
            "tier": "TIER_2_STEALTH",
            "sucesso": False,
            "imoveis": [],
            "total_imoveis": 0,
            "paginas_processadas": 0,
            "bloqueio_detectado": None,
            "erro": None
        }
        
        context = None
        page = None
        
        try:
            context = await self.criar_contexto_stealth()
            page = await context.new_page()
            
            # Determinar URL de imóveis
            url_imoveis = self._construir_url_imoveis(url_base, dominio)
            
            # Navegar
            response = await page.goto(url_imoveis, wait_until='domcontentloaded', timeout=45000)
            await asyncio.sleep(3)
            
            # Verificar bloqueios
            content = await page.content()
            bloqueio = self._detectar_bloqueio(content)
            
            if bloqueio:
                resultado["bloqueio_detectado"] = bloqueio
                logger.warning(f"   ⚠️ Bloqueio detectado: {bloqueio}")
                
                # Se for CloudFlare forte, marcar para TIER 3
                if "CLOUDFLARE" in bloqueio:
                    self.promocoes_tier3.append(dominio)
                    resultado["erro"] = f"Promovido para TIER 3: {bloqueio}"
                    return resultado
            
            # Scroll para carregar conteúdo
            await self._scroll_pagina(page)
            
            # Extrair imóveis
            imoveis = await self._extrair_imoveis_pagina(page, url_imoveis)
            resultado["imoveis"].extend(imoveis)
            resultado["paginas_processadas"] = 1
            
            # Processar paginação se configurada
            if config_paginacao and config_paginacao.get("tipo") == "INFINITE_SCROLL":
                imoveis_extras = await self._processar_infinite_scroll(page, config_paginacao)
                resultado["imoveis"].extend(imoveis_extras)
            elif config_paginacao and config_paginacao.get("tipo") == "NUMERIC":
                imoveis_extras = await self._processar_paginacao_numerica(page, url_base, config_paginacao)
                resultado["imoveis"].extend(imoveis_extras)
                resultado["paginas_processadas"] = config_paginacao.get("total_paginas", 1)
            
            resultado["total_imoveis"] = len(resultado["imoveis"])
            resultado["sucesso"] = resultado["total_imoveis"] > 0
            
        except Exception as e:
            resultado["erro"] = str(e)[:200]
            logger.error(f"   ❌ Erro: {e}")
            
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
        
        return resultado
    
    def _construir_url_imoveis(self, url_base: str, dominio: str) -> str:
        """Constrói URL da página de imóveis."""
        
        # URLs conhecidas
        urls_conhecidas = {
            "frazaoleiloes.com.br": "/sale/searchLot?&categoria=Imóveis&pesquisaSimples=false",
            "sold.com.br": "/leiloes/imoveis",
            "megaleiloes.com.br": "/imoveis",
            "portalzuk.com.br": "/leilao-de-imoveis",
        }
        
        if dominio in urls_conhecidas:
            return url_base + urls_conhecidas[dominio]
        
        # Tentar path comum
        return url_base + "/imoveis"
    
    def _detectar_bloqueio(self, content: str) -> Optional[str]:
        """Detecta tipo de bloqueio na página."""
        
        content_lower = content.lower()
        
        if 'cloudflare' in content_lower and ('challenge' in content_lower or 'ray id' in content_lower):
            return "CLOUDFLARE_CHALLENGE"
        elif 'captcha' in content_lower or 'recaptcha' in content_lower:
            return "CAPTCHA"
        elif 'blocked' in content_lower or 'denied' in content_lower:
            return "WAF_BLOCKED"
        elif 'navegador incompatível' in content_lower:
            return "BROWSER_CHECK"
        elif len(content) < 1000:
            return "PAGINA_VAZIA"
        
        return None
    
    async def _scroll_pagina(self, page: Page):
        """Faz scroll para carregar conteúdo lazy."""
        
        try:
            await page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 500;
                        const maxScroll = 10000;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= maxScroll) {
                                clearInterval(timer);
                                window.scrollTo(0, 0);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            await asyncio.sleep(2)
        except:
            pass
    
    async def _extrair_imoveis_pagina(self, page: Page, url_origem: str) -> List[Dict]:
        """Extrai imóveis da página atual."""
        
        imoveis = []
        
        # Seletores para links de imóveis
        seletores = [
            'a[href*="/imovel/"]',
            'a[href*="/lote/"]',
            'a[href*="/detalhes/"]',
            'a[href*="/item/"]',
            '.property-card a',
            '.imovel-card a',
        ]
        
        for seletor in seletores:
            try:
                elementos = await page.query_selector_all(seletor)
                
                for elem in elementos:
                    try:
                        href = await elem.get_attribute('href')
                        texto = await elem.inner_text()
                        
                        if href and '/imovel' in href or '/lote' in href:
                            imovel = {
                                "url": href if href.startswith('http') else f"https://{url_origem.split('//')[1].split('/')[0]}{href}",
                                "texto_card": texto[:500] if texto else None,
                                "url_origem": url_origem,
                                "extraido_em": datetime.now().isoformat(),
                            }
                            
                            # Extrair preço do texto
                            preco_match = re.search(r'R\$\s*([\d.,]+)', texto or '')
                            if preco_match:
                                preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                                try:
                                    imovel["preco"] = float(preco_str)
                                except:
                                    pass
                            
                            imoveis.append(imovel)
                            
                    except Exception as e:
                        logger.debug(f"Erro ao extrair elemento: {e}")
                
                if imoveis:
                    break
                    
            except Exception as e:
                logger.debug(f"Erro com seletor {seletor}: {e}")
        
        # Remover duplicatas
        urls_vistas = set()
        imoveis_unicos = []
        for imovel in imoveis:
            if imovel["url"] not in urls_vistas:
                urls_vistas.add(imovel["url"])
                imoveis_unicos.append(imovel)
        
        return imoveis_unicos
    
    async def _processar_infinite_scroll(self, page: Page, config: Dict) -> List[Dict]:
        """Processa sites com scroll infinito / botão Ver Mais."""
        
        imoveis_extras = []
        button_selector = config.get("button_selector", "button:has-text('Ver Mais')")
        max_cliques = 20
        
        for i in range(max_cliques):
            try:
                # Tentar clicar no botão
                button = await page.query_selector(button_selector)
                if not button:
                    break
                
                await button.click()
                await asyncio.sleep(2)
                
                # Extrair novos imóveis
                novos = await self._extrair_imoveis_pagina(page, page.url)
                
                if not novos:
                    break
                
                imoveis_extras.extend(novos)
                logger.info(f"      Clique {i+1}: +{len(novos)} imóveis")
                
            except:
                break
        
        return imoveis_extras
    
    async def _processar_paginacao_numerica(self, page: Page, url_base: str, config: Dict) -> List[Dict]:
        """Processa sites com paginação numérica."""
        
        imoveis_extras = []
        pattern = config.get("url_pattern", "/imoveis?page={page}")
        total_paginas = config.get("total_paginas", 5)
        
        # Começar da página 2 (página 1 já foi processada)
        for num_pagina in range(2, total_paginas + 1):
            try:
                url = url_base + pattern.format(page=num_pagina)
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                
                novos = await self._extrair_imoveis_pagina(page, url)
                imoveis_extras.extend(novos)
                
                logger.info(f"      Página {num_pagina}: +{len(novos)} imóveis")
                
            except Exception as e:
                logger.warning(f"      Erro na página {num_pagina}: {e}")
                break
        
        return imoveis_extras
    
    async def processar_lista(self, dominios: List[str], config_paginacao: Dict = None):
        """Processa lista de domínios."""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 TIER 2: Processando {len(dominios)} sites com Playwright Stealth")
        logger.info(f"{'='*60}\n")
        
        await self.setup_browser()
        
        try:
            for i, dominio in enumerate(dominios, 1):
                logger.info(f"\n[{i}/{len(dominios)}] {'-'*40}")
                
                config = config_paginacao.get(dominio) if config_paginacao else None
                resultado = await self.extrair_site(dominio, config)
                
                if resultado["sucesso"]:
                    self.resultados.append(resultado)
                    logger.info(f"   ✅ Sucesso: {resultado['total_imoveis']} imóveis")
                else:
                    self.falhas.append(resultado)
                    logger.warning(f"   ⚠️ Falha: {resultado.get('erro', 'Nenhum imóvel')}")
                
                await asyncio.sleep(3)
                
        finally:
            if self.browser:
                await self.browser.close()
        
        # Salvar resultados
        await self._salvar_resultados()
    
    async def _salvar_resultados(self):
        """Salva resultados."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON completo
        json_file = OUTPUT_DIR / f"tier2_resultados_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "tier": "TIER_2_STEALTH",
                "timestamp": datetime.now().isoformat(),
                "total_sites": len(self.resultados) + len(self.falhas),
                "sucesso": len(self.resultados),
                "falhas": len(self.falhas),
                "promocoes_tier3": self.promocoes_tier3,
                "total_imoveis": sum(r["total_imoveis"] for r in self.resultados),
                "resultados": self.resultados,
                "falhas_detalhes": self.falhas
            }, f, ensure_ascii=False, indent=2)
        
        # Lista de promoções para TIER 3
        if self.promocoes_tier3:
            promo_file = OUTPUT_DIR / f"promocoes_tier3_{timestamp}.json"
            with open(promo_file, 'w', encoding='utf-8') as f:
                json.dump(self.promocoes_tier3, f, ensure_ascii=False, indent=2)
            logger.info(f"\n⚠️ {len(self.promocoes_tier3)} sites promovidos para TIER 3")
        
        logger.info(f"\n📁 Resultados salvos em: {OUTPUT_DIR}")


async def main():
    """Função principal."""
    
    config_path = Path("config/roteamento_sites.json")
    
    if not config_path.exists():
        logger.error(f"❌ Arquivo de roteamento não encontrado: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    sites_tier2 = config.get("TIER_2_STEALTH", {}).get("sites", [])
    config_paginacao = config.get("PAGINACAO", {}).get("sites", {})
    
    logger.info(f"📋 Sites TIER 2 carregados: {len(sites_tier2)}")
    
    extrator = ExtratorTier2()
    await extrator.processar_lista(sites_tier2, config_paginacao)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔧 ETAPA 5: CRIAR EXTRATOR TIER 3 (SCRAPINGBEE)

**Arquivo**: `leilao-backend/scripts/extractors/extrator_tier3_scrapingbee.py`

```python
#!/usr/bin/env python3
"""
EXTRATOR TIER 3: ScrapingBee
Para sites com CloudFlare forte ou proteção avançada
Usa ScrapingBee API diretamente (sem tentar outros métodos)
"""

import asyncio
import httpx
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("logs/extracao_fase2/tier3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")


class ExtratorTier3:
    """Extrator usando ScrapingBee para sites difíceis."""
    
    def __init__(self):
        if not SCRAPINGBEE_API_KEY:
            raise ValueError("SCRAPINGBEE_API_KEY não configurada no .env")
        
        self.api_key = SCRAPINGBEE_API_KEY
        self.api_url = "https://app.scrapingbee.com/api/v1/"
        self.resultados: List[Dict] = []
        self.falhas: List[Dict] = []
        self.creditos_usados = 0
        
    async def extrair_site(self, dominio: str, config_paginacao: Optional[Dict] = None) -> Dict:
        """Extrai imóveis usando ScrapingBee."""
        
        url_base = f"https://www.{dominio}"
        url_imoveis = self._construir_url_imoveis(url_base, dominio)
        
        logger.info(f"🔍 Extraindo (ScrapingBee): {dominio}")
        
        resultado = {
            "dominio": dominio,
            "url_base": url_base,
            "timestamp": datetime.now().isoformat(),
            "tier": "TIER_3_SCRAPINGBEE",
            "sucesso": False,
            "imoveis": [],
            "total_imoveis": 0,
            "creditos_usados": 0,
            "erro": None
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                
                # Parâmetros do ScrapingBee
                params = {
                    "api_key": self.api_key,
                    "url": url_imoveis,
                    "render_js": "true",           # Renderizar JavaScript
                    "premium_proxy": "true",       # Proxy premium (bypassa CloudFlare)
                    "country_code": "br",          # IP brasileiro
                    "wait": "5000",                # Esperar 5s para JS carregar
                    "block_ads": "true",           # Bloquear ads
                }
                
                response = await client.get(self.api_url, params=params)
                
                # Contabilizar créditos (premium_proxy = 10-25 créditos)
                self.creditos_usados += 25
                resultado["creditos_usados"] = 25
                
                if response.status_code == 200:
                    html = response.text
                    
                    # Extrair imóveis do HTML
                    imoveis = self._extrair_imoveis_html(html, url_imoveis)
                    resultado["imoveis"] = imoveis
                    resultado["total_imoveis"] = len(imoveis)
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
        """Constrói URL da página de imóveis."""
        
        urls_conhecidas = {
            "leje.com.br": "/leiloes/imoveis",
            "biasileiloes.com.br": "/imoveis",
            "milanleiloes.com.br": "/leiloes",
            "leiloes.com.br": "/imoveis",
        }
        
        if dominio in urls_conhecidas:
            return url_base + urls_conhecidas[dominio]
        
        return url_base + "/imoveis"
    
    def _extrair_imoveis_html(self, html: str, url_origem: str) -> List[Dict]:
        """Extrai imóveis do HTML."""
        
        soup = BeautifulSoup(html, 'html.parser')
        imoveis = []
        
        # Seletores
        seletores = [
            'a[href*="/imovel/"]',
            'a[href*="/lote/"]',
            'a[href*="/detalhes/"]',
            '.property-card',
            '.imovel-card',
        ]
        
        for seletor in seletores:
            cards = soup.select(seletor)
            if cards:
                for card in cards:
                    imovel = self._extrair_dados_card(card, url_origem)
                    if imovel:
                        imoveis.append(imovel)
                break
        
        # Remover duplicatas
        urls_vistas = set()
        imoveis_unicos = []
        for imovel in imoveis:
            url = imovel.get("url", "")
            if url and url not in urls_vistas:
                urls_vistas.add(url)
                imoveis_unicos.append(imovel)
        
        return imoveis_unicos
    
    def _extrair_dados_card(self, card, url_origem: str) -> Optional[Dict]:
        """Extrai dados de um card."""
        
        dados = {
            "url_origem": url_origem,
            "extraido_em": datetime.now().isoformat(),
            "tier": "TIER_3_SCRAPINGBEE"
        }
        
        # URL
        if card.name == 'a':
            href = card.get('href', '')
        else:
            link = card.find('a')
            href = link.get('href', '') if link else ''
        
        if href:
            if not href.startswith('http'):
                from urllib.parse import urljoin
                href = urljoin(url_origem, href)
            dados["url"] = href
        else:
            return None
        
        # Texto
        texto = card.get_text(strip=True)
        dados["texto_card"] = texto[:500] if texto else None
        
        # Preço
        preco_match = re.search(r'R\$\s*([\d.,]+)', texto or '')
        if preco_match:
            preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
            try:
                dados["preco"] = float(preco_str)
            except:
                pass
        
        return dados
    
    async def processar_lista(self, dominios: List[str], config_paginacao: Dict = None):
        """Processa lista de domínios."""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 TIER 3: Processando {len(dominios)} sites com ScrapingBee")
        logger.info(f"⚠️ Estimativa de créditos: {len(dominios) * 25}")
        logger.info(f"{'='*60}\n")
        
        for i, dominio in enumerate(dominios, 1):
            logger.info(f"\n[{i}/{len(dominios)}] {'-'*40}")
            
            config = config_paginacao.get(dominio) if config_paginacao else None
            resultado = await self.extrair_site(dominio, config)
            
            if resultado["sucesso"]:
                self.resultados.append(resultado)
            else:
                self.falhas.append(resultado)
            
            # Pausa para não sobrecarregar API
            await asyncio.sleep(2)
        
        await self._salvar_resultados()
    
    async def _salvar_resultados(self):
        """Salva resultados."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        json_file = OUTPUT_DIR / f"tier3_resultados_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "tier": "TIER_3_SCRAPINGBEE",
                "timestamp": datetime.now().isoformat(),
                "total_sites": len(self.resultados) + len(self.falhas),
                "sucesso": len(self.resultados),
                "falhas": len(self.falhas),
                "creditos_totais_usados": self.creditos_usados,
                "total_imoveis": sum(r["total_imoveis"] for r in self.resultados),
                "resultados": self.resultados,
                "falhas_detalhes": self.falhas
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📁 Resultados salvos: {json_file}")
        logger.info(f"💰 Créditos ScrapingBee usados: {self.creditos_usados}")


async def main():
    """Função principal."""
    
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
```

---

## 🔧 ETAPA 6: CRIAR ORQUESTRADOR PRINCIPAL

**Arquivo**: `leilao-backend/scripts/executar_fase2_completa.py`

```python
#!/usr/bin/env python3
"""
ORQUESTRADOR FASE 2: Executa extração em 3 tiers
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def executar_tier(tier: int, script_name: str):
    """Executa script de um tier."""
    
    logger.info(f"\n{'='*70}")
    logger.info(f"🚀 EXECUTANDO TIER {tier}")
    logger.info(f"{'='*70}\n")
    
    script_path = Path(f"scripts/extractors/{script_name}")
    
    if not script_path.exists():
        logger.error(f"❌ Script não encontrado: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=7200  # 2 horas timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✅ TIER {tier} completado com sucesso")
            return True
        else:
            logger.error(f"❌ TIER {tier} falhou: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ TIER {tier} timeout (2h)")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao executar TIER {tier}: {e}")
        return False


async def consolidar_resultados():
    """Consolida resultados de todos os tiers."""
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 CONSOLIDANDO RESULTADOS")
    logger.info(f"{'='*70}\n")
    
    todos_imoveis = []
    estatisticas = {
        "timestamp": datetime.now().isoformat(),
        "tiers": {}
    }
    
    # Processar cada tier
    for tier in [1, 2, 3]:
        tier_dir = Path(f"logs/extracao_fase2/tier{tier}")
        
        if not tier_dir.exists():
            continue
        
        # Encontrar arquivo mais recente
        arquivos = list(tier_dir.glob(f"tier{tier}_resultados_*.json"))
        
        if not arquivos:
            continue
        
        arquivo_recente = max(arquivos, key=lambda x: x.stat().st_mtime)
        
        with open(arquivo_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        estatisticas["tiers"][f"tier_{tier}"] = {
            "sucesso": dados.get("sucesso", 0),
            "falhas": dados.get("falhas", 0),
            "total_imoveis": dados.get("total_imoveis", 0)
        }
        
        # Extrair imóveis
        for resultado in dados.get("resultados", []):
            todos_imoveis.extend(resultado.get("imoveis", []))
    
    # Salvar consolidado
    output_dir = Path("logs/extracao_fase2")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Estatísticas
    estatisticas["total_imoveis"] = len(todos_imoveis)
    estatisticas_file = output_dir / f"estatisticas_consolidadas_{timestamp}.json"
    with open(estatisticas_file, 'w', encoding='utf-8') as f:
        json.dump(estatisticas, f, ensure_ascii=False, indent=2)
    
    # Todos os imóveis
    imoveis_file = output_dir / f"todos_imoveis_{timestamp}.json"
    with open(imoveis_file, 'w', encoding='utf-8') as f:
        json.dump(todos_imoveis, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📊 RESUMO FINAL:")
    logger.info(f"   Total de imóveis extraídos: {len(todos_imoveis)}")
    
    for tier, stats in estatisticas.get("tiers", {}).items():
        logger.info(f"   {tier}: {stats['total_imoveis']} imóveis de {stats['sucesso']} sites")
    
    logger.info(f"\n📁 Arquivos salvos:")
    logger.info(f"   {estatisticas_file}")
    logger.info(f"   {imoveis_file}")
    
    return todos_imoveis


async def main():
    """Executa Fase 2 completa."""
    
    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 FASE 2: EXTRAÇÃO INTELIGENTE COM ROTEAMENTO")
    logger.info(f"{'='*70}")
    logger.info(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*70}\n")
    
    inicio = datetime.now()
    
    # Executar Tier 1 (HTTP simples)
    await executar_tier(1, "extrator_tier1_http.py")
    
    # Executar Tier 2 (Playwright Stealth)
    await executar_tier(2, "extrator_tier2_stealth.py")
    
    # Executar Tier 3 (ScrapingBee)
    await executar_tier(3, "extrator_tier3_scrapingbee.py")
    
    # Consolidar resultados
    todos_imoveis = await consolidar_resultados()
    
    fim = datetime.now()
    duracao = fim - inicio
    
    logger.info(f"\n{'='*70}")
    logger.info(f"🎉 FASE 2 COMPLETA!")
    logger.info(f"{'='*70}")
    logger.info(f"Duração: {duracao}")
    logger.info(f"Total de imóveis: {len(todos_imoveis)}")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔧 ETAPA 7: EXECUTAR

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# 1. Criar arquivo de roteamento
# (copiar o JSON da Etapa 2 para config/roteamento_sites.json)

# 2. Executar Fase 2 completa
python scripts/executar_fase2_completa.py

# OU executar tiers individualmente:
python scripts/extractors/extrator_tier1_http.py
python scripts/extractors/extrator_tier2_stealth.py
python scripts/extractors/extrator_tier3_scrapingbee.py
```

---

## 📊 RESULTADOS ESPERADOS

| Tier | Sites | Imóveis Estimados | Tempo |
|------|-------|-------------------|-------|
| TIER 1 | 146 | 5.000-8.000 | ~1h |
| TIER 2 | 85 | 3.000-5.000 | ~2h |
| TIER 3 | 25 | 1.000-2.000 | ~30min |
| **TOTAL** | **256** | **9.000-15.000** | **~4h** |

---

## ✅ CRITÉRIOS DE SUCESSO

1. ✅ Sites TIER 1 extraídos com HTTP simples
2. ✅ Sites TIER 2 extraídos com Playwright Stealth
3. ✅ Sites TIER 3 extraídos com ScrapingBee
4. ✅ Créditos ScrapingBee economizados (só ~25 sites)
5. ✅ Resultados consolidados em JSON
6. ✅ Mecanismo de promoção de tier funcionando

---

## 🔄 MANUTENÇÃO DO ROTEAMENTO

Se um site mudar de comportamento:

```python
# Promover de TIER 1 para TIER 2
mover_site("dominio.com.br", "TIER_1_HTTP", "TIER_2_STEALTH")

# Promover de TIER 2 para TIER 3
mover_site("dominio.com.br", "TIER_2_STEALTH", "TIER_3_SCRAPINGBEE")
```

---

**FIM DA TAREFA FASE 2**
