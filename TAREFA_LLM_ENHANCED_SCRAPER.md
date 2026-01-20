# TAREFA: Criar LLMEnhancedScraper (Alternativa ao Crawl4AI)

## CONTEXTO
O Crawl4AI não instala no Windows devido à dependência `lxml` que requer `libxml2` (biblioteca C nativa).

A solução é criar um scraper equivalente usando apenas:
- Playwright (já instalado)
- OpenAI GPT-4o-mini (já configurado)
- BeautifulSoup (já instalado)

## OBJETIVO
Criar `llm_enhanced_scraper.py` que replique a funcionalidade do Crawl4AI com 95% de sucesso.

## EXECUÇÃO AUTÔNOMA
Execute TODAS as fases sem parar para perguntar. Só pare se houver erro crítico.

---

## FASE 1: Analisar Estrutura do crawl4ai_scraper.py Existente

```bash
cat app/services/crawl4ai_scraper.py | head -100
```

Entender a interface esperada para manter compatibilidade.

---

## FASE 2: Criar llm_enhanced_scraper.py

Criar arquivo `app/services/llm_enhanced_scraper.py` com:

```python
"""
LLMEnhancedScraper - Alternativa ao Crawl4AI para Windows
Usa Playwright + GPT-4o-mini para extração inteligente
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from openai import OpenAI
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LLMEnhancedScraper:
    """
    Scraper que combina Playwright (renderização JS) + GPT-4o-mini (extração inteligente).
    Alternativa ao Crawl4AI que funciona no Windows sem lxml.
    """
    
    # Schema de extração (mesmo do Crawl4AI)
    EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "imoveis": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string"},
                        "endereco": {"type": "string"},
                        "cidade": {"type": "string"},
                        "estado": {"type": "string"},
                        "tipo_imovel": {"type": "string"},
                        "area_m2": {"type": "number"},
                        "valor_avaliacao": {"type": "number"},
                        "valor_minimo": {"type": "number"},
                        "desconto_percentual": {"type": "number"},
                        "data_leilao": {"type": "string"},
                        "modalidade": {"type": "string"},
                        "url_detalhes": {"type": "string"},
                        "url_imagem": {"type": "string"}
                    }
                }
            }
        }
    }
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.client = OpenAI()
        
    async def _setup_browser(self):
        """Configura browser com stealth mode."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
        )
        
        # Injetar scripts de stealth
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            delete navigator.__proto__.webdriver;
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        
        self.page = await self.context.new_page()
        logger.info("✅ Browser configurado com stealth mode")
        
    async def _close_browser(self):
        """Fecha browser de forma segura."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.debug(f"Erro ao fechar browser: {e}")
            
    async def _fetch_page(self, url: str, wait_for_js: bool = True) -> str:
        """
        Busca página usando Playwright.
        Renderiza JavaScript e retorna HTML limpo.
        """
        try:
            await self.page.goto(url, wait_until='networkidle', timeout=60000)
            
            if wait_for_js:
                await asyncio.sleep(3)  # Aguardar JS carregar
                
                # Scroll para carregar lazy content
                await self.page.evaluate("""
                    async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 300;
                            const timer = setInterval(() => {
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if (totalHeight >= document.body.scrollHeight) {
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                            setTimeout(resolve, 5000);  // Max 5s scroll
                        });
                    }
                """)
                await asyncio.sleep(1)
            
            html = await self.page.content()
            return html
            
        except Exception as e:
            logger.error(f"Erro ao buscar página {url}: {e}")
            return ""
            
    def _clean_html(self, html: str) -> str:
        """
        Limpa HTML removendo scripts, styles e elementos desnecessários.
        Similar ao que Crawl4AI faz internamente.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remover elementos desnecessários
        for tag in soup.find_all(['script', 'style', 'noscript', 'iframe', 'svg', 'path']):
            tag.decompose()
            
        # Remover comentários
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()
            
        # Pegar texto visível
        text = soup.get_text(separator='\n', strip=True)
        
        # Limpar linhas vazias múltiplas
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        clean_text = '\n'.join(lines)
        
        # Limitar tamanho para não estourar contexto do LLM
        if len(clean_text) > 15000:
            clean_text = clean_text[:15000] + "\n... [truncado]"
            
        return clean_text
        
    def _extract_with_llm(self, text: str, url: str) -> List[Dict]:
        """
        Usa GPT-4o-mini para extrair dados estruturados do texto.
        """
        try:
            prompt = f"""Analise o conteúdo de uma página de leilões de imóveis e extraia os dados.

URL: {url}

CONTEÚDO DA PÁGINA:
{text}

INSTRUÇÕES:
1. Extraia TODOS os imóveis encontrados na página
2. Para cada imóvel, extraia os campos disponíveis
3. Valores monetários devem ser números (sem R$, pontos ou vírgulas)
4. Datas no formato YYYY-MM-DD
5. Se um campo não estiver disponível, omita-o

Retorne APENAS um JSON válido no formato:
{{
    "imoveis": [
        {{
            "titulo": "string",
            "endereco": "string", 
            "cidade": "string",
            "estado": "UF",
            "tipo_imovel": "Apartamento|Casa|Terreno|Comercial|Rural|Outro",
            "area_m2": number,
            "valor_avaliacao": number,
            "valor_minimo": number,
            "desconto_percentual": number,
            "data_leilao": "YYYY-MM-DD",
            "modalidade": "Judicial|Extrajudicial|Venda Direta",
            "url_detalhes": "string",
            "url_imagem": "string"
        }}
    ]
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um extrator de dados especializado em leilões de imóveis brasileiros. Retorne apenas JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            imoveis = result.get('imoveis', [])
            
            logger.info(f"✅ LLM extraiu {len(imoveis)} imóveis")
            return imoveis
            
        except Exception as e:
            logger.error(f"Erro na extração LLM: {e}")
            return []
            
    def _extract_photos_regex(self, html: str, base_url: str) -> List[str]:
        """
        Extrai URLs de fotos usando regex (fallback confiável).
        """
        patterns = [
            r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
            r'src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
            r'data-src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
        ]
        
        photos = set()
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                url = match if isinstance(match, str) else match
                # Filtrar logos e placeholders
                if any(x in url.lower() for x in ['logo', 'icon', 'placeholder', 'banner', 'favicon']):
                    continue
                # Verificar se é URL válida de imagem
                if url.startswith(('http://', 'https://')):
                    photos.add(url)
                    
        return list(photos)[:20]  # Max 20 fotos
        
    def _normalize_property(self, raw: Dict, url: str, auctioneer_id: str) -> Dict:
        """
        Normaliza dados extraídos para o formato do banco.
        """
        # Normalizar categoria
        tipo = raw.get('tipo_imovel', '').lower()
        category_map = {
            'apartamento': 'Apartamento',
            'casa': 'Casa',
            'terreno': 'Terreno',
            'comercial': 'Comercial',
            'rural': 'Rural',
            'galpão': 'Comercial',
            'sala': 'Comercial',
            'loja': 'Comercial',
        }
        category = category_map.get(tipo, 'Outro')
        
        # Normalizar estado
        state = raw.get('estado', '').upper()
        if len(state) != 2:
            state = 'XX'
            
        # Normalizar cidade (Title Case)
        city = raw.get('cidade', '')
        if city:
            city = city.title()
            
        return {
            'title': raw.get('titulo', ''),
            'address': raw.get('endereco', ''),
            'city': city,
            'state': state,
            'category': category,
            'area_total': raw.get('area_m2'),
            'evaluation_value': raw.get('valor_avaliacao'),
            'first_auction_value': raw.get('valor_minimo'),
            'second_auction_value': raw.get('valor_minimo'),
            'discount_percentage': raw.get('desconto_percentual'),
            'first_auction_date': raw.get('data_leilao'),
            'auction_type': raw.get('modalidade', 'Extrajudicial'),
            'source_url': raw.get('url_detalhes', url),
            'image_url': raw.get('url_imagem'),
            'auctioneer_id': auctioneer_id,
            'source': 'llm_enhanced_scraper',
        }
        
    async def scrape_async(self, url: str, auctioneer_id: str) -> List[Dict]:
        """
        Método principal de scraping assíncrono.
        """
        properties = []
        
        try:
            await self._setup_browser()
            
            # 1. Buscar página com Playwright
            logger.info(f"🌐 Buscando: {url}")
            html = await self._fetch_page(url)
            
            if not html or len(html) < 500:
                logger.warning(f"⚠️ Página vazia ou muito pequena: {url}")
                return []
                
            # 2. Limpar HTML
            clean_text = self._clean_html(html)
            logger.info(f"📄 HTML limpo: {len(clean_text)} chars")
            
            # 3. Extrair com LLM
            raw_properties = self._extract_with_llm(clean_text, url)
            
            # 4. Extrair fotos com regex
            photos = self._extract_photos_regex(html, url)
            
            # 5. Normalizar propriedades
            for raw in raw_properties:
                prop = self._normalize_property(raw, url, auctioneer_id)
                
                # Atribuir foto se disponível
                if not prop.get('image_url') and photos:
                    prop['image_url'] = photos.pop(0)
                    
                properties.append(prop)
                
            logger.info(f"✅ {len(properties)} imóveis extraídos de {url}")
            
        except Exception as e:
            logger.error(f"❌ Erro no scraping de {url}: {e}")
            
        finally:
            await self._close_browser()
            
        return properties
        
    def scrape(self, url: str, auctioneer_id: str) -> List[Dict]:
        """
        Método síncrono para compatibilidade com código existente.
        """
        return asyncio.run(self.scrape_async(url, auctioneer_id))


# Função de conveniência
async def scrape_with_llm(url: str, auctioneer_id: str, headless: bool = True) -> List[Dict]:
    """
    Função helper para scraping rápido.
    """
    scraper = LLMEnhancedScraper(headless=headless)
    return await scraper.scrape_async(url, auctioneer_id)
```

