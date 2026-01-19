#!/usr/bin/env python3
"""
AUDITORIA COMPLETA DE LEILOEIROS
Execução autônoma - NÃO requer interação humana
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Configurar logging detalhado
LOG_DIR = Path("logs/scraper_audit")
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

# Importar scraper
from app.services.llm_enhanced_scraper import LLMEnhancedScraper

# ============================================================
# LISTA MESTRE DE LEILOEIROS - URLs CONHECIDAS
# ============================================================

LEILOEIROS_MESTRE = [
    # Tier 1: Grandes leiloeiros (alta prioridade)
    {"id": "megaleiloes", "name": "Mega Leilões", "urls": [
        "https://www.megaleiloes.com.br/leiloes-de-imoveis",
        "https://www.megaleiloes.com.br/busca?categoria=imoveis",
    ]},
    {"id": "portalzuk", "name": "Portal Zuk", "urls": [
        "https://www.portalzuk.com.br/leilao-de-imoveis",
        "https://www.portalzuk.com.br/busca?tipo=imovel",
    ]},
    {"id": "sodresantoro", "name": "Sodré Santoro", "urls": [
        "https://www.sodresantoro.com.br/leiloes?c=imoveis",
        "https://www.sodresantoro.com.br/imoveis",
    ]},
    {"id": "superbid", "name": "Superbid", "urls": [
        "https://www.superbid.net/leilao?category=imoveis",
        "https://www.superbid.net/busca?tipo=imovel",
    ]},
    
    # Tier 2: Médios leiloeiros
    {"id": "flexleiloes", "name": "Flex Leilões", "urls": [
        "https://www.flexleiloes.com.br/auctions?property_type=imovel",
    ]},
    {"id": "pestana", "name": "Pestana Leilões", "urls": [
        "https://www.pestanaleiloes.com.br/imoveis",
        "https://www.pestanaleiloes.com.br/leiloes/imoveis",
    ]},
    {"id": "sold", "name": "Sold Leilões", "urls": [
        "https://www.sold.com.br/leiloes/imoveis",
        "https://www.sold.com.br/busca?categoria=imoveis",
    ]},
    {"id": "lancejudicial", "name": "Lance Judicial", "urls": [
        "https://www.lancejudicial.com.br/leiloes/imoveis",
        "https://www.lancejudicial.com.br/busca?tipo=imovel",
    ]},
    {"id": "vivaleiloes", "name": "Viva Leilões", "urls": [
        "https://www.vivaleiloes.com.br/leiloes/imoveis",
        "https://www.vivaleiloes.com.br/busca?tipoBem=1",
    ]},
    
    # Tier 3: Outros leiloeiros
    {"id": "frfranceleiloes", "name": "FR France Leilões", "urls": [
        "https://www.frfranceleiloes.com.br/imoveis",
    ]},
    {"id": "bifranceleiloes", "name": "BI France Leilões", "urls": [
        "https://www.bifranceleiloes.com.br/imoveis",
    ]},
    {"id": "zukerman", "name": "Zukerman Leilões", "urls": [
        "https://www.zfrfranceleiloes.com.br/leiloes/imoveis",
    ]},
    {"id": "leilaoimovel", "name": "Leilão Imóvel", "urls": [
        "https://www.leilaoimovel.com.br/",
    ]},
    {"id": "leilomaster", "name": "Leilomaster", "urls": [
        "https://www.leilomaster.com.br/imoveis",
    ]},
    {"id": "lut", "name": "LUT Leilões", "urls": [
        "https://www.lfrfranceleiloes.com.br/imoveis",
    ]},
    {"id": "frazao", "name": "Frazão Leilões", "urls": [
        "https://www.frazaoleiloes.com.br/imoveis",
    ]},
    {"id": "freitas", "name": "Freitas Leilões", "urls": [
        "https://www.freitasleiloes.com.br/imoveis",
    ]},
    {"id": "franco", "name": "Franco Leilões", "urls": [
        "https://www.francoleiloes.com.br/imoveis",
    ]},
    {"id": "brileiloes", "name": "BRI Leilões", "urls": [
        "https://www.bfrfranceleiloes.com.br/imoveis",
    ]},
]


class AuditoriaLeiloeiros:
    """Executa auditoria completa de todos os leiloeiros."""
    
    def __init__(self):
        self.resultados: Dict[str, Dict] = {}
        self.scraper = None
        self.total_imoveis = 0
        self.inicio = datetime.now()
        
    async def _testar_url(self, url: str, leiloeiro_id: str, leiloeiro_name: str) -> Tuple[bool, int, str]:
        """Testa uma URL específica."""
        try:
            logger.info(f"  Testando: {url}")
            
            if not self.scraper:
                self.scraper = LLMEnhancedScraper(headless=True)
            
            properties = await self.scraper.scrape_url(url, leiloeiro_id, leiloeiro_name)
            
            if properties and len(properties) > 0:
                logger.info(f"  SUCESSO: {len(properties)} imoveis")
                return True, len(properties), url
            else:
                logger.warning(f"  Sem imoveis: {url}")
                return False, 0, "Nenhum imóvel encontrado"
                
        except Exception as e:
            error_msg = str(e)[:200]
            logger.error(f"  ERRO: {error_msg}")
            return False, 0, error_msg
            
    async def testar_leiloeiro(self, leiloeiro: Dict) -> Dict:
        """Testa um leiloeiro tentando múltiplas URLs."""
        lid = leiloeiro["id"]
        name = leiloeiro["name"]
        urls = leiloeiro["urls"]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"LEILOEIRO: {name} ({lid})")
        logger.info(f"{'='*60}")
        
        resultado = {
            "id": lid,
            "name": name,
            "status": "falha",
            "imoveis": 0,
            "url_funcionou": None,
            "urls_testadas": [],
            "erro": None,
        }
        
        for url in urls:
            sucesso, count, msg = await self._testar_url(url, lid, name)
            resultado["urls_testadas"].append({"url": url, "sucesso": sucesso, "count": count, "msg": msg})
            
            if sucesso:
                resultado["status"] = "sucesso"
                resultado["imoveis"] = count
                resultado["url_funcionou"] = url
                self.total_imoveis += count
                break  # Encontrou URL que funciona, para de testar
        
        if resultado["status"] == "falha":
            # Pegar último erro
            if resultado["urls_testadas"]:
                resultado["erro"] = resultado["urls_testadas"][-1]["msg"]
        
        self.resultados[lid] = resultado
        return resultado
        
    async def executar_auditoria(self) -> Dict:
        """Executa auditoria completa de todos os leiloeiros."""
        logger.info("="*60)
        logger.info("AUDITORIA COMPLETA DE LEILOEIROS - INÍCIO")
        logger.info(f"Data: {self.inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total de leiloeiros: {len(LEILOEIROS_MESTRE)}")
        logger.info("="*60)
        
        for i, leiloeiro in enumerate(LEILOEIROS_MESTRE, 1):
            logger.info(f"\n[{i}/{len(LEILOEIROS_MESTRE)}]")
            
            try:
                await self.testar_leiloeiro(leiloeiro)
            except Exception as e:
                logger.error(f"Erro crítico em {leiloeiro['id']}: {e}")
                self.resultados[leiloeiro["id"]] = {
                    "id": leiloeiro["id"],
                    "name": leiloeiro["name"],
                    "status": "erro_critico",
                    "imoveis": 0,
                    "erro": str(e)[:200],
                }
            
            # Fechar browser entre leiloeiros para liberar memória
            if self.scraper:
                try:
                    await self.scraper._close_browser()
                    self.scraper = None
                except:
                    pass
            
            # Pausa entre leiloeiros
            await asyncio.sleep(2)
        
        return self._gerar_relatorio()
        
    def _gerar_relatorio(self) -> Dict:
        """Gera relatório final da auditoria."""
        fim = datetime.now()
        duracao = (fim - self.inicio).total_seconds()
        
        sucessos = [r for r in self.resultados.values() if r["status"] == "sucesso"]
        falhas = [r for r in self.resultados.values() if r["status"] == "falha"]
        erros = [r for r in self.resultados.values() if r["status"] == "erro_critico"]
        
        taxa_sucesso = 100 * len(sucessos) / len(self.resultados) if self.resultados else 0
        
        relatorio = {
            "meta": {
                "inicio": self.inicio.isoformat(),
                "fim": fim.isoformat(),
                "duracao_segundos": duracao,
                "duracao_minutos": duracao / 60,
            },
            "resumo": {
                "total_leiloeiros": len(self.resultados),
                "sucessos": len(sucessos),
                "falhas": len(falhas),
                "erros_criticos": len(erros),
                "taxa_sucesso": round(taxa_sucesso, 1),
                "total_imoveis": self.total_imoveis,
            },
            "leiloeiros_funcionando": [
                {"id": r["id"], "name": r["name"], "imoveis": r["imoveis"], "url": r["url_funcionou"]}
                for r in sucessos
            ],
            "leiloeiros_falhando": [
                {"id": r["id"], "name": r["name"], "erro": r.get("erro", "Desconhecido")}
                for r in falhas + erros
            ],
            "detalhes": self.resultados,
        }
        
        # Salvar relatório JSON
        relatorio_file = LOG_DIR / f"relatorio_{timestamp}.json"
        with open(relatorio_file, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        # Gerar relatório Markdown
        md_file = LOG_DIR / f"RELATORIO_{timestamp}.md"
        self._gerar_markdown(relatorio, md_file)
        
        # Imprimir resumo
        self._imprimir_resumo(relatorio)
        
        return relatorio
        
    def _gerar_markdown(self, relatorio: Dict, filepath: Path):
        """Gera relatório em Markdown."""
        r = relatorio["resumo"]
        
        md = f"""# 📊 Relatório de Auditoria de Leiloeiros

