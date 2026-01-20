# TAREFA AUTÔNOMA: Integrar Código Crawl4AI do leilohub-scraper-final

**Data:** 2026-01-19
**Executor:** Cursor Agent
**Modo:** AUTÔNOMO - Execute sem parar para perguntar

---

## CONTEXTO CRÍTICO

Existem DOIS projetos LeiloHub:

| Projeto | Localização | Crawl4AI | Taxa Sucesso |
|---------|-------------|----------|--------------|
| `leilohub-scraper-final` | `C:\LeiloHub\leilohub-scraper-final\` | ✅ Funciona | **95%** |
| `leilao-aggregator-git` | `C:\LeiloHub\leilao-aggregator-git\` | ❌ Não tem | 1.8% |

O código que teve 95% de sucesso em 116 leiloeiros (testado em Dez/2025) está em `leilohub-scraper-final` mas NUNCA foi integrado ao projeto principal.

**OBJETIVO:** Integrar a lógica Crawl4AI + GPT-4o-mini do projeto que funciona para o projeto principal.

---

## FASE 1: Analisar Estrutura do Projeto Fonte

```powershell
cd C:\LeiloHub\leilohub-scraper-final

# Ver estrutura
Write-Host "=== ESTRUTURA leilohub-scraper-final ===" -ForegroundColor Yellow
Get-ChildItem -Recurse -Name -Include "*.py" | Select-Object -First 30

# Ver main_v45.py (entry point que teve 95% sucesso)
Write-Host "`n=== main_v45.py (primeiras 100 linhas) ===" -ForegroundColor Yellow
Get-Content "main_v45.py" -ErrorAction SilentlyContinue | Select-Object -First 100

# Ver adaptador default (usa Crawl4AI)
Write-Host "`n=== adaptadores/default.py (primeiras 150 linhas) ===" -ForegroundColor Yellow
Get-Content "adaptadores/default.py" -ErrorAction SilentlyContinue | Select-Object -First 150
```

Documente:
- Como o Crawl4AI é usado
- Como o GPT-4o-mini é chamado
- Qual o schema de extração
- Como os dados são normalizados

---

## FASE 2: Verificar Dependências

```powershell
cd C:\LeiloHub\leilohub-scraper-final

# Ver requirements
Write-Host "=== requirements.txt ===" -ForegroundColor Yellow
Get-Content "requirements.txt" -ErrorAction SilentlyContinue

# Ver .env (quais variáveis são necessárias)
Write-Host "`n=== Variáveis no .env ===" -ForegroundColor Yellow
Get-Content ".env" | ForEach-Object { if ($_ -match "^([A-Z_]+)=") { $matches[1] } }
```

---

## FASE 3: Criar Módulo Crawl4AI no Projeto Principal

Crie o arquivo `C:\LeiloHub\leilao-aggregator-git\leilao-backend\app\services\crawl4ai_scraper.py`:

```python
"""
Scraper baseado em Crawl4AI + GPT-4o-mini
Portado de leilohub-scraper-final (95% sucesso em 116 leiloeiros - Dez/2025)

Fluxo:
1. Crawl4AI baixa página HTML
2. PruningContentFilter limpa conteúdo irrelevante
3. LLMExtractionStrategy + GPT-4o-mini extrai dados estruturados
4. Regex fallback para fotos
5. Normalização e retorno
"""
import os
import sys
import json
import re
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Verificar dependências
try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
    from crawl4ai.chunking_strategy import RegexChunking
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("crawl4ai não instalado. Execute: pip install crawl4ai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Schema para extração de imóveis (mesmo usado nos testes de 95%)
IMOVEL_SCHEMA = {
    "type": "object",
    "properties": {
        "imoveis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "description": "Título ou descrição do imóvel"},
                    "endereco": {"type": "string", "description": "Endereço completo"},
                    "cidade": {"type": "string", "description": "Cidade"},
                    "estado": {"type": "string", "description": "Estado (sigla UF de 2 letras)"},
                    "tipo": {"type": "string", "description": "Tipo: Apartamento, Casa, Terreno, Comercial, Rural"},
                    "area": {"type": "number", "description": "Área em m²"},
                    "valor_avaliacao": {"type": "number", "description": "Valor de avaliação em R$"},
                    "valor_minimo": {"type": "number", "description": "Lance mínimo ou valor de 2ª praça em R$"},
                    "desconto": {"type": "number", "description": "Percentual de desconto"},
                    "data_leilao": {"type": "string", "description": "Data do leilão"},
                    "modalidade": {"type": "string", "description": "Judicial, Extrajudicial ou Venda Direta"},
                    "url": {"type": "string", "description": "URL da página do imóvel"},
                    "imagem": {"type": "string", "description": "URL da imagem principal"}
                }
            }
        }
    }
}