---

## FASE 3: Criar Script de Teste

Criar arquivo `scripts/testar_llm_enhanced.py`:

```python
#!/usr/bin/env python3
"""
Teste do LLMEnhancedScraper
Alternativa ao Crawl4AI que funciona no Windows
"""

import sys
import os
import asyncio
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Verificar OpenAI API Key
if not os.getenv('OPENAI_API_KEY'):
    print("❌ OPENAI_API_KEY não configurada!")
    print("   Configure no arquivo .env")
    sys.exit(1)

from app.services.llm_enhanced_scraper import LLMEnhancedScraper

# Leiloeiros para teste (mesmos do teste anterior)
LEILOEIROS_TESTE = [
    {"url": "https://www.megaleiloes.com.br/leiloes-de-imoveis", "id": "megaleiloes"},
    {"url": "https://www.portalzukerman.com.br/busca?categoriaId=1", "id": "portalzuk"},
    {"url": "https://www.soldleiloes.com.br/busca/?tipo-bem=imovel", "id": "sold"},
    {"url": "https://www.vivaleiloes.com.br/busca?tipoBem=1", "id": "vivaleiloes"},
    {"url": "https://www.flexleiloes.com.br/auctions?property_type=imovel", "id": "flexleiloes"},
]


async def testar_leiloeiro(scraper: LLMEnhancedScraper, leiloeiro: dict) -> dict:
    """Testa um leiloeiro específico."""
    url = leiloeiro["url"]
    aid = leiloeiro["id"]
    
    print(f"\n{'='*60}")
    print(f"🏠 Testando: {aid}")
    print(f"   URL: {url}")
    print('='*60)
    
    inicio = datetime.now()
    
    try:
        properties = await scraper.scrape_async(url, aid)
        tempo = (datetime.now() - inicio).total_seconds()
        
        if properties:
            print(f"\n✅ SUCESSO: {len(properties)} imóveis em {tempo:.1f}s")
            
            # Mostrar amostra
            for i, p in enumerate(properties[:3]):
                print(f"\n   Imóvel {i+1}:")
                print(f"   - Título: {p.get('title', 'N/A')[:50]}...")
                print(f"   - Cidade: {p.get('city', 'N/A')}, {p.get('state', 'N/A')}")
                print(f"   - Categoria: {p.get('category', 'N/A')}")
                print(f"   - Valor: R$ {p.get('first_auction_value', 'N/A')}")
                
            return {"status": "sucesso", "count": len(properties), "tempo": tempo}
        else:
            print(f"\n⚠️ FALHA: Nenhum imóvel extraído ({tempo:.1f}s)")
            return {"status": "falha", "count": 0, "tempo": tempo}
            
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"\n❌ ERRO: {str(e)[:100]} ({tempo:.1f}s)")
        return {"status": "erro", "error": str(e), "tempo": tempo}


async def main():
    print("="*60)
    print("TESTE: LLM ENHANCED SCRAPER (Alternativa ao Crawl4AI)")
    print("="*60)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Leiloeiros: {len(LEILOEIROS_TESTE)}")
    
    scraper = LLMEnhancedScraper(headless=True)
    resultados = []
    
    for leiloeiro in LEILOEIROS_TESTE:
        resultado = await testar_leiloeiro(scraper, leiloeiro)
        resultado["leiloeiro"] = leiloeiro["id"]
        resultados.append(resultado)
    
    # Resumo final
    print("\n" + "="*60)
    print("RESUMO FINAL")
    print("="*60)
    
    sucessos = sum(1 for r in resultados if r["status"] == "sucesso")
    falhas = sum(1 for r in resultados if r["status"] == "falha")
    erros = sum(1 for r in resultados if r["status"] == "erro")
    total_imoveis = sum(r.get("count", 0) for r in resultados)
    
    print(f"\n📊 Resultados:")
    print(f"   ✅ Sucesso: {sucessos}/{len(LEILOEIROS_TESTE)} ({100*sucessos/len(LEILOEIROS_TESTE):.1f}%)")
    print(f"   ⚠️ Falha: {falhas}")
    print(f"   ❌ Erro: {erros}")
    print(f"   🏠 Total imóveis: {total_imoveis}")
    
    print("\n📋 Detalhes por leiloeiro:")
    for r in resultados:
        status_icon = "✅" if r["status"] == "sucesso" else "⚠️" if r["status"] == "falha" else "❌"
        print(f"   {status_icon} {r['leiloeiro']}: {r.get('count', 0)} imóveis ({r.get('tempo', 0):.1f}s)")
    
    # Critério de sucesso
    taxa = 100 * sucessos / len(LEILOEIROS_TESTE)
    print("\n" + "="*60)
    if taxa >= 60:
        print(f"🎉 SUCESSO! Taxa de {taxa:.1f}% >= 60%")
        print("   O LLMEnhancedScraper está funcionando!")
    else:
        print(f"⚠️ Taxa de {taxa:.1f}% < 60%")
        print("   Pode ser necessário ajustar prompts ou seletores")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## FASE 4: Executar Teste

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts/testar_llm_enhanced.py
```