**Data**: {relatorio["meta"]["inicio"][:10]}  
**Duração**: {relatorio["meta"]["duracao_minutos"]:.1f} minutos  

---

## 📈 Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Total de Leiloeiros | {r["total_leiloeiros"]} |
| ✅ Sucesso | {r["sucessos"]} |
| ⚠️ Falha | {r["falhas"]} |
| ❌ Erro Crítico | {r["erros_criticos"]} |
| **Taxa de Sucesso** | **{r["taxa_sucesso"]}%** |
| 🏠 Total de Imóveis | {r["total_imoveis"]} |

---

## ✅ Leiloeiros Funcionando ({r["sucessos"]})

| Leiloeiro | Imóveis | URL |
|-----------|---------|-----|
"""
        for l in relatorio["leiloeiros_funcionando"]:
            md += f"| {l['name']} | {l['imoveis']} | `{l['url'][:50]}...` |\n"
        
        md += f"""
---

## ⚠️ Leiloeiros com Falha ({r["falhas"] + r["erros_criticos"]})

| Leiloeiro | Erro |
|-----------|------|
"""
        for l in relatorio["leiloeiros_falhando"]:
            erro = l['erro'][:80] if l['erro'] else 'Desconhecido'
            md += f"| {l['name']} | {erro} |\n"
        
        md += f"""