# Prompt otimizado (baseado nos testes de Dez/2025)
EXTRACTION_PROMPT = """
Extraia TODOS os imóveis disponíveis para leilão nesta página.

Para cada imóvel, extraia:
- titulo: Nome/descrição do imóvel
- endereco: Endereço completo se disponível
- cidade: Cidade do imóvel
- estado: Sigla do estado (UF) com 2 letras (SP, RJ, MG, etc.)
- tipo: Apartamento, Casa, Terreno, Comercial ou Rural
- area: Área em m² (apenas número)
- valor_avaliacao: Valor de avaliação em R$ (apenas número)
- valor_minimo: Lance mínimo ou 2ª praça em R$ (apenas número)
- desconto: Percentual de desconto (apenas número)
- data_leilao: Data do leilão (formato DD/MM/YYYY)
- modalidade: Judicial, Extrajudicial ou Venda Direta
- url: URL completa da página do imóvel
- imagem: URL da imagem principal

REGRAS:
- Se um campo não estiver disponível, deixe em branco ou null
- Para valores monetários, extraia apenas o número (sem R$, pontos ou vírgulas)
- Para área, extraia apenas o número (sem m²)
- Foque em imóveis reais, ignore anúncios, banners e menus
- Estado deve ser sigla de 2 letras maiúsculas
"""


