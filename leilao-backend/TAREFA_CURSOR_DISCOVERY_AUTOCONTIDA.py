# ============================================================
# TAREFA AUTÔNOMA: Discovery Inteligente de Leiloeiros
# ============================================================
# Para: Cursor Agent
# Modo: AUTÔNOMO - Executar sem parar para perguntar
# Tempo estimado: 15-20 minutos
# ============================================================

"""
INSTRUÇÕES PARA O CURSOR AGENT:

1. Crie o arquivo app/utils/discovery_leiloeiros.py com o código abaixo
2. Execute o script
3. Analise os resultados
4. Apresente relatório final

NÃO PARE PARA PERGUNTAR - Execute até o fim!
"""

# ============================================================
# CÓDIGO PARA CRIAR EM: app/utils/discovery_leiloeiros.py
# ============================================================

CODIGO_DISCOVERY = '''
#!/usr/bin/env python3
"""
Discovery Inteligente de Leiloeiros
Analisa estrutura dos sites para otimizar scrapers

Execução: python -m app.utils.discovery_leiloeiros
"""

import asyncio
import httpx
import json
import csv
import re
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SiteAnalysis:
    """Resultado da análise de um site."""
    auctioneer_id: str
    name: str
    website: str
    
    # Status
    is_online: bool = False
    http_status: int = 0
    response_time_ms: int = 0
    
    # Proteções detectadas
    has_cloudflare: bool = False
    has_captcha: bool = False
    requires_javascript: bool = False
    
    # Estrutura de URLs
    property_url_pattern: Optional[str] = None
    listing_url: Optional[str] = None
    
    # Seletores identificados
    selectors: Dict = None
    
    # Recomendação
    recommended_method: str = "unknown"
    difficulty: str = "unknown"
    
    # Metadados
    analyzed_at: str = ""
    error: Optional[str] = None
    
    def __post_init__(self):
        self.analyzed_at = datetime.now().isoformat()
        if self.selectors is None:
            self.selectors = {}


class IntelligentDiscovery:
    """Discovery inteligente que analisa a estrutura dos sites."""
    
    PROPERTY_URL_PATTERNS = [
        r'/imovel/[^/]+',
        r'/imoveis/[^/]+',
        r'/lote/\\d+',
        r'/lotes/\\d+',
        r'/item/\\d+',
        r'/detalhes/\\d+',
        r'/property/\\d+',
        r'/bem/\\d+',
    ]
    
    CLOUDFLARE_INDICATORS = [
        'cloudflare', 'cf-ray', '__cf_bm', 'challenge-platform',
    ]
    
    JAVASCRIPT_REQUIRED_INDICATORS = [
        'react', 'vue', 'angular', '__NEXT_DATA__',
        'window.__INITIAL_STATE__', 'data-reactroot',
    ]
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.results: List[SiteAnalysis] = []
        
    async def analyze_site(self, auctioneer: Dict) -> SiteAnalysis:
        """Analisa um único site de leiloeiro."""
        
        analysis = SiteAnalysis(
            auctioneer_id=str(auctioneer.get('id', '')),
            name=auctioneer.get('name', ''),
            website=auctioneer.get('website', '')
        )
        
        if not analysis.website:
            analysis.error = "Website não informado"
            return analysis
        
        url = analysis.website
        if not url.startswith('http'):
            url = f'https://{url}'
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=False
            ) as client:
                
                start_time = datetime.now()
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml',
                    'Accept-Language': 'pt-BR,pt;q=0.9',
                }
                
                response = await client.get(url, headers=headers)
                
                analysis.http_status = response.status_code
                analysis.response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                analysis.is_online = response.status_code == 200
                
                if not analysis.is_online:
                    analysis.error = f"HTTP {response.status_code}"
                    return analysis
                
                html = response.text.lower()
                
                # Detectar proteções
                analysis.has_cloudflare = any(
                    indicator in html or indicator in str(response.headers).lower()
                    for indicator in self.CLOUDFLARE_INDICATORS
                )
                
                analysis.has_captcha = 'captcha' in html or 'recaptcha' in html
                
                analysis.requires_javascript = any(
                    indicator in html 
                    for indicator in self.JAVASCRIPT_REQUIRED_INDICATORS
                )
                
                # Identificar padrão de URLs
                for pattern in self.PROPERTY_URL_PATTERNS:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        analysis.property_url_pattern = pattern
                        break
                
                # Identificar seletores
                analysis.selectors = self._identify_selectors(response.text)
                
                # Recomendar método
                analysis.recommended_method, analysis.difficulty = self._recommend_method(analysis)
                
                logger.info(
                    f"✅ {analysis.name}: {analysis.recommended_method} "
                    f"({analysis.difficulty}) - {analysis.response_time_ms}ms"
                )
                
        except httpx.TimeoutException:
            analysis.error = "Timeout"
            analysis.is_online = False
            logger.warning(f"⏱️ {analysis.name}: Timeout")
            
        except Exception as e:
            analysis.error = str(e)[:100]
            analysis.is_online = False
            logger.error(f"❌ {analysis.name}: {e}")
        
        return analysis
    
    def _identify_selectors(self, html: str) -> Dict:
        """Tenta identificar seletores CSS comuns."""
        selectors = {}
        
        patterns = {
            'property_card': [r'class="[^"]*(?:card|item|property|imovel|lote)[^"]*"'],
            'price': [r'class="[^"]*(?:price|preco|valor|lance)[^"]*"'],
            'location': [r'class="[^"]*(?:location|local|endereco|cidade)[^"]*"'],
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    class_match = re.search(r'class="([^"]+)"', matches[0])
                    if class_match:
                        selectors[field] = f'.{class_match.group(1).split()[0]}'
                    break
        
        return selectors
    
    def _recommend_method(self, analysis: SiteAnalysis) -> Tuple[str, str]:
        """Recomenda método de scraping."""
        
        if analysis.has_cloudflare and analysis.requires_javascript:
            return "playwright_stealth", "high"
        
        if analysis.requires_javascript:
            return "playwright_simple", "medium"
        
        if analysis.has_cloudflare:
            return "httpx_stealth", "medium"
        
        if analysis.property_url_pattern:
            return "httpx_simple", "low"
        
        return "needs_investigation", "unknown"
    
    async def analyze_batch(self, auctioneers: List[Dict], concurrency: int = 5) -> List[SiteAnalysis]:
        """Analisa um lote de leiloeiros."""
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def analyze_with_semaphore(auctioneer: Dict) -> SiteAnalysis:
            async with semaphore:
                result = await self.analyze_site(auctioneer)
                await asyncio.sleep(1)
                return result
        
        tasks = [analyze_with_semaphore(a) for a in auctioneers]
        self.results = await asyncio.gather(*tasks)
        
        return self.results
    
    def generate_report(self) -> Dict:
        """Gera relatório consolidado."""
        
        online = [r for r in self.results if r.is_online]
        offline = [r for r in self.results if not r.is_online]
        
        by_method = {}
        by_difficulty = {}
        
        for r in online:
            by_method[r.recommended_method] = by_method.get(r.recommended_method, 0) + 1
            by_difficulty[r.difficulty] = by_difficulty.get(r.difficulty, 0) + 1
        
        return {
            "summary": {
                "total_analyzed": len(self.results),
                "online": len(online),
                "offline": len(offline),
                "online_rate": f"{len(online)/max(1,len(self.results))*100:.1f}%"
            },
            "by_method": by_method,
            "by_difficulty": by_difficulty,
            "cloudflare_protected": len([r for r in online if r.has_cloudflare]),
            "javascript_required": len([r for r in online if r.requires_javascript]),
        }
    
    def save_results(self, output_dir: str = "discovery_results"):
        """Salva resultados em arquivos."""
        
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON completo
        results_file = f"{output_dir}/discovery_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in self.results], f, ensure_ascii=False, indent=2)
        
        # Relatório
        report = self.generate_report()
        report_file = f"{output_dir}/report_{timestamp}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Ações prioritárias
        actions_file = f"{output_dir}/actions_{timestamp}.md"
        with open(actions_file, 'w', encoding='utf-8') as f:
            f.write("# Ações Prioritárias - Discovery de Leiloeiros\\n\\n")
            
            f.write("## Resumo\\n\\n")
            for key, value in report['summary'].items():
                f.write(f"- **{key}**: {value}\\n")
            
            f.write("\\n## Prontos para Scraping Simples (httpx)\\n\\n")
            simple = [r for r in self.results if r.recommended_method in ['httpx_simple', 'httpx_stealth']]
            for r in simple[:15]:
                f.write(f"- [ ] {r.name}: `{r.website}`\\n")
            
            f.write("\\n## Precisam de Playwright\\n\\n")
            playwright = [r for r in self.results if 'playwright' in r.recommended_method]
            for r in playwright[:15]:
                f.write(f"- [ ] {r.name}: `{r.website}` ({r.difficulty})\\n")
            
            f.write("\\n## Offline/Erro\\n\\n")
            offline = [r for r in self.results if not r.is_online]
            for r in offline[:15]:
                f.write(f"- {r.name}: {r.error}\\n")
        
        logger.info(f"📄 Resultados salvos em {output_dir}/")
        
        return {"results_file": results_file, "report_file": report_file, "actions_file": actions_file}


def load_auctioneers_from_supabase():
    """Carrega leiloeiros do banco de dados."""
    try:
        # Tentar importar do projeto
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from app.services.postgres_database import PostgresDatabase
        
        db = PostgresDatabase()
        
        # Query para buscar leiloeiros ordenados por property_count
        query = """
            SELECT id, name, website, property_count, scrape_status
            FROM auctioneers 
            WHERE website IS NOT NULL AND website != ''
            ORDER BY COALESCE(property_count, 0) DESC
            LIMIT 60
        """
        
        result = db.execute_query(query)
        
        if result:
            logger.info(f"✅ {len(result)} leiloeiros carregados do banco")
            return [dict(r) for r in result]
        
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível carregar do banco: {e}")
    
    return None


def load_auctioneers_from_csv():
    """Carrega leiloeiros de arquivo CSV."""
    
    # Caminhos possíveis
    csv_paths = [
        "LISTA_MESTRE_LEILOEIROS.csv",
        "../LISTA_MESTRE_LEILOEIROS.csv",
        "../../LISTA_MESTRE_LEILOEIROS.csv",
        "/mnt/project/LISTA_MESTRE_LEILOEIROS.csv",
    ]
    
    for csv_path in csv_paths:
        if os.path.exists(csv_path):
            auctioneers = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('website'):
                        auctioneers.append(row)
            
            # Ordenar por property_count
            auctioneers.sort(
                key=lambda x: int(x.get('property_count', 0) or 0),
                reverse=True
            )
            
            logger.info(f"✅ {len(auctioneers)} leiloeiros carregados de {csv_path}")
            return auctioneers[:60]
    
    return None


def get_hardcoded_top_auctioneers():
    """Lista hardcoded dos principais leiloeiros (fallback)."""
    
    # Top 60 leiloeiros do mercado brasileiro
    return [
        {"id": "1", "name": "Portal Zukerman", "website": "https://www.portalzuk.com.br"},
        {"id": "2", "name": "Mega Leilões", "website": "https://www.megaleiloes.com.br"},
        {"id": "3", "name": "Sodré Santoro", "website": "https://www.sodresantoro.com.br"},
        {"id": "4", "name": "Pestana Leilões", "website": "https://www.pestanaleiloes.com.br"},
        {"id": "5", "name": "Sold Leilões", "website": "https://www.sold.com.br"},
        {"id": "6", "name": "Frazão Leilões", "website": "https://www.frazaoleiloes.com.br"},
        {"id": "7", "name": "Lance no Leilão", "website": "https://www.lancenoleilao.com.br"},
        {"id": "8", "name": "Freitas Leiloeiro", "website": "https://www.freitasleiloeiro.com.br"},
        {"id": "9", "name": "Franco Leilões", "website": "https://www.francoleiloes.com.br"},
        {"id": "10", "name": "Superbid", "website": "https://www.superbid.net"},
        {"id": "11", "name": "Lut Leilões", "website": "https://www.lfreisoleiloes.com.br"},
        {"id": "12", "name": "Biasi Leilões", "website": "https://www.biasileiloes.com.br"},
        {"id": "13", "name": "Milan Leilões", "website": "https://www.milanleiloes.com.br"},
        {"id": "14", "name": "Sato Leilões", "website": "https://www.sfreisoleiloes.com.br"},
        {"id": "15", "name": "Leilões Judiciais", "website": "https://www.leiloesjudiciais.com.br"},
        {"id": "16", "name": "Vip Leilões", "website": "https://www.vfreisoleiloes.com.br"},
        {"id": "17", "name": "Cronos Leilões", "website": "https://www.cronosleiloes.com.br"},
        {"id": "18", "name": "Hayashi Leilões", "website": "https://www.hayashileiloes.com.br"},
        {"id": "19", "name": "Fidalgo Leilões", "website": "https://www.fidalgoleiloes.com.br"},
        {"id": "20", "name": "Al Leilões", "website": "https://www.alleiloes.com.br"},
        {"id": "21", "name": "Flex Leilões", "website": "https://www.flexleiloes.com.br"},
        {"id": "22", "name": "LCA Leilões", "website": "https://www.lcaleiloes.com.br"},
        {"id": "23", "name": "Positivo Leilões", "website": "https://www.positivoleiloes.com.br"},
        {"id": "24", "name": "RJ Leilões", "website": "https://www.rjleiloes.com.br"},
        {"id": "25", "name": "SP Leilões", "website": "https://www.spleiloes.com.br"},
        {"id": "26", "name": "BH Leilões", "website": "https://www.bhleiloes.com.br"},
        {"id": "27", "name": "Curitiba Leilões", "website": "https://www.curitibfileiloes.com.br"},
        {"id": "28", "name": "Salvador Leilões", "website": "https://www.salvadorleiloes.com.br"},
        {"id": "29", "name": "Recife Leilões", "website": "https://www.recifeleiloes.com.br"},
        {"id": "30", "name": "Fortaleza Leilões", "website": "https://www.fortalezaleiloes.com.br"},
        {"id": "31", "name": "Lanceja", "website": "https://www.lanceja.com.br"},
        {"id": "32", "name": "Hasta Pública", "website": "https://www.hastapublica.com.br"},
        {"id": "33", "name": "Leilomaster", "website": "https://www.leilomaster.com.br"},
        {"id": "34", "name": "Bid Leilões", "website": "https://www.bidleiloes.com.br"},
        {"id": "35", "name": "Top Leilões", "website": "https://www.topleiloes.com.br"},
        {"id": "36", "name": "Prime Leilões", "website": "https://www.primeleiloes.com.br"},
        {"id": "37", "name": "Gold Leilões", "website": "https://www.goldleiloes.com.br"},
        {"id": "38", "name": "Master Leilões", "website": "https://www.masterleiloes.com.br"},
        {"id": "39", "name": "Elite Leilões", "website": "https://www.eliteleiloes.com.br"},
        {"id": "40", "name": "Royal Leilões", "website": "https://www.royalleiloes.com.br"},
        {"id": "41", "name": "Turani Leilões", "website": "https://www.turanileiloes.com.br"},
        {"id": "42", "name": "Agostinho Leilões", "website": "https://www.agostinholeiloes.com.br"},
        {"id": "43", "name": "Bianchi Leilões", "website": "https://www.bianchileiloes.com.br"},
        {"id": "44", "name": "Cardoso Leilões", "website": "https://www.cardosoleiloes.com.br"},
        {"id": "45", "name": "Dias Leilões", "website": "https://www.diasleiloes.com.br"},
        {"id": "46", "name": "Ferreira Leilões", "website": "https://www.meulfreisoleiloes.com.br"},
        {"id": "47", "name": "Gomes Leilões", "website": "https://www.gomesleiloes.com.br"},
        {"id": "48", "name": "Henriques Leilões", "website": "https://www.henriquesleiloes.com.br"},
        {"id": "49", "name": "Inova Leilão", "website": "https://www.inovaleilao.com.br"},
        {"id": "50", "name": "Jorge Leilões", "website": "https://www.jorgeleiloes.com.br"},
        {"id": "51", "name": "Lima Leilões", "website": "https://www.limaleiloes.com.br"},
        {"id": "52", "name": "Martins Leilões", "website": "https://www.martinsleiloes.com.br"},
        {"id": "53", "name": "Nunes Leilões", "website": "https://www.nunesleiloes.com.br"},
        {"id": "54", "name": "Oliveira Leilões", "website": "https://www.oliveiraleiloes.com.br"},
        {"id": "55", "name": "Pereira Leilões", "website": "https://www.pereiraleiloes.com.br"},
        {"id": "56", "name": "Queiroz Leilões", "website": "https://www.queirozleiloes.com.br"},
        {"id": "57", "name": "Ribeiro Leilões", "website": "https://www.ribeiroleiloes.com.br"},
        {"id": "58", "name": "Santos Leilões", "website": "https://www.santosleiloes.com.br"},
        {"id": "59", "name": "Teixeira Leilões", "website": "https://www.teixeiraleiloes.com.br"},
        {"id": "60", "name": "Vargas Leilões", "website": "https://www.vargasleiloes.com.br"},
    ]


async def main():
    """Função principal."""
    
    print("=" * 60)
    print("🔍 DISCOVERY INTELIGENTE DE LEILOEIROS")
    print("=" * 60)
    
    # 1. Tentar carregar leiloeiros (em ordem de preferência)
    auctioneers = None
    
    # Opção 1: Do banco de dados
    auctioneers = load_auctioneers_from_supabase()
    
    # Opção 2: Do CSV
    if not auctioneers:
        auctioneers = load_auctioneers_from_csv()
    
    # Opção 3: Lista hardcoded
    if not auctioneers:
        logger.info("📋 Usando lista hardcoded de leiloeiros")
        auctioneers = get_hardcoded_top_auctioneers()
    
    print(f"\\n📋 {len(auctioneers)} leiloeiros para analisar")
    
    # 2. Executar discovery
    discovery = IntelligentDiscovery(timeout=30.0)
    
    print("\\n⏳ Iniciando análise (pode levar alguns minutos)...\\n")
    
    results = await discovery.analyze_batch(auctioneers, concurrency=5)
    
    # 3. Gerar relatório
    report = discovery.generate_report()
    
    print("\\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL")
    print("=" * 60)
    
    print(f"\\n📈 Resumo:")
    for key, value in report['summary'].items():
        print(f"   {key}: {value}")
    
    print(f"\\n🔧 Por método recomendado:")
    for method, count in sorted(report['by_method'].items(), key=lambda x: -x[1]):
        print(f"   - {method}: {count}")
    
    print(f"\\n📊 Por dificuldade:")
    for diff, count in sorted(report['by_difficulty'].items(), key=lambda x: -x[1]):
        print(f"   - {diff}: {count}")
    
    # 4. Salvar resultados
    files = discovery.save_results()
    
    print("\\n" + "=" * 60)
    print("✅ DISCOVERY CONCLUÍDO")
    print("=" * 60)
    
    print("\\n📁 Arquivos gerados:")
    for name, path in files.items():
        print(f"   - {path}")
    
    # 5. Mostrar próximos passos
    print("\\n🎯 PRÓXIMOS PASSOS:")
    
    simple = [r for r in results if r.recommended_method in ['httpx_simple', 'httpx_stealth'] and r.is_online]
    if simple:
        print(f"\\n   1. Scraping Simples ({len(simple)} sites):")
        for r in simple[:5]:
            print(f"      - {r.name}")
    
    playwright = [r for r in results if 'playwright' in r.recommended_method and r.is_online]
    if playwright:
        print(f"\\n   2. Precisam Playwright ({len(playwright)} sites):")
        for r in playwright[:5]:
            print(f"      - {r.name} ({r.difficulty})")
    
    offline = [r for r in results if not r.is_online]
    if offline:
        print(f"\\n   3. Offline/Erro ({len(offline)} sites):")
        for r in offline[:5]:
            print(f"      - {r.name}: {r.error}")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())
'''