---

## 🎯 Próximos Passos

"""
        if r["taxa_sucesso"] >= 70:
            md += "✅ **META ATINGIDA!** Taxa de sucesso >= 70%\n\n"
            md += "O LLMEnhancedScraper está funcionando bem para a maioria dos leiloeiros.\n"
        else:
            md += "⚠️ **META NÃO ATINGIDA** - Taxa de sucesso < 70%\n\n"
            md += "### Ações Recomendadas:\n"
            md += "1. Verificar URLs dos leiloeiros que falharam\n"
            md += "2. Alguns sites podem ter proteção anti-bot mais forte\n"
            md += "3. Considerar criar scrapers específicos para os que falharam\n"
        
        md += f"""
---

## 📁 Arquivos Gerados

- Log completo: `{log_file.name}`
- Relatório JSON: `relatorio_{timestamp}.json`
- Este relatório: `RELATORIO_{timestamp}.md`

---

*Gerado automaticamente pelo sistema de auditoria LeiloHub*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
        
        logger.info(f"\n📄 Relatório Markdown salvo: {filepath}")
        
    def _imprimir_resumo(self, relatorio: Dict):
        """Imprime resumo no console."""
        r = relatorio["resumo"]
        
        print("\n" + "="*60)
        print("RESUMO FINAL DA AUDITORIA")
        print("="*60)
        print(f"\nSucesso: {r['sucessos']}/{r['total_leiloeiros']} ({r['taxa_sucesso']}%)")
        print(f"Falha: {r['falhas']}")
        print(f"Erro: {r['erros_criticos']}")
        print(f"Total imoveis: {r['total_imoveis']}")
        print(f"Duracao: {relatorio['meta']['duracao_minutos']:.1f} min")
        
        print("\n" + "-"*60)
        print("LEILOEIROS FUNCIONANDO:")
        print("-"*60)
        for l in relatorio["leiloeiros_funcionando"]:
            print(f"  {l['name']}: {l['imoveis']} imoveis")
        
        if r["taxa_sucesso"] >= 70:
            print("\n" + "="*60)
            print("META ATINGIDA! Taxa >= 70%")
            print("="*60)
        else:
            print("\n" + "="*60)
            print(f"META NAO ATINGIDA ({r['taxa_sucesso']}% < 70%)")
            print("="*60)


async def main():
    """Função principal."""
    print("="*60)
    print("INICIANDO AUDITORIA COMPLETA DE LEILOEIROS")
    print("="*60)
    print(f"Leiloeiros a testar: {len(LEILOEIROS_MESTRE)}")
    print(f"Tempo estimado: 30-60 minutos")
    print(f"Logs em: {LOG_DIR}")
    print("="*60)
    print("\nExecutando de forma AUTONOMA...")
    print("   Voce pode sair, o processo continuara rodando.\n")
    
    auditoria = AuditoriaLeiloeiros()
    
    try:
        relatorio = await auditoria.executar_auditoria()
        
        # Retornar código de saída baseado no resultado
        if relatorio["resumo"]["taxa_sucesso"] >= 70:
            print("\nAUDITORIA CONCLUIDA COM SUCESSO!")
            sys.exit(0)
        else:
            print("\nAUDITORIA CONCLUIDA - META NAO ATINGIDA")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