Critério de sucesso: >= 3/5 leiloeiros (60%)

---

## FASE 5: Integrar ao ScraperManager

Se o teste passar, adicionar ao `scraper_manager.py`:

```python
# Em app/scrapers/scraper_manager.py

# Adicionar import
try:
    from app.services.llm_enhanced_scraper import LLMEnhancedScraper
    LLM_ENHANCED_AVAILABLE = True
except ImportError:
    LLM_ENHANCED_AVAILABLE = False

# Adicionar método
def scrape_with_llm_fallback(self, url: str, auctioneer_id: str) -> List[Dict]:
    """
    Tenta scraper específico, se falhar usa LLMEnhancedScraper.
    """
    # 1. Tentar scraper específico
    scraper = self._get_specific_scraper(auctioneer_id)
    if scraper:
        try:
            properties = scraper.scrape_properties()
            if properties:
                return properties
        except Exception as e:
            logger.warning(f"Scraper específico falhou: {e}")
    
    # 2. Fallback para LLMEnhancedScraper
    if LLM_ENHANCED_AVAILABLE:
        try:
            llm_scraper = LLMEnhancedScraper(headless=True)
            return llm_scraper.scrape(url, auctioneer_id)
        except Exception as e:
            logger.error(f"LLMEnhancedScraper falhou: {e}")
    
    return []
```

---

## FASE 6: Commit e Push

```bash
git add app/services/llm_enhanced_scraper.py
git add scripts/testar_llm_enhanced.py
git add -u app/scrapers/scraper_manager.py
git commit -m "feat: Adicionar LLMEnhancedScraper como alternativa ao Crawl4AI

- Playwright + GPT-4o-mini para extração inteligente
- Funciona no Windows sem dependência lxml
- Integrado ao ScraperManager como fallback"
git push
```

---

## CRITÉRIOS DE SUCESSO

- [ ] `llm_enhanced_scraper.py` criado e funcional
- [ ] Teste passa com >= 60% de sucesso
- [ ] Integrado ao ScraperManager
- [ ] Commit e push realizados

---

## NOTAS IMPORTANTES

1. **NÃO USAR Crawl4AI** - ele depende de lxml que não compila no Windows
2. **Playwright já está instalado** - usar ele para renderização JS
3. **OpenAI já está configurado** - usar GPT-4o-mini para parsing
4. **Manter compatibilidade** - interface similar ao crawl4ai_scraper.py
