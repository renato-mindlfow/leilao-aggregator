"""
Configura estratégia otimizada para Tier 2:
1. Cria config superbid_agregado (já criado)
2. Desabilita sites cobertos pelo agregado
3. Cria configs básicos para sites com sistema próprio
"""
import json
from pathlib import Path

CONFIG_DIR = Path("app/configs/sites")

# Sites cobertos pelo superbid_agregado (store.id: 1161)
SITES_COBERTOS_AGREGADO = [
    "superbid",
    "lancenoleilao",
    "lut",
    "bigleilao",
    "vialeiloes",
    "frazaoleiloes",
    "francoleiloes",
    "leiloesfreire",
    "bfrcontabil",
    "kronbergleiloes",
    "leilomaster",
    "nossoleilao",
    "liderleiloes",
    "leiloesjudiciaisrs",
    "santamarialeiloes",
    "mgleiloes-rs",
    "rochaleiloes",
    "rigolonleiloes",
    "hastalegal",
    "hastapublica",
    "escritoriodeleiloes",
    "grandesleiloes",
    "tonialleiloes",
    "trevisanleiloes",
    "vidalleiloes",
    "webleiloes",
    "zuccalmaglioleiloes",
    "zagoleiloes",
]

# Sites com sistema próprio (requerem config individual)
SITES_PROPRIOS = [
    "freitasleiloeiro",
]

print("="*70)
print("CONFIGURANDO ESTRATÉGIA OTIMIZADA - TIER 2")
print("="*70)

# 1. Desabilitar sites cobertos pelo agregado
print(f"\n[1/3] Desabilitando {len(SITES_COBERTOS_AGREGADO)} sites cobertos pelo agregado...")
disabled_count = 0
for site_id in SITES_COBERTOS_AGREGADO:
    config_file = CONFIG_DIR / f"{site_id}.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['enabled'] = False
        config['notes'] = config.get('notes', [])
        config['notes'].append(f"Desabilitado - coberto por superbid_agregado (store.id: 1161)")
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        disabled_count += 1

print(f"  [OK] {disabled_count} sites desabilitados")

# 2. Configurar sites próprios
print(f"\n[2/3] Configurando {len(SITES_PROPRIOS)} sites com sistema próprio...")

# Freitas Leiloeiro - config básico (será refinado)
freitas_config = {
    "id": "freitasleiloeiro",
    "name": "Freitas Leiloeiro",
    "website": "https://www.freitasleiloeiro.com.br",
    "enabled": True,
    "method": "playwright",
    "listing_url": "/Leiloes",
    "selectors": {
        "card": ".card, .lote-item, [class*='lote']",
        "link": "a[href*='/Leilao/'], a[href*='/Lote/']",
        "title": "h1, h2, .titulo",
        "price": ".valor, .preco, .lance",
        "location": ".endereco, .local",
    },
    "pagination": {
        "type": "query_param",
        "param": "PageNumber"
    },
    "api": {
        "base_url": "https://www.freitasleiloeiro.com.br",
        "endpoints": {
            "listar": "/Leiloes/ListarLeiloes",
            "destaques": "/Leiloes/ListarLeiloesDestaques",
            "pesquisar": "/Leiloes/PesquisarDestaques"
        }
    },
    "notes": [
        "Sistema próprio (ASP.NET MVC)",
        "API própria descoberta: /Leiloes/ListarLeiloes",
        "Requer investigação adicional para filtrar imóveis",
        "Config básico - será refinado após análise completa"
    ]
}

freitas_file = CONFIG_DIR / "freitasleiloeiro.json"
with open(freitas_file, 'w', encoding='utf-8') as f:
    json.dump(freitas_config, f, indent=2, ensure_ascii=False)

print(f"  [OK] Config criado para Freitas Leiloeiro")

# 3. Resumo
print(f"\n[3/3] Resumo da estratégia:")
print(f"  - Scraper agregado: superbid_agregado.json ({len(SITES_COBERTOS_AGREGADO)} sites cobertos)")
print(f"  - Sites próprios: {len(SITES_PROPRIOS)}")
print(f"  - Total sites Tier 2: {len(SITES_COBERTOS_AGREGADO) + len(SITES_PROPRIOS)}")

print("\n" + "="*70)
print("ESTRATÉGIA CONFIGURADA COM SUCESSO!")
print("="*70)
print(f"\nScrapers necessários:")
print(f"  1. superbid_agregado (API) - ~11.475 imóveis")
print(f"  2. freitasleiloeiro (Playwright/API própria) - quantidade a descobrir")
print(f"\nAo invés de 30 scrapers individuais, temos 2 scrapers otimizados!")