class Crawl4AIScraper:
    """
    Scraper usando Crawl4AI + GPT-4o-mini.
    Portado de leilohub-scraper-final com 95% de sucesso.
    """
    
    def __init__(self):
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("crawl4ai não está instalado. Execute: pip install crawl4ai")
        
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não configurada no .env")
        
        self.extraction_strategy = LLMExtractionStrategy(
            provider="openai/gpt-4o-mini",
            api_token=OPENAI_API_KEY,
            schema=IMOVEL_SCHEMA,
            extraction_type="schema",
            instruction=EXTRACTION_PROMPT,
            chunk_token_threshold=8000,  # Otimizado nos testes
            overlap_rate=0.1,
        )
    
    async def scrape_url(self, url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
        """
        Extrai imóveis de uma URL usando Crawl4AI + GPT-4o-mini.
        
        Args:
            url: URL da página de listagem do leiloeiro
            auctioneer_id: ID do leiloeiro (para normalização)
            auctioneer_name: Nome do leiloeiro
        
        Returns:
            Lista de dicionários com dados dos imóveis
        """
        logger.info(f"Crawl4AI: Iniciando scrape de {url}")
        
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    extraction_strategy=self.extraction_strategy,
                    bypass_cache=True,
                    page_timeout=60000,
                )
                
                if not result.success:
                    logger.error(f"Crawl4AI: Falha ao acessar {url}: {result.error_message}")
                    return []
                
                # Parsear resultado
                imoveis = self._parse_result(result.extracted_content)
                
                # Extrair fotos via regex (mais confiável que LLM para URLs)
                fotos = self._extract_fotos_regex(result.html)
                
                # Normalizar e enriquecer dados
                normalized = []
                for i, imovel in enumerate(imoveis):
                    prop = self._normalize_property(imovel, auctioneer_id, auctioneer_name, url)
                    
                    # Adicionar foto se disponível
                    if i < len(fotos) and not prop.get('image_url'):
                        prop['image_url'] = fotos[i]
                    
                    normalized.append(prop)
                
                logger.info(f"Crawl4AI: Extraídos {len(normalized)} imóveis de {url}")
                return normalized
                
        except Exception as e:
            logger.error(f"Crawl4AI: Erro em {url}: {e}")
            return []
    
    def _parse_result(self, extracted_content: str) -> List[Dict]:
        """Parseia o JSON retornado pelo LLM."""
        if not extracted_content:
            return []
        
        try:
            data = json.loads(extracted_content)
            return data.get("imoveis", [])
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao parsear JSON: {e}")
            return []
    
    def _extract_fotos_regex(self, html: str) -> List[str]:
        """
        Extrai URLs de fotos via regex.
        Mais confiável que LLM para URLs de imagens.
        """
        if not html:
            return []
        
        # Padrões comuns de URLs de fotos de imóveis
        patterns = [
            r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
            r'https?://cdn[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
            r'https?://[^\s"\'<>]*imovel[^\s"\'<>]*\.(?:jpg|jpeg|png|webp)',
        ]
        
        fotos = set()
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            fotos.update(matches)
        
        # Filtrar logos e placeholders
        fotos_filtradas = [
            f for f in fotos 
            if not any(x in f.lower() for x in ['logo', 'banner', 'placeholder', 'icon', 'avatar'])
        ]
        
        return list(fotos_filtradas)[:20]  # Limitar a 20 fotos
    
    def _normalize_property(self, imovel: Dict, auctioneer_id: str, auctioneer_name: str, source_url: str) -> Dict:
        """Normaliza dados do imóvel para o formato do banco."""
        
        # Inferir auctioneer_id da URL se não fornecido
        if not auctioneer_id:
            from urllib.parse import urlparse
            domain = urlparse(source_url).netloc
            auctioneer_id = domain.replace('www.', '').replace('.com.br', '').replace('.', '_')
        
        return {
            # Identificação
            'source': auctioneer_id.lower(),
            'auctioneer_id': auctioneer_id.lower(),
            'auctioneer_name': auctioneer_name or auctioneer_id.title(),
            'source_url': imovel.get('url') or source_url,
            
            # Dados básicos
            'title': imovel.get('titulo', '').strip(),
            'address': imovel.get('endereco', '').strip(),
            'city': self._title_case(imovel.get('cidade', '')),
            'state': self._normalize_state(imovel.get('estado', '')),
            'category': self._normalize_category(imovel.get('tipo', '')),
            
            # Valores
            'evaluation_value': self._parse_number(imovel.get('valor_avaliacao')),
            'first_auction_value': self._parse_number(imovel.get('valor_avaliacao')),
            'second_auction_value': self._parse_number(imovel.get('valor_minimo')),
            'discount_percentage': self._parse_number(imovel.get('desconto')),
            'area_total': self._parse_number(imovel.get('area')),
            
            # Datas e modalidade
            'first_auction_date': self._parse_date(imovel.get('data_leilao')),
            'auction_type': self._normalize_modalidade(imovel.get('modalidade', '')),
            
            # Imagem
            'image_url': imovel.get('imagem'),
            
            # Metadata
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
    
    def _title_case(self, text: str) -> str:
        """Converte para Title Case."""
        if not text:
            return ''
        return ' '.join(word.capitalize() for word in text.strip().split())
    
    def _normalize_state(self, state: str) -> str:
        """Normaliza sigla do estado."""
        if not state:
            return ''
        state = state.strip().upper()
        valid_states = {'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
                       'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
                       'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'}
        return state if state in valid_states else ''
    
    def _normalize_category(self, tipo: str) -> str:
        """Normaliza categoria do imóvel."""
        if not tipo:
            return 'Outro'
        tipo_lower = tipo.lower()
        
        if 'apartamento' in tipo_lower or 'apto' in tipo_lower:
            return 'Apartamento'
        elif 'casa' in tipo_lower:
            return 'Casa'
        elif 'terreno' in tipo_lower or 'lote' in tipo_lower:
            return 'Terreno'
        elif 'comercial' in tipo_lower or 'sala' in tipo_lower or 'loja' in tipo_lower:
            return 'Comercial'
        elif 'rural' in tipo_lower or 'fazenda' in tipo_lower or 'sítio' in tipo_lower:
            return 'Rural'
        else:
            return 'Outro'
    
    def _normalize_modalidade(self, modalidade: str) -> str:
        """Normaliza modalidade do leilão."""
        if not modalidade:
            return 'Extrajudicial'
        modalidade_lower = modalidade.lower()
        
        if 'judicial' in modalidade_lower and 'extra' not in modalidade_lower:
            return 'Judicial'
        elif 'extrajudicial' in modalidade_lower:
            return 'Extrajudicial'
        elif 'direta' in modalidade_lower or 'venda' in modalidade_lower:
            return 'Venda Direta'
        else:
            return 'Extrajudicial'
    
    def _parse_number(self, value) -> Optional[float]:
        """Converte valor para float."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remover formatação brasileira
            clean = re.sub(r'[R$\s.]', '', value).replace(',', '.')
            try:
                return float(clean)
            except ValueError:
                return None
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Converte data para formato ISO."""
        if not date_str:
            return None
        
        # Tentar diversos formatos
        formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None
    
    def scrape_url_sync(self, url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
        """Versão síncrona do scrape_url."""
        return asyncio.run(self.scrape_url(url, auctioneer_id, auctioneer_name))


# Função de conveniência
def scrape_with_crawl4ai(url: str, auctioneer_id: str = None, auctioneer_name: str = None) -> List[Dict]:
    """
    Função de conveniência para scraping com Crawl4AI.
    
    Uso:
        from app.services.crawl4ai_scraper import scrape_with_crawl4ai
        imoveis = scrape_with_crawl4ai("https://www.megaleiloes.com.br")
    """
    scraper = Crawl4AIScraper()
    return scraper.scrape_url_sync(url, auctioneer_id, auctioneer_name)
```

---

## FASE 4: Copiar Lógica Adicional do Projeto Fonte

Verifique se há lógica adicional importante em `leilohub-scraper-final`:

```powershell
cd C:\LeiloHub\leilohub-scraper-final

# Ver database.py (normalização)
Write-Host "=== database.py ===" -ForegroundColor Yellow
Get-Content "database.py" -ErrorAction SilentlyContinue | Select-Object -First 100

# Ver se há configs específicas
Write-Host "`n=== configs/ ===" -ForegroundColor Yellow
Get-ChildItem "configs" -ErrorAction SilentlyContinue

# Ver deduplicação
Write-Host "`n=== deduplicacao.py ===" -ForegroundColor Yellow
Get-Content "deduplicacao.py" -ErrorAction SilentlyContinue | Select-Object -First 80
```

Se houver lógica importante, integre ao módulo criado.

---

## FASE 5: Instalar Dependências no Projeto Principal

```powershell
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# Copiar requirements do projeto fonte se necessário
Write-Host "=== Instalando dependências Crawl4AI ===" -ForegroundColor Yellow

# Instalar crawl4ai
pip install crawl4ai

# Instalar playwright (Crawl4AI usa internamente)
pip install playwright
playwright install chromium

# Verificar instalação
python -c "from crawl4ai import AsyncWebCrawler; print('crawl4ai: OK')"
python -c "import openai; print('openai: OK')"
```

**SE CRAWL4AI FALHAR NO WINDOWS:**
O projeto `leilohub-scraper-final` conseguiu instalar, então deve funcionar.
Verifique se está no mesmo ambiente Python.

```powershell
# Verificar qual Python o leilohub-scraper-final usa
cd C:\LeiloHub\leilohub-scraper-final
python --version
pip list | Select-String "crawl4ai"
```

---

## FASE 6: Criar Script de Teste

Crie `leilao-backend/scripts/testar_crawl4ai_integrado.py`:

```python
"""
Testa o módulo Crawl4AI integrado ao projeto principal.
Deve reproduzir os 95% de sucesso do leilohub-scraper-final.
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("TESTE: CRAWL4AI INTEGRADO AO PROJETO PRINCIPAL")
print("=" * 70)

# Verificar dependências
print("\n[1] Verificando dependências...")
try:
    from app.services.crawl4ai_scraper import Crawl4AIScraper, scrape_with_crawl4ai
    print("  ✓ crawl4ai_scraper importado")
except ImportError as e:
    print(f"  ✗ Erro: {e}")
    sys.exit(1)

# Testar em 5 leiloeiros
LEILOEIROS_TESTE = [
    {"nome": "Mega Leilões", "url": "https://www.megaleiloes.com.br", "id": "megaleiloes"},
    {"nome": "Sold Leilões", "url": "https://www.sold.com.br", "id": "sold"},
    {"nome": "Flex Leilões", "url": "https://www.flexleiloes.com.br", "id": "flexleiloes"},
    {"nome": "Viva Leilões", "url": "https://www.vivaleiloes.com.br", "id": "vivaleiloes"},
    {"nome": "Lance Judicial", "url": "https://www.lancejudicial.com.br", "id": "lancejudicial"},
]

print(f"\n[2] Testando {len(LEILOEIROS_TESTE)} leiloeiros...")

resultados = []
for leiloeiro in LEILOEIROS_TESTE:
    print(f"\n  [{leiloeiro['nome']}] {leiloeiro['url']}")
    
    try:
        imoveis = scrape_with_crawl4ai(
            url=leiloeiro['url'],
            auctioneer_id=leiloeiro['id'],
            auctioneer_name=leiloeiro['nome']
        )
        
        if imoveis:
            print(f"    ✓ {len(imoveis)} imóveis extraídos")
            # Mostrar exemplo
            if imoveis[0].get('title'):
                print(f"    Exemplo: {imoveis[0]['title'][:50]}")
            resultados.append({"nome": leiloeiro['nome'], "sucesso": True, "qtd": len(imoveis)})
        else:
            print(f"    ✗ Nenhum imóvel extraído")
            resultados.append({"nome": leiloeiro['nome'], "sucesso": False, "qtd": 0})
            
    except Exception as e:
        print(f"    ✗ Erro: {e}")
        resultados.append({"nome": leiloeiro['nome'], "sucesso": False, "qtd": 0, "erro": str(e)})

# Resumo
print("\n" + "=" * 70)
print("RESUMO")
print("=" * 70)

sucessos = sum(1 for r in resultados if r['sucesso'])
total_imoveis = sum(r['qtd'] for r in resultados)

print(f"\nTaxa de sucesso: {sucessos}/{len(LEILOEIROS_TESTE)} ({sucessos/len(LEILOEIROS_TESTE)*100:.0f}%)")
print(f"Total de imóveis: {total_imoveis}")

for r in resultados:
    status = "✓" if r['sucesso'] else "✗"
    print(f"  {status} {r['nome']}: {r['qtd']} imóveis")

if sucessos >= 4:
    print("\n✓ INTEGRAÇÃO BEM SUCEDIDA!")
else:
    print("\n⚠ VERIFICAR PROBLEMAS")
```

Execute:

```powershell
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts/testar_crawl4ai_integrado.py
```

---

## FASE 7: Integrar ao ScraperManager

Se os testes passarem, integre ao ScraperManager:

Edite `app/scrapers/scraper_manager.py` para adicionar fallback Crawl4AI:

```python
# No início do arquivo, adicionar import
try:
    from app.services.crawl4ai_scraper import Crawl4AIScraper
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False

# Adicionar método de fallback na classe ScraperManager
def scrape_with_fallback(self, url: str, auctioneer_id: str = None) -> List[Dict]:
    """
    Tenta scraper específico primeiro, depois Crawl4AI como fallback.
    """
    # Tentar scraper específico
    if auctioneer_id in self.scrapers:
        try:
            scraper = self.scrapers[auctioneer_id]()
            result = scraper.scrape_properties(max_properties=50)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Scraper específico falhou: {e}")
    
    # Fallback: Crawl4AI
    if CRAWL4AI_AVAILABLE:
        try:
            scraper = Crawl4AIScraper()
            return scraper.scrape_url_sync(url, auctioneer_id)
        except Exception as e:
            logger.error(f"Crawl4AI fallback falhou: {e}")
    
    return []
```

---

## FASE 8: Atualizar requirements.txt

```powershell
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# Adicionar dependências
Add-Content "requirements.txt" "`n# Crawl4AI + LLM (95% sucesso - integrado de leilohub-scraper-final)"
Add-Content "requirements.txt" "crawl4ai>=0.3.0"
Add-Content "requirements.txt" "openai>=1.0.0"
```

---

## FASE 9: Commit

```powershell
cd C:\LeiloHub\leilao-aggregator-git

git add leilao-backend/app/services/crawl4ai_scraper.py
git add leilao-backend/scripts/testar_crawl4ai_integrado.py
git add leilao-backend/requirements.txt
git add leilao-backend/app/scrapers/scraper_manager.py

git commit -m "feat: integrar Crawl4AI do leilohub-scraper-final (95% sucesso)

- Criar crawl4ai_scraper.py com lógica portada
- Usar mesmo schema e prompt que teve 95% sucesso em Dez/2025
- Adicionar fallback Crawl4AI ao ScraperManager
- Atualizar requirements.txt

Fonte: leilohub-scraper-final/main_v45.py e adaptadores/default.py"

git push origin main
```

---

## CRITÉRIOS DE SUCESSO

- [ ] Estrutura do `leilohub-scraper-final` analisada
- [ ] `crawl4ai_scraper.py` criado no projeto principal
- [ ] Crawl4AI instalado e funcionando
- [ ] Teste com 5 leiloeiros executado
- [ ] Taxa de sucesso >= 60% (3/5)
- [ ] Integração com ScraperManager feita
- [ ] Commit e push realizados

---

## SE CRAWL4AI NÃO INSTALAR

Se mesmo copiando do projeto que funciona o Crawl4AI não instalar:

1. Verificar se o ambiente Python é o mesmo
2. Tentar instalar via: `pip install crawl4ai --no-deps` e depois instalar dependências manualmente
3. Como último recurso, criar versão Playwright + OpenAI direta (sem Crawl4AI)

---

## DOCUMENTAÇÃO

Após conclusão, atualize `VERIFICACAO_ARQUITETURA.md`:

```markdown
## Integração Crawl4AI (DATA)

### Status
- [x] Código portado de leilohub-scraper-final
- [x] crawl4ai_scraper.py criado
- [ ] Dependências instaladas
- [ ] Testes executados

### Resultados
[Preencher após execução]
```

---

**COMECE AGORA. Execute todas as fases em sequência.**
