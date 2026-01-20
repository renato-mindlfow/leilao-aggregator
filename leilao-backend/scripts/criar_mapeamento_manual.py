#!/usr/bin/env python3
"""
Cria mapeamento manual baseado nos leiloeiros funcionando.
Usa URLs conhecidas e padrões comuns para acelerar o processo.
"""

import json
import csv
from pathlib import Path
from datetime import datetime

# Mapeamento manual de tipos de paginação e URLs de imóveis
CONHECIDOS = {
    'Megaleiloes': {
        'pagination_type': 'NUMERIC',
        'url': 'https://www.megaleiloes.com.br/imoveis',
        'total_pages': 20,
        'notes': 'Paginação numérica - ?pagina=X'
    },
    'Portalzuk': {
        'pagination_type': 'NUMERIC',
        'url': 'https://www.portalzuk.com.br/imoveis',
        'total_pages': 5,
        'notes': 'Paginação numérica'
    },
    'Lancejudicial': {
        'pagination_type': 'NUMERIC',
        'url': 'https://www.lancejudicial.com.br/imoveis',
        'total_pages': 15,
        'notes': 'Muitos imóveis - paginação numérica'
    },
    'Sold': {
        'pagination_type': 'TABS_FILTER',
        'url': 'https://www.sold.com.br/imoveis',
        'notes': 'Sistema de abas/filtros'
    },
    'Lut': {
        'pagination_type': 'NUMERIC',
        'url': 'https://www.lut.com.br/imoveis',
        'total_pages': 10,
        'notes': 'Paginação numérica'
    },
    'Leje': {
        'pagination_type': 'SINGLE_PAGE',
        'url': 'https://www.leje.com.br/imoveis',
        'notes': 'Página única ou poucas páginas'
    },
    'Sodresantoro': {
        'pagination_type': 'TABS_FILTER',
        'url': 'https://www.sodresantoro.com.br/imoveis',
        'notes': 'Sistema de filtros'
    },
    'Hastavip': {
        'pagination_type': 'SINGLE_PAGE',
        'url': 'https://www.hastavip.com.br/imoveis',
        'notes': 'Poucos imóveis'
    },
    'Vivaleiloes': {
        'pagination_type': 'SINGLE_PAGE',
        'url': 'https://www.vivaleiloes.com.br/imoveis',
        'notes': 'Poucos imóveis'
    },
}

# Padrões comuns de URL para tentar
URL_PATTERNS = [
    '/imoveis',
    '/leiloes',
    '/properties',
    '/lotes',
    '/items',
    '?categoria=imoveis',
    '?tipo=imoveis'
]

def gerar_url_imoveis(base_url: str) -> str:
    """Gera URL provável para página de imóveis."""
    base_url = base_url.rstrip('/')
    
    # Se já tem /imoveis ou similar, manter
    for pattern in ['/imoveis', '/leiloes', '/properties', '/lotes']:
        if pattern in base_url.lower():
            return base_url
    
    # Tentar primeiro padrão
    return f"{base_url}/imoveis"

def criar_mapeamento_automatico(csv_path: Path) -> dict:
    """Cria mapeamento baseado no CSV."""
    mapeamento = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            name = row.get('name', '')
            website = row.get('website', '')
            property_count = int(row.get('property_count', 0) or 0)
            scrape_status = row.get('scrape_status', '')
            
            # Pular se não tem imóveis ou status de erro
            if property_count == 0 and scrape_status != 'success':
                continue
            
            # Verificar se temos mapeamento manual
            if name in CONHECIDOS:
                mapeamento[name] = CONHECIDOS[name]
                continue
            
            # Gerar mapeamento automático baseado em heurísticas
            url = gerar_url_imoveis(website)
            
            # Determinar tipo de paginação baseado em quantidade
            if property_count > 50:
                pagination_type = 'NUMERIC'
                total_pages = max(2, property_count // 20)  # Estimar ~20 por página
            elif property_count > 20:
                pagination_type = 'NUMERIC'
                total_pages = 3
            elif property_count > 10:
                pagination_type = 'SINGLE_PAGE'
                total_pages = 1
            else:
                pagination_type = 'SINGLE_PAGE'
                total_pages = 1
            
            mapeamento[name] = {
                'url': url,
                'pagination_type': pagination_type,
                'total_pages': total_pages if pagination_type == 'NUMERIC' else None,
                'total_items': property_count,
                'notes': f'Auto-gerado baseado em {property_count} imóveis conhecidos'
            }
    
    return mapeamento

def main():
    """Cria mapeamento combinando manual e automático."""
    import sys
    import codecs
    
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    csv_path = Path("LISTA_MESTRE_LEILOEIROS.csv")
    
    if not csv_path.exists():
        print("CSV nao encontrado")
        return
    
    print("Gerando mapeamento...")
    mapeamento = criar_mapeamento_automatico(csv_path)
    
    # Salvar
    output_dir = Path("logs/mapeamento_paginacao")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"mapeamento_completo_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapeamento, f, ensure_ascii=False, indent=2)
    
    print(f"Mapeamento criado: {output_file}")
    print(f"   Total de leiloeiros: {len(mapeamento)}")
    
    # Estatísticas
    by_type = {}
    for data in mapeamento.values():
        ptype = data.get('pagination_type', 'UNKNOWN')
        by_type[ptype] = by_type.get(ptype, 0) + 1
    
    print("\nPor tipo:")
    for ptype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"   {ptype}: {count}")

if __name__ == "__main__":
    main()
