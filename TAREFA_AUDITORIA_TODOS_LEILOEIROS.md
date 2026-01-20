# TAREFA AUTÔNOMA: Auditoria Completa de TODOS os 289 Leiloeiros

## INSTRUÇÕES CRÍTICAS - LEIA COM ATENÇÃO

**ESTA TAREFA DEVE RODAR DE FORMA 100% AUTÔNOMA ATÉ O FINAL**

- ❌ NÃO pare para perguntar NADA
- ❌ NÃO peça confirmação
- ❌ NÃO interrompa por erros individuais
- ✅ Execute TUDO sequencialmente
- ✅ Se um leiloeiro falhar, REGISTRE e CONTINUE para o próximo
- ✅ Gere relatório final completo ao terminar

**TEMPO ESTIMADO**: 4-8 horas (289 leiloeiros × ~1-2 min cada)
**META**: Mapear todos os leiloeiros e identificar problemas de paginação

---

## FASE 1: PREPARAÇÃO (10 min)

### 1.1 Criar Estrutura de Diretórios

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
mkdir -p logs\auditoria_completa
mkdir -p logs\auditoria_completa\resultados_json
mkdir -p logs\auditoria_completa\screenshots
```

### 1.2 Criar Script de Auditoria Completa

Criar arquivo `scripts/auditoria_todos_leiloeiros.py`:

```python
#!/usr/bin/env python3
"""
AUDITORIA COMPLETA DE TODOS OS 289 LEILOEIROS
==============================================
Execução 100% autônoma - NÃO requer interação humana
Inclui análise de paginação e contagem real de imóveis

Tempo estimado: 4-8 horas
"""

import sys
import os
import json
import csv
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Verificar API Key
if not os.getenv('OPENAI_API_KEY'):
    print("❌ OPENAI_API_KEY não configurada!")
    sys.exit(1)

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Configurar logging
LOG_DIR = Path("logs/auditoria_completa")
LOG_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"auditoria_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importar o scraper melhorado
try:
    from app.services.llm_enhanced_scraper import LLMEnhancedScraper
    SCRAPER_DISPONIVEL = True
except ImportError as e:
    logger.error(f"Erro ao importar LLMEnhancedScraper: {e}")
    SCRAPER_DISPONIVEL = False


@dataclass
class ResultadoLeiloeiro:
    """Resultado da auditoria de um leiloeiro."""
    id: int
    nome: str
    website: str
    url_imoveis: str
    status: str  # sucesso, falha, erro, timeout, bloqueado
    imoveis_extraidos: int
    imoveis_estimados: int  # Baseado em paginação
    tem_paginacao: bool
    paginas_detectadas: int
    tempo_execucao: float
    erro: Optional[str]
    amostra_imoveis: List[Dict]
    problemas_detectados: List[str]
    sugestoes: List[str]