# ============================================================
# INSTRUÇÕES PARA O CURSOR AGENT
# ============================================================

print("""
╔══════════════════════════════════════════════════════════════╗
║  TAREFA AUTÔNOMA PARA CURSOR AGENT                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  PASSO 1: Criar o arquivo                                    ║
║  ─────────────────────────────────────────────────────────   ║
║  Crie: app/utils/discovery_leiloeiros.py                     ║
║  Com o conteúdo da variável CODIGO_DISCOVERY acima           ║
║                                                              ║
║  PASSO 2: Executar o discovery                               ║
║  ─────────────────────────────────────────────────────────   ║
║  cd leilao-backend                                           ║
║  python -m app.utils.discovery_leiloeiros                    ║
║                                                              ║
║  PASSO 3: Aguardar conclusão                                 ║
║  ─────────────────────────────────────────────────────────   ║
║  O script analisa ~60 sites (15-20 minutos)                  ║
║                                                              ║
║  PASSO 4: Verificar resultados                               ║
║  ─────────────────────────────────────────────────────────   ║
║  Arquivos em: discovery_results/                             ║
║  - discovery_*.json (análises)                               ║
║  - report_*.json (resumo)                                    ║
║  - actions_*.md (próximos passos)                            ║
║                                                              ║
║  CRITÉRIOS DE SUCESSO:                                       ║
║  □ Script executou sem erros fatais                          ║
║  □ Pasta discovery_results/ criada                           ║
║  □ Pelo menos 1 arquivo JSON gerado                          ║
║  □ Relatório final exibido no console                        ║
║                                                              ║
║  NÃO PARE PARA PERGUNTAR - Execute até o fim!                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

# Salvar o script automaticamente
if __name__ == "__main__":
    import os
    
    # Criar diretório se não existir
    os.makedirs("app/utils", exist_ok=True)
    
    # Salvar o script
    script_path = "app/utils/discovery_leiloeiros.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(CODIGO_DISCOVERY)
    
    print(f"✅ Arquivo criado: {script_path}")
    print(f"\nPara executar:")
    print(f"  python -m app.utils.discovery_leiloeiros")
