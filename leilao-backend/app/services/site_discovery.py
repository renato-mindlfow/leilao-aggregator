"""
Site Discovery Service
Analisa a estrutura de sites de leiloeiros para descobrir como extrair imóveis.
"""

import json
import logging
import os
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)

class SiteDiscoveryService:
    """Serviço para descobrir estrutura de sites de leiloeiros"""
    
    DISCOVERY_PROMPT = """Analise esta página HTML de um site de leilões de imóveis brasileiro.

Sua tarefa é descobrir a ESTRUTURA do site para extração automatizada de imóveis.

Identifique:

1. **FILTROS DE IMÓVEIS**: O site tem filtros/categorias para tipos de imóveis?
   - Procure por: links/botões como "Apartamento", "Casa", "Terreno", "Comercial", "Rural"
   - Procure por: menus dropdown, checkboxes, sidebar com categorias
   - Extraia a URL de cada filtro (href dos links)

2. **LISTA DE IMÓVEIS**: Onde os imóveis são listados?
   - Procure por: grid de cards, lista de itens, galeria
   - Identifique o seletor CSS da lista

3. **PAGINAÇÃO**: Como funciona a paginação?
   - Procure por: botões "Próxima", números de página, "Carregar mais"
   - Identifique o padrão de URL (?page=2, ?pagina=2, /page/2)

4. **DETALHES DO IMÓVEL**: Como acessar detalhes?
   - Procure por: links "Ver mais", "Detalhes", "Ver lote"
   - Identifique o padrão de URL dos detalhes

Responda APENAS com JSON válido no formato:

{
  "site_type": "filter_based|list_based|api_based|unknown",
  "property_filters": [
    {"name": "Nome do Filtro", "url": "/url-relativa-ou-absoluta", "selector": "seletor-css-opcional"}
  ],
  "pagination": {
    "type": "query_param|path_segment|load_more|none",
    "param": "page",
    "pattern": "?page={n}",
    "next_selector": ".paginacao .next"
  },
  "property_list_selector": ".lista-imoveis .item",
  "property_link_selector": "a.detalhes",
  "fallback_url": "/imoveis",
  "requires_js": false,
  "notes": "Observações sobre o site"
}

Se não encontrar filtros específicos para imóveis, retorne site_type="list_based" e coloque a melhor URL em fallback_url.

HTML para analisar:
"""

    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.jina_enabled = True
    
    async def discover_site_structure(self, auctioneer: Dict) -> Dict[str, Any]:
        """
        Descobre a estrutura de um site de leiloeiro.
        
        Args:
            auctioneer: Dict com id, name, website
            
        Returns:
            Dict com configuração descoberta ou erro
        """
        website = auctioneer.get("website", "").rstrip("/")
        name = auctioneer.get("name", "Unknown")
        
        logger.info(f"🔍 Iniciando descoberta de estrutura: {name} ({website})")
        
        try:
            # 1. Baixar homepage
            html = await self._fetch_homepage(website)
            if not html or len(html) < 1000:
                return {"success": False, "error": "Não foi possível acessar o site"}
            
            # 2. Analisar com IA
            config = await self._analyze_with_ai(html, website)
            if not config:
                return {"success": False, "error": "IA não conseguiu analisar o site"}
            
            # 3. Validar e enriquecer configuração
            config = self._enrich_config(config, website, html)
            
            # 4. Testar configuração (opcional - verificar se URLs funcionam)
            config = await self._validate_config(config, website)
            
            logger.info(f"✅ Descoberta concluída para {name}: {config.get('site_type')}")
            
            return {
                "success": True,
                "config": config
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na descoberta de {name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _fetch_homepage(self, website: str) -> Optional[str]:
        """Baixa a homepage do site"""
        
        # Tentar fetch direto primeiro
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(website, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                if response.status_code == 200 and len(response.text) > 1000:
                    logger.info(f"Homepage obtida via fetch direto: {len(response.text)} chars")
                    return response.text
        except Exception as e:
            logger.warning(f"Fetch direto falhou: {e}")
        
        # Fallback para Jina
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                jina_url = f"https://r.jina.ai/{website}"
                response = await client.get(jina_url, headers={"X-Return-Format": "html"})
                if response.status_code == 200:
                    logger.info(f"Homepage obtida via Jina: {len(response.text)} chars")
                    return response.text
        except Exception as e:
            logger.warning(f"Jina falhou: {e}")
        
        return None
    
    async def _analyze_with_ai(self, html: str, website: str) -> Optional[Dict]:
        """Usa OpenAI para analisar a estrutura do site"""
        
        # Limitar tamanho do HTML para não estourar contexto
        html_truncated = html[:50000] if len(html) > 50000 else html
        
        prompt = self.DISCOVERY_PROMPT + f"\n\nURL base: {website}\n\n" + html_truncated
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": "Você é um especialista em web scraping. Analise sites e retorne APENAS JSON válido, sem explicações."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI retornou {response.status_code}")
                    return None
                
                result = response.json()
                
                # Validar resposta
                if not result or "choices" not in result or len(result["choices"]) == 0:
                    logger.error("Resposta vazia da OpenAI")
                    return None
                
                content = result["choices"][0].get("message", {}).get("content", "")
                if not content:
                    logger.error("Content vazio na resposta")
                    return None
                
                # Limpar e parsear JSON
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                config = json.loads(content)
                logger.info(f"IA descobriu estrutura: {config.get('site_type')}")
                return config
                
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON da IA: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro na análise com IA: {e}")
            return None
    
    def _enrich_config(self, config: Dict, website: str, html: str = None) -> Dict:
        """Enriquece a configuração com metadados e hash de estrutura"""
        
        config["version"] = "1.0"
        config["discovered_at"] = datetime.utcnow().isoformat() + "Z"
        config["base_url"] = website
        
        # Calcular data de expiração (30 dias padrão)
        config["expires_at"] = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
        
        # Calcular hash da estrutura se HTML disponível
        if html:
            structure = self._extract_structure_signature(html)
            config["validation"] = {
                "structure_hash": hashlib.md5(structure.encode()).hexdigest(),
                "last_validated_at": datetime.utcnow().isoformat() + "Z",
                "consecutive_failures": 0,
                "total_extractions": 0,
                "successful_extractions": 0
            }
        
        # Garantir que URLs dos filtros são absolutas
        if "property_filters" in config:
            for f in config["property_filters"]:
                if f.get("url") and not f["url"].startswith("http"):
                    f["url"] = website.rstrip("/") + "/" + f["url"].lstrip("/")
        
        # Garantir fallback_url absoluta
        if config.get("fallback_url") and not config["fallback_url"].startswith("http"):
            config["fallback_url"] = website.rstrip("/") + "/" + config["fallback_url"].lstrip("/")
        
        return config
    
    def _extract_structure_signature(self, html: str) -> str:
        """Extrai assinatura da estrutura para hash"""
        
        nav_links = re.findall(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>', html, re.IGNORECASE)
        
        relevant_patterns = ['imovel', 'imoveis', 'lote', 'lotes', 'busca', 'catalogo', 
                           'categoria', 'filtro', 'tipo', 'apartamento', 'casa', 'terreno']
        
        relevant_links = [link for link in nav_links 
                         if any(p in link.lower() for p in relevant_patterns)]
        
        main_classes = re.findall(r'class=["\']([^"\']*(?:lista|grid|cards|imoveis|lotes)[^"\']*)["\']', 
                                  html, re.IGNORECASE)
        
        signature = "|".join(sorted(set(relevant_links[:50]))) + "||" + "|".join(sorted(set(main_classes[:20])))
        
        return signature
    
    async def _validate_config(self, config: Dict, website: str) -> Dict:
        """Valida se as URLs descobertas funcionam"""
        
        validated_filters = []
        
        if "property_filters" in config:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                for f in config["property_filters"]:
                    url = f.get("url")
                    if not url:
                        continue
                    
                    try:
                        response = await client.head(url, headers={
                            "User-Agent": "Mozilla/5.0"
                        })
                        if response.status_code in [200, 301, 302]:
                            f["validated"] = True
                            validated_filters.append(f)
                            logger.debug(f"✓ Filtro validado: {f['name']}")
                        else:
                            logger.debug(f"✗ Filtro inválido ({response.status_code}): {f['name']}")
                    except:
                        logger.debug(f"✗ Filtro inacessível: {f['name']}")
        
            config["property_filters"] = validated_filters
        
        config["validated_at"] = datetime.utcnow().isoformat() + "Z"
        return config


# Instância global
site_discovery = SiteDiscoveryService()