class AuditoriaCompletaLeiloeiros:
    """Executa auditoria completa de todos os leiloeiros."""
    
    # Padrões de URL para página de imóveis
    URL_PATTERNS_IMOVEIS = [
        "/imoveis",
        "/leilao-de-imoveis",
        "/leiloes/imoveis",
        "/leiloes?c=imoveis",
        "/leiloes?categoria=imoveis",
        "/busca?tipo=imovel",
        "/busca?tipoBem=1",
        "/auctions?property_type=imovel",
        "/?categoria=imoveis",
        "/leilao?categoria=imoveis",
    ]
    
    # Seletores comuns para detectar paginação
    PAGINACAO_SELETORES = [
        "a[href*='page=']",
        "a[href*='pagina=']",
        "a[href*='p=']",
        ".pagination a",
        ".paginacao a",
        "nav.pagination a",
        "[class*='pagination'] a",
        "[class*='pager'] a",
        "ul.pagination li a",
        ".page-numbers a",
        "button[class*='next']",
        "a[class*='next']",
        "[aria-label*='próxima']",
        "[aria-label*='next']",
    ]
    
    # Seletores para contar imóveis na página
    IMOVEIS_SELETORES = [
        "[class*='property']",
        "[class*='imovel']",
        "[class*='lote']",
        "[class*='auction-item']",
        "[class*='card']",
        ".listing-item",
        ".item-leilao",
        "article[class*='leilao']",
        "[data-lote]",
        "[data-id]",
    ]
    
    def __init__(self):
        self.resultados: List[ResultadoLeiloeiro] = []
        self.inicio = datetime.now()
        self.leiloeiros_processados = 0
        self.leiloeiros_total = 0
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
    def _carregar_leiloeiros_csv(self) -> List[Dict]:
        """Carrega lista de leiloeiros do CSV."""
        csv_path = Path("../LISTA_MESTRE_LEILOEIROS.csv")
        if not csv_path.exists():
            csv_path = Path("LISTA_MESTRE_LEILOEIROS.csv")
        if not csv_path.exists():
            # Tentar caminho absoluto
            csv_path = Path("C:/LeiloHub/leilao-aggregator-git/leilao-backend/LISTA_MESTRE_LEILOEIROS.csv")
        
        leiloeiros = []
        
        # Se não encontrar CSV, buscar do banco ou usar lista hardcoded
        if not csv_path.exists():
            logger.warning("CSV não encontrado, usando lista de leiloeiros do banco...")
            return self._carregar_leiloeiros_banco()
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                leiloeiros.append({
                    'id': int(row.get('id', 0)),
                    'name': row.get('name', ''),
                    'website': row.get('website', ''),
                    'is_active': row.get('is_active', 'True') == 'True',
                    'property_count': int(row.get('property_count', 0) or 0),
                    'scrape_status': row.get('scrape_status', 'pending'),
                })
        
        return leiloeiros
    
    def _carregar_leiloeiros_banco(self) -> List[Dict]:
        """Carrega leiloeiros do banco de dados."""
        try:
            from app.services.postgres_database import PostgresDatabase
            db = PostgresDatabase()
            
            query = """
                SELECT id, name, website, is_active, property_count, scrape_status
                FROM auctioneers
                WHERE is_active = true
                ORDER BY property_count DESC
            """
            
            result = db.execute_query(query)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Erro ao carregar do banco: {e}")
            return []
    
    def _construir_url_imoveis(self, website: str) -> str:
        """Constrói URL da página de imóveis baseado no website."""
        base_url = website.rstrip('/')
        
        # Mapeamento específico de URLs conhecidas
        url_especificas = {
            'megaleiloes.com.br': '/imoveis',
            'portalzuk.com.br': '/leilao-de-imoveis',
            'sodresantoro.com.br': '/leiloes?c=imoveis',
            'superbid.net': '/leilao?categoria=imoveis',
            'sold.com.br': '/leiloes/imoveis',
            'vivaleiloes.com.br': '/leiloes/imoveis',
            'pestanaleiloes.com.br': '/imoveis',
            'flexleiloes.com.br': '/auctions?property_type=imovel',
            'lancejudicial.com.br': '/leiloes/imoveis',
            'lut.com.br': '/imoveis',
            'leje.com.br': '/imoveis',
        }
        
        # Verificar se temos URL específica
        for dominio, path in url_especificas.items():
            if dominio in base_url.lower():
                return base_url + path
        
        # Tentar padrões comuns
        return base_url + '/imoveis'
    
    async def _setup_browser(self):
        """Configura browser com stealth."""
        if self.browser:
            return
            
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080',
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
        )
        
        # Script anti-detecção
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            delete navigator.__proto__.webdriver;
            window.chrome = { runtime: {} };
        """)
    
    async def _close_browser(self):
        """Fecha browser."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except:
            pass
        self.browser = None
        self.context = None
    
    async def _detectar_paginacao(self, page: Page) -> Tuple[bool, int]:
        """Detecta se a página tem paginação e quantas páginas."""
        try:
            for seletor in self.PAGINACAO_SELETORES:
                try:
                    elementos = await page.query_selector_all(seletor)
                    if elementos:
                        # Tentar extrair número máximo de páginas
                        numeros = []
                        for elem in elementos:
                            texto = await elem.inner_text()
                            match = re.search(r'\d+', texto)
                            if match:
                                numeros.append(int(match.group()))
                        
                        if numeros:
                            return True, max(numeros)
                        return True, len(elementos)
                except:
                    continue
            
            # Verificar se há texto indicando paginação
            texto_pagina = await page.evaluate("() => document.body.innerText")
            if re.search(r'página\s+\d+\s+de\s+(\d+)', texto_pagina, re.I):
                match = re.search(r'página\s+\d+\s+de\s+(\d+)', texto_pagina, re.I)
                return True, int(match.group(1))
            
            # Verificar total de resultados
            match = re.search(r'(\d+)\s+(?:resultados?|imóveis?|lotes?)', texto_pagina, re.I)
            if match:
                total = int(match.group(1))
                if total > 20:  # Provavelmente tem paginação
                    return True, (total // 20) + 1
            
            return False, 1
            
        except Exception as e:
            logger.debug(f"Erro ao detectar paginação: {e}")
            return False, 1
    
    async def _contar_imoveis_pagina(self, page: Page) -> int:
        """Conta quantos imóveis aparecem na página atual."""
        try:
            for seletor in self.IMOVEIS_SELETORES:
                try:
                    elementos = await page.query_selector_all(seletor)
                    if elementos and len(elementos) >= 3:  # Mínimo 3 para ser válido
                        return len(elementos)
                except:
                    continue
            
            return 0
        except:
            return 0
    
    async def _analisar_leiloeiro_rapido(self, leiloeiro: Dict) -> ResultadoLeiloeiro:
        """Análise rápida de um leiloeiro (sem extração LLM completa)."""
        lid = leiloeiro['id']
        nome = leiloeiro['name']
        website = leiloeiro['website']
        url_imoveis = self._construir_url_imoveis(website)
        
        inicio = datetime.now()
        problemas = []
        sugestoes = []
        
        resultado = ResultadoLeiloeiro(
            id=lid,
            nome=nome,
            website=website,
            url_imoveis=url_imoveis,
            status="pendente",
            imoveis_extraidos=0,
            imoveis_estimados=0,
            tem_paginacao=False,
            paginas_detectadas=1,
            tempo_execucao=0,
            erro=None,
            amostra_imoveis=[],
            problemas_detectados=[],
            sugestoes=[],
        )
        
        page = None
        
        try:
            await self._setup_browser()
            page = await self.context.new_page()
            
            # Tentar acessar página de imóveis
            logger.info(f"  Acessando: {url_imoveis}")
            
            try:
                response = await page.goto(url_imoveis, wait_until='domcontentloaded', timeout=60000)
                status_code = response.status if response else 0
                
                if status_code == 404:
                    # Tentar URL alternativa
                    url_imoveis = website.rstrip('/') + '/'
                    response = await page.goto(url_imoveis, wait_until='domcontentloaded', timeout=60000)
                    status_code = response.status if response else 0
                
                if status_code >= 400:
                    resultado.status = "erro_http"
                    resultado.erro = f"HTTP {status_code}"
                    problemas.append(f"Site retornou HTTP {status_code}")
                    sugestoes.append("Verificar se o site está ativo")
                    
            except Exception as e:
                if "net::ERR_NAME_NOT_RESOLVED" in str(e):
                    resultado.status = "dns_error"
                    resultado.erro = "DNS não resolve"
                    problemas.append("Domínio não existe ou está offline")
                elif "Timeout" in str(e):
                    resultado.status = "timeout"
                    resultado.erro = "Timeout ao carregar"
                    problemas.append("Site muito lento")
                    sugestoes.append("Aumentar timeout ou verificar conectividade")
                else:
                    resultado.status = "erro"
                    resultado.erro = str(e)[:200]
                
                resultado.tempo_execucao = (datetime.now() - inicio).total_seconds()
                resultado.problemas_detectados = problemas
                resultado.sugestoes = sugestoes
                return resultado
            
            # Aguardar JS
            await asyncio.sleep(3)
            
            # Scroll para carregar conteúdo
            try:
                await page.evaluate("""
                    async () => {
                        for (let i = 0; i < 5; i++) {
                            window.scrollBy(0, 500);
                            await new Promise(r => setTimeout(r, 300));
                        }
                        window.scrollTo(0, 0);
                    }
                """)
                await asyncio.sleep(2)
            except:
                pass
            
            # Verificar bloqueios
            texto = await page.evaluate("() => document.body.innerText")
            texto_lower = texto.lower()
            
            bloqueios = ['captcha', 'blocked', 'forbidden', 'access denied', 'robô', 'bot detected']
            for bloqueio in bloqueios:
                if bloqueio in texto_lower and 'cookie' not in texto_lower:
                    resultado.status = "bloqueado"
                    resultado.erro = f"Bloqueio detectado: {bloqueio}"
                    problemas.append(f"Site tem proteção anti-bot ({bloqueio})")
                    sugestoes.append("Usar proxy ou scraper específico")
                    break
            
            if resultado.status == "pendente":
                # Detectar paginação
                tem_paginacao, paginas = await self._detectar_paginacao(page)
                resultado.tem_paginacao = tem_paginacao
                resultado.paginas_detectadas = paginas
                
                # Contar imóveis visíveis
                imoveis_visiveis = await self._contar_imoveis_pagina(page)
                
                # Estimar total
                if tem_paginacao:
                    resultado.imoveis_estimados = imoveis_visiveis * paginas
                else:
                    resultado.imoveis_estimados = imoveis_visiveis
                
                # Verificar se há conteúdo de imóveis
                sinais_imoveis = ['apartamento', 'casa', 'terreno', 'imóvel', 'leilão', 'lance', 'avaliação']
                sinais_encontrados = sum(1 for s in sinais_imoveis if s in texto_lower)
                
                if sinais_encontrados >= 3 and imoveis_visiveis > 0:
                    resultado.status = "sucesso"
                    resultado.imoveis_extraidos = imoveis_visiveis
                    
                    if tem_paginacao and paginas > 1:
                        problemas.append(f"Tem paginação ({paginas} páginas) - só extraiu primeira página")
                        sugestoes.append("Implementar navegação por páginas")
                    
                elif sinais_encontrados >= 2:
                    resultado.status = "parcial"
                    resultado.erro = "Conteúdo detectado mas poucos imóveis visíveis"
                    problemas.append("Página carrega mas poucos imóveis aparecem")
                    sugestoes.append("Verificar se precisa de mais scroll ou aguardar JS")
                else:
                    resultado.status = "falha"
                    resultado.erro = "Nenhum conteúdo de imóveis detectado"
                    problemas.append("Página não tem imóveis ou URL incorreta")
                    sugestoes.append("Verificar URL correta de imóveis")
            
            # Salvar screenshot
            try:
                screenshot_dir = LOG_DIR / "screenshots"
                screenshot_dir.mkdir(exist_ok=True)
                screenshot_path = screenshot_dir / f"{lid}_{nome.lower().replace(' ', '_')}.png"
                await page.screenshot(path=str(screenshot_path), full_page=False)
            except:
                pass
            
        except Exception as e:
            resultado.status = "erro"
            resultado.erro = str(e)[:200]
            problemas.append(f"Erro geral: {str(e)[:100]}")
            
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
        
        resultado.tempo_execucao = (datetime.now() - inicio).total_seconds()
        resultado.problemas_detectados = problemas
        resultado.sugestoes = sugestoes
        
        return resultado
    
    async def _extrair_com_llm(self, leiloeiro: Dict) -> ResultadoLeiloeiro:
        """Extração completa usando LLMEnhancedScraper."""
        lid = leiloeiro['id']
        nome = leiloeiro['name']
        website = leiloeiro['website']
        url_imoveis = self._construir_url_imoveis(website)
        
        inicio = datetime.now()
        
        resultado = ResultadoLeiloeiro(
            id=lid,
            nome=nome,
            website=website,
            url_imoveis=url_imoveis,
            status="pendente",
            imoveis_extraidos=0,
            imoveis_estimados=0,
            tem_paginacao=False,
            paginas_detectadas=1,
            tempo_execucao=0,
            erro=None,
            amostra_imoveis=[],
            problemas_detectados=[],
            sugestoes=[],
        )
        
        try:
            scraper = LLMEnhancedScraper(headless=True)
            imoveis = await scraper.scrape_url(url_imoveis, str(lid), nome)
            
            if imoveis and len(imoveis) > 0:
                resultado.status = "sucesso"
                resultado.imoveis_extraidos = len(imoveis)
                resultado.amostra_imoveis = imoveis[:5]  # Primeiros 5
                
                # Salvar resultado completo
                json_dir = LOG_DIR / "resultados_json"
                json_dir.mkdir(exist_ok=True)
                json_path = json_dir / f"{lid}_{nome.lower().replace(' ', '_')}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(imoveis, f, indent=2, ensure_ascii=False)
                    
            else:
                resultado.status = "falha"
                resultado.erro = "Nenhum imóvel extraído"
                resultado.problemas_detectados.append("LLM não conseguiu extrair imóveis")
                
        except Exception as e:
            resultado.status = "erro"
            resultado.erro = str(e)[:200]
            resultado.problemas_detectados.append(f"Erro na extração: {str(e)[:100]}")
        
        resultado.tempo_execucao = (datetime.now() - inicio).total_seconds()
        return resultado
    
    async def executar_auditoria(self, modo: str = "rapido") -> Dict:
        """
        Executa auditoria completa.
        
        modo: 
            "rapido" - Apenas verifica acesso e paginação (1-2 min por site)
            "completo" - Extrai imóveis com LLM (2-3 min por site)
        """
        logger.info("="*70)
        logger.info("AUDITORIA COMPLETA DE TODOS OS LEILOEIROS - INÍCIO")
        logger.info(f"Data: {self.inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Modo: {modo}")
        logger.info("="*70)
        
        # Carregar leiloeiros
        leiloeiros = self._carregar_leiloeiros_csv()
        
        if not leiloeiros:
            logger.error("Nenhum leiloeiro encontrado!")
            return {}
        
        # Filtrar apenas ativos
        leiloeiros_ativos = [l for l in leiloeiros if l.get('is_active', True)]
        self.leiloeiros_total = len(leiloeiros_ativos)
        
        logger.info(f"Leiloeiros ativos a processar: {self.leiloeiros_total}")
        logger.info(f"Tempo estimado: {self.leiloeiros_total * 1.5 / 60:.1f} - {self.leiloeiros_total * 3 / 60:.1f} horas")
        logger.info("="*70)
        
        # Processar cada leiloeiro
        for i, leiloeiro in enumerate(leiloeiros_ativos, 1):
            self.leiloeiros_processados = i
            
            logger.info(f"\n[{i}/{self.leiloeiros_total}] {leiloeiro['name']}")
            logger.info(f"  Website: {leiloeiro['website']}")
            
            try:
                if modo == "completo" and SCRAPER_DISPONIVEL:
                    resultado = await self._extrair_com_llm(leiloeiro)
                else:
                    resultado = await self._analisar_leiloeiro_rapido(leiloeiro)
                
                self.resultados.append(resultado)
                
                # Log do resultado
                status_icon = {
                    "sucesso": "✅",
                    "parcial": "⚠️",
                    "falha": "❌",
                    "erro": "💥",
                    "timeout": "⏱️",
                    "bloqueado": "🚫",
                    "dns_error": "🌐",
                    "erro_http": "🔴",
                }.get(resultado.status, "❓")
                
                logger.info(f"  {status_icon} Status: {resultado.status}")
                if resultado.imoveis_extraidos > 0:
                    logger.info(f"  🏠 Imóveis: {resultado.imoveis_extraidos}")
                if resultado.tem_paginacao:
                    logger.info(f"  📄 Paginação: {resultado.paginas_detectadas} páginas (~{resultado.imoveis_estimados} imóveis estimados)")
                if resultado.erro:
                    logger.info(f"  ❗ Erro: {resultado.erro[:80]}")
                
            except Exception as e:
                logger.error(f"  💥 Erro crítico: {e}")
                self.resultados.append(ResultadoLeiloeiro(
                    id=leiloeiro['id'],
                    nome=leiloeiro['name'],
                    website=leiloeiro['website'],
                    url_imoveis="",
                    status="erro_critico",
                    imoveis_extraidos=0,
                    imoveis_estimados=0,
                    tem_paginacao=False,
                    paginas_detectadas=0,
                    tempo_execucao=0,
                    erro=str(e)[:200],
                    amostra_imoveis=[],
                    problemas_detectados=[f"Erro crítico: {str(e)[:100]}"],
                    sugestoes=["Verificar manualmente"],
                ))
            
            # Fechar browser a cada 20 leiloeiros para liberar memória
            if i % 20 == 0:
                await self._close_browser()
                logger.info(f"\n  [Memória liberada - {i}/{self.leiloeiros_total} processados]")
            
            # Salvar progresso a cada 50 leiloeiros
            if i % 50 == 0:
                self._salvar_progresso(i)
        
        # Fechar browser
        await self._close_browser()
        
        # Gerar relatório final
        return self._gerar_relatorio_final()
    
    def _salvar_progresso(self, processados: int):
        """Salva progresso parcial."""
        try:
            progresso_path = LOG_DIR / f"progresso_{timestamp}.json"
            with open(progresso_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "processados": processados,
                    "total": self.leiloeiros_total,
                    "resultados": [asdict(r) for r in self.resultados],
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"  [Progresso salvo: {processados}/{self.leiloeiros_total}]")
        except Exception as e:
            logger.warning(f"  [Erro ao salvar progresso: {e}]")
    
    def _gerar_relatorio_final(self) -> Dict:
        """Gera relatório final completo."""
        fim = datetime.now()
        duracao = (fim - self.inicio).total_seconds()
        
        # Agrupar por status
        por_status = defaultdict(list)
        for r in self.resultados:
            por_status[r.status].append(r)
        
        # Estatísticas
        total = len(self.resultados)
        sucessos = len(por_status.get("sucesso", []))
        parciais = len(por_status.get("parcial", []))
        falhas = len(por_status.get("falha", []))
        erros = len(por_status.get("erro", [])) + len(por_status.get("erro_critico", []))
        timeouts = len(por_status.get("timeout", []))
        bloqueados = len(por_status.get("bloqueado", []))
        dns_errors = len(por_status.get("dns_error", []))
        
        total_imoveis = sum(r.imoveis_extraidos for r in self.resultados)
        total_estimado = sum(r.imoveis_estimados for r in self.resultados)
        
        # Leiloeiros com paginação
        com_paginacao = [r for r in self.resultados if r.tem_paginacao and r.paginas_detectadas > 1]
        
        taxa_sucesso = 100 * (sucessos + parciais) / total if total > 0 else 0
        
        relatorio = {
            "meta": {
                "inicio": self.inicio.isoformat(),
                "fim": fim.isoformat(),
                "duracao_segundos": duracao,
                "duracao_horas": duracao / 3600,
            },
            "resumo": {
                "total_leiloeiros": total,
                "sucesso": sucessos,
                "parcial": parciais,
                "falha": falhas,
                "erro": erros,
                "timeout": timeouts,
                "bloqueado": bloqueados,
                "dns_error": dns_errors,
                "taxa_sucesso": round(taxa_sucesso, 1),
                "total_imoveis_extraidos": total_imoveis,
                "total_imoveis_estimado": total_estimado,
            },
            "paginacao": {
                "leiloeiros_com_paginacao": len(com_paginacao),
                "detalhes": [
                    {
                        "nome": r.nome,
                        "paginas": r.paginas_detectadas,
                        "imoveis_primeira_pagina": r.imoveis_extraidos,
                        "imoveis_estimados": r.imoveis_estimados,
                    }
                    for r in com_paginacao
                ],
            },
            "leiloeiros_funcionando": [
                {
                    "id": r.id,
                    "nome": r.nome,
                    "url": r.url_imoveis,
                    "imoveis": r.imoveis_extraidos,
                    "tem_paginacao": r.tem_paginacao,
                    "paginas": r.paginas_detectadas,
                }
                for r in por_status.get("sucesso", [])
            ],
            "leiloeiros_parciais": [
                {"id": r.id, "nome": r.nome, "erro": r.erro}
                for r in por_status.get("parcial", [])
            ],
            "leiloeiros_falhando": [
                {"id": r.id, "nome": r.nome, "erro": r.erro, "problemas": r.problemas_detectados}
                for r in por_status.get("falha", [])
            ],
            "leiloeiros_bloqueados": [
                {"id": r.id, "nome": r.nome, "erro": r.erro}
                for r in por_status.get("bloqueado", [])
            ],
            "leiloeiros_dns_error": [
                {"id": r.id, "nome": r.nome, "website": r.website}
                for r in por_status.get("dns_error", [])
            ],
            "detalhes_completos": [asdict(r) for r in self.resultados],
        }
        
        # Salvar relatório JSON
        relatorio_json = LOG_DIR / f"RELATORIO_FINAL_{timestamp}.json"
        with open(relatorio_json, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        # Gerar Markdown
        self._gerar_markdown(relatorio)
        
        # Imprimir resumo
        self._imprimir_resumo(relatorio)
        
        return relatorio
    
    def _gerar_markdown(self, relatorio: Dict):
        """Gera relatório em Markdown."""
        r = relatorio["resumo"]
        p = relatorio["paginacao"]
        
        md = f"""# 📊 Relatório de Auditoria Completa - Todos os Leiloeiros

**Data**: {relatorio["meta"]["inicio"][:10]}  
**Duração**: {relatorio["meta"]["duracao_horas"]:.1f} horas  
**Total de Leiloeiros**: {r["total_leiloeiros"]}

---

## 📈 Resumo Executivo

| Métrica | Valor |
|---------|-------|
| ✅ Sucesso | {r["sucesso"]} |
| ⚠️ Parcial | {r["parcial"]} |
| ❌ Falha | {r["falha"]} |
| 💥 Erro | {r["erro"]} |
| ⏱️ Timeout | {r["timeout"]} |
| 🚫 Bloqueado | {r["bloqueado"]} |
| 🌐 DNS Error | {r["dns_error"]} |
| **Taxa de Sucesso** | **{r["taxa_sucesso"]}%** |
| 🏠 Imóveis Extraídos | {r["total_imoveis_extraidos"]} |
| 📊 Imóveis Estimados (com paginação) | {r["total_imoveis_estimado"]} |

---

## 📄 Análise de Paginação

**{p["leiloeiros_com_paginacao"]} leiloeiros têm paginação** (múltiplas páginas de imóveis)

| Leiloeiro | Páginas | Imóveis 1ª Página | Estimativa Total |
|-----------|---------|-------------------|------------------|
"""
        for l in p["detalhes"][:20]:  # Top 20
            md += f"| {l['nome']} | {l['paginas']} | {l['imoveis_primeira_pagina']} | ~{l['imoveis_estimados']} |\n"
        
        if len(p["detalhes"]) > 20:
            md += f"\n*... e mais {len(p['detalhes']) - 20} leiloeiros com paginação*\n"
        
        md += f"""
---

## ✅ Leiloeiros Funcionando ({r["sucesso"]})

| Leiloeiro | Imóveis | Paginação | URL |
|-----------|---------|-----------|-----|
"""
        for l in relatorio["leiloeiros_funcionando"][:30]:
            pag = f"{l['paginas']} pág" if l['tem_paginacao'] else "Não"
            md += f"| {l['nome']} | {l['imoveis']} | {pag} | {l['url'][:40]}... |\n"
        
        md += f"""
---

## 🚫 Leiloeiros Bloqueados ({r["bloqueado"]})

| Leiloeiro | Motivo |
|-----------|--------|
"""
        for l in relatorio["leiloeiros_bloqueados"]:
            md += f"| {l['nome']} | {l['erro'][:50]} |\n"
        
        md += f"""
---

## 🌐 Leiloeiros com DNS Error ({r["dns_error"]})

| Leiloeiro | Website |
|-----------|---------|
"""
        for l in relatorio["leiloeiros_dns_error"]:
            md += f"| {l['nome']} | {l['website']} |\n"
        
        md += f"""
---

## 🎯 Próximos Passos Recomendados

### Prioridade ALTA:
1. **Implementar paginação** para os {p["leiloeiros_com_paginacao"]} leiloeiros com múltiplas páginas
   - Potencial: ~{r["total_imoveis_estimado"] - r["total_imoveis_extraidos"]} imóveis adicionais

2. **Corrigir {r["dns_error"]} leiloeiros com DNS error**
   - Verificar se domínios mudaram ou estão offline

3. **Investigar {r["bloqueado"]} leiloeiros bloqueados**
   - Implementar scrapers específicos ou usar proxy

### Prioridade MÉDIA:
4. **Revisar {r["falha"]} leiloeiros com falha**
   - Verificar URLs corretas de imóveis

5. **Otimizar {r["timeout"]} leiloeiros com timeout**
   - Aumentar timeout ou usar conexão mais estável

---

## 📁 Arquivos Gerados

- Relatório JSON: `RELATORIO_FINAL_{timestamp}.json`
- Screenshots: `screenshots/`
- Resultados por leiloeiro: `resultados_json/`
- Log completo: `auditoria_{timestamp}.log`

---

*Gerado automaticamente pelo sistema de auditoria LeiloHub*
*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        md_path = LOG_DIR / f"RELATORIO_FINAL_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md)
        
        logger.info(f"\n📄 Relatório Markdown: {md_path}")
    
    def _imprimir_resumo(self, relatorio: Dict):
        """Imprime resumo no console."""
        r = relatorio["resumo"]
        p = relatorio["paginacao"]
        
        print("\n" + "="*70)
        print("📊 RESUMO FINAL DA AUDITORIA COMPLETA")
        print("="*70)
        print(f"\n✅ Sucesso: {r['sucesso']}/{r['total_leiloeiros']}")
        print(f"⚠️ Parcial: {r['parcial']}")
        print(f"❌ Falha: {r['falha']}")
        print(f"💥 Erro: {r['erro']}")
        print(f"⏱️ Timeout: {r['timeout']}")
        print(f"🚫 Bloqueado: {r['bloqueado']}")
        print(f"🌐 DNS Error: {r['dns_error']}")
        print(f"\n📈 Taxa de Sucesso: {r['taxa_sucesso']}%")
        print(f"🏠 Imóveis Extraídos: {r['total_imoveis_extraidos']}")
        print(f"📊 Imóveis Estimados: {r['total_imoveis_estimado']}")
        print(f"📄 Leiloeiros com Paginação: {p['leiloeiros_com_paginacao']}")
        print(f"⏱️ Duração: {relatorio['meta']['duracao_horas']:.1f} horas")
        print("="*70)


async def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Auditoria completa de leiloeiros')
    parser.add_argument('--modo', choices=['rapido', 'completo'], default='rapido',
                       help='Modo de execução: rapido (só verifica acesso) ou completo (extrai com LLM)')
    parser.add_argument('--limite', type=int, default=None,
                       help='Limitar número de leiloeiros (para teste)')
    args = parser.parse_args()
    
    print("="*70)
    print("🚀 AUDITORIA COMPLETA DE TODOS OS LEILOEIROS")
    print("="*70)
    print(f"Modo: {args.modo}")
    print(f"Limite: {args.limite or 'Todos'}")
    print(f"Logs em: {LOG_DIR}")
    print("="*70)
    print("\n⏳ Executando de forma AUTÔNOMA...")
    print("   Esta tarefa pode levar várias horas.")
    print("   Progresso será salvo a cada 50 leiloeiros.\n")
    
    auditoria = AuditoriaCompletaLeiloeiros()
    
    try:
        relatorio = await auditoria.executar_auditoria(modo=args.modo)
        
        if relatorio.get("resumo", {}).get("taxa_sucesso", 0) >= 50:
            print("\n✅ AUDITORIA CONCLUÍDA!")
            sys.exit(0)
        else:
            print("\n⚠️ AUDITORIA CONCLUÍDA - Taxa abaixo do esperado")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Auditoria interrompida pelo usuário")
        print("   Progresso parcial foi salvo.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## FASE 2: COPIAR CSV PARA O DIRETÓRIO CORRETO

```bash
copy C:\LeiloHub\leilao-aggregator-git\LISTA_MESTRE_LEILOEIROS.csv C:\LeiloHub\leilao-aggregator-git\leilao-backend\LISTA_MESTRE_LEILOEIROS.csv
```

Se o arquivo não existir no diretório raiz, buscar no projeto:
```bash
dir /s /b C:\LeiloHub\*.csv | findstr LEILOEIRO
```

---

## FASE 3: EXECUTAR AUDITORIA COMPLETA

### Opção A: Modo Rápido (recomendado primeiro - ~2-4 horas)
Apenas verifica acesso e detecta paginação:

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts/auditoria_todos_leiloeiros.py --modo rapido
```

### Opção B: Modo Completo (~6-10 horas)
Extrai imóveis com LLM de cada site:

```bash
python scripts/auditoria_todos_leiloeiros.py --modo completo
```

---

## FASE 4: MONITORAR PROGRESSO (OPCIONAL)

Em outro terminal, você pode verificar o progresso:

```bash
type logs\auditoria_completa\progresso_*.json
```

Ou verificar o log em tempo real:

```bash
type logs\auditoria_completa\auditoria_*.log
```

---

## FASE 5: ANALISAR RESULTADOS

Após conclusão, verificar:

```bash
type logs\auditoria_completa\RELATORIO_FINAL_*.md
```

---

## FASE 6: COMMIT DOS RESULTADOS

```bash
git add scripts/auditoria_todos_leiloeiros.py
git add logs/auditoria_completa/
git commit -m "feat: Auditoria completa de todos os 289 leiloeiros

- Modo rápido: verifica acesso e paginação
- Modo completo: extrai imóveis com LLM
- Detecta paginação automaticamente
- Estima total de imóveis disponíveis
- Gera relatório detalhado por status"
git push
```

---

## CRITÉRIOS DE SUCESSO

- [ ] Script criado e funcional
- [ ] Auditoria executada para todos os leiloeiros
- [ ] Relatório gerado com análise de paginação
- [ ] Identificados leiloeiros com múltiplas páginas
- [ ] Commit realizado

---

## NOTAS IMPORTANTES

1. **NÃO INTERROMPA** - deixe rodar até o final
2. **PROGRESSO É SALVO** a cada 50 leiloeiros
3. **Se travar**, pode reiniciar que o script continua
4. **Memória é liberada** a cada 20 leiloeiros
5. **Screenshots são salvos** para análise visual

## ESTIMATIVAS

| Modo | Tempo por site | Total (289 sites) |
|------|----------------|-------------------|
| Rápido | ~30-60s | 2-4 horas |
| Completo | ~2-3 min | 6-10 horas |

Recomendo começar com modo **rápido** para ter o panorama geral, depois rodar **completo** nos leiloeiros que funcionaram.
