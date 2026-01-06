#!/usr/bin/env python3
"""
Script de Consolidação e Atualização de Configurações
=====================================================

Consolida resultados dos scrapers e atualiza arquivos de configuração.
"""

import json
import os
from datetime import datetime
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results"
CONFIGS_DIR = Path(__file__).parent.parent / "app" / "configs" / "sites"


def update_config(site_id: str, result: dict):
    """Atualiza arquivo de configuração com resultados do scraping."""
    
    config_path = CONFIGS_DIR / f"{site_id}.json"
    
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"id": site_id}
        
        # Atualizar status
        config["enabled"] = result.get("success", False) and result.get("total_properties", 0) > 0
        config["last_scrape"] = {
            "date": datetime.now().isoformat(),
            "success": result.get("success", False),
            "properties_found": result.get("total_properties", 0),
            "errors_count": len(result.get("errors", []))
        }
        
        if result.get("errors"):
            config["last_scrape"]["errors"] = result.get("errors", [])[:5]  # Limitar a 5 erros
        
        # Atualizar status geral
        if not config.get("enabled"):
            config["status"] = "failed"
            if result.get("errors"):
                config["error"] = result.get("errors", [])[0][:100]  # Primeiro erro
        else:
            config["status"] = "success"
            if "error" in config:
                del config["error"]
        
        # Salvar
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        print(f"   [ERRO] Erro ao atualizar {site_id}: {e}")
        return False


def generate_report(consolidated_file: Path) -> str:
    """Gera relatório markdown a partir do arquivo consolidado."""
    
    with open(consolidated_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    report = f"""# RELATÓRIO DE SCRAPING FINAL - LEILOHUB

**Data de Execução:** {data['data_execucao']}  
**Total de Imóveis Extraídos:** {data['total_imoveis']:,}  
**Fontes Ativas:** {data['resumo']['fontes_ativas']}/6  
**Taxa de Sucesso:** {data['resumo']['taxa_sucesso']}

---

## 📊 RESULTADOS POR FONTE

| Fonte | Esperado | Extraído | Status | Arquivo |
|-------|----------|----------|--------|---------|
"""
    
    expected = {
        "superbid_agregado": "~11.475",
        "portal_zuk": "~949",
        "mega_leiloes": "~650",
        "lance_judicial": "~308",
        "sold": "~143",
        "sodre_santoro": "~28"
    }
    
    names = {
        "superbid_agregado": "Superbid Agregado",
        "portal_zuk": "Portal Zukerman",
        "mega_leiloes": "Mega Leilões",
        "lance_judicial": "Lance Judicial",
        "sold": "Sold Leilões",
        "sodre_santoro": "Sodré Santoro"
    }
    
    for source_id, info in data['por_fonte'].items():
        name = names.get(source_id, source_id)
        exp = expected.get(source_id, "?")
        extracted = info['total']
        status = "✅" if info['success'] else "❌"
        arquivo = info['arquivo']
        
        report += f"| {name} | {exp} | {extracted:,} | {status} | {arquivo} |\n"
    
    total_expected = 13553
    report += f"\n| **TOTAL** | **~{total_expected:,}** | **{data['total_imoveis']:,}** | | |\n"
    
    # Exemplos
    report += "\n---\n\n## 📝 EXEMPLOS DE IMÓVEIS\n\n"
    
    for source_id, info in data['por_fonte'].items():
        if info['total'] > 0:
            result_file = RESULTS_DIR / info['arquivo']
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)
                    properties = result_data.get('properties', [])[:3]
                    
                    if properties:
                        report += f"### {names.get(source_id, source_id)}\n\n"
                        for i, prop in enumerate(properties, 1):
                            title = prop.get('title', prop.get('url', 'N/A'))[:60]
                            price = prop.get('price', 'N/A')
                            location = prop.get('location', 'N/A')
                            url = prop.get('url', 'N/A')
                            
                            report += f"{i}. **{title}**\n"
                            report += f"   - Preço: {price}\n"
                            report += f"   - Localização: {location}\n"
                            report += f"   - URL: {url[:80]}...\n\n"
    
    # Erros
    if data['resumo']['erros']:
        report += "---\n\n## ⚠️ ERROS ENCONTRADOS\n\n"
        for error in data['resumo']['erros'][:20]:
            report += f"- {error}\n"
        if len(data['resumo']['erros']) > 20:
            report += f"\n*... e mais {len(data['resumo']['erros']) - 20} erros*\n"
    
    report += "\n---\n\n## 📁 ARQUIVOS GERADOS\n\n"
    report += "- `scraping_consolidado_final.json` - Dados consolidados\n"
    for source_id, info in data['por_fonte'].items():
        report += f"- `{info['arquivo']}` - {names.get(source_id, source_id)}\n"
    
    return report


def main():
    """Função principal."""
    
    print("="*70)
    print("CONSOLIDAÇÃO E ATUALIZAÇÃO DE CONFIGURAÇÕES")
    print("="*70)
    
    # Carregar consolidado
    consolidated_file = RESULTS_DIR / "scraping_consolidado_final.json"
    
    if not consolidated_file.exists():
        print(f"[ERRO] Arquivo consolidado não encontrado: {consolidated_file}")
        return
    
    with open(consolidated_file, 'r', encoding='utf-8') as f:
        consolidated = json.load(f)
    
    # Mapear IDs
    id_mapping = {
        "superbid_agregado": "superbid_agregado",
        "portal_zuk": "portalzuk",
        "mega_leiloes": "megaleiloes",
        "lance_judicial": "lancejudicial",
        "sold": "sold",
        "sodre_santoro": "sodresantoro"
    }
    
    # Carregar resultados individuais e atualizar configs
    print("\nAtualizando configurações...")
    
    for source_id, info in consolidated['por_fonte'].items():
        config_id = id_mapping.get(source_id, source_id)
        result_file = RESULTS_DIR / info['arquivo']
        
        if result_file.exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            if update_config(config_id, result):
                print(f"   [OK] {config_id}")
            else:
                print(f"   [ERRO] {config_id}")
        else:
            print(f"   [AVISO] Arquivo não encontrado: {result_file}")
    
    # Gerar relatório
    print("\nGerando relatório...")
    report = generate_report(consolidated_file)
    
    report_file = RESULTS_DIR / "RELATORIO_SCRAPING_FINAL.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"   [OK] Relatório salvo: {report_file}")
    
    print("\n" + "="*70)
    print("CONCLUÍDO")
    print("="*70)


if __name__ == "__main__":
    main()

