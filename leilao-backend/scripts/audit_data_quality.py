"""
Script de auditoria de qualidade de dados.
Pode ser executado via cron ou manualmente.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")


def audit_data_quality(fix: bool = False) -> dict:
    """
    Audita qualidade dos dados e opcionalmente corrige.
    
    Args:
        fix: Se True, corrige problemas encontrados
        
    Returns:
        Relatório de auditoria
    """
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "fix" if fix else "audit",
        "issues": {},
        "fixed": {} if fix else None,
        "stats": {}
    }
    
    print("=" * 60)
    print(f"AUDITORIA DE QUALIDADE - {report['timestamp']}")
    print(f"Modo: {'CORREÇÃO' if fix else 'APENAS RELATÓRIO'}")
    print("=" * 60)
    
    # 1. Cidades em maiúsculas
    print("\n📍 Verificando cidades...")
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE city = UPPER(city) AND city IS NOT NULL AND LENGTH(city) > 2
    ''')
    count = cur.fetchone()[0]
    report["issues"]["uppercase_cities"] = count
    print(f"   Cidades em MAIÚSCULAS: {count}")
    
    if fix and count > 0:
        cur.execute('UPDATE properties SET city = INITCAP(city) WHERE city = UPPER(city) AND city IS NOT NULL')
        report["fixed"]["uppercase_cities"] = cur.rowcount
        print(f"   ✅ Corrigidas: {cur.rowcount}")
    
    # 2. Bairros em maiúsculas
    print("\n🏘️ Verificando bairros...")
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE neighborhood = UPPER(neighborhood) AND neighborhood IS NOT NULL AND LENGTH(neighborhood) > 2
    ''')
    count = cur.fetchone()[0]
    report["issues"]["uppercase_neighborhoods"] = count
    print(f"   Bairros em MAIÚSCULAS: {count}")
    
    if fix and count > 0:
        cur.execute('UPDATE properties SET neighborhood = INITCAP(neighborhood) WHERE neighborhood = UPPER(neighborhood) AND neighborhood IS NOT NULL')
        report["fixed"]["uppercase_neighborhoods"] = cur.rowcount
        print(f"   ✅ Corrigidos: {cur.rowcount}")
    
    # 3. Imagens inválidas
    print("\n🖼️ Verificando imagens...")
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE image_url LIKE '%%facebook%%'
           OR image_url LIKE '%%logo%%'
           OR image_url LIKE '%%placeholder%%'
           OR image_url LIKE '%%no-image%%'
    ''')
    count = cur.fetchone()[0]
    report["issues"]["invalid_images"] = count
    print(f"   Imagens inválidas: {count}")
    
    if fix and count > 0:
        cur.execute('''
            UPDATE properties SET image_url = NULL
            WHERE image_url LIKE '%%facebook%%'
               OR image_url LIKE '%%logo%%'
               OR image_url LIKE '%%placeholder%%'
               OR image_url LIKE '%%no-image%%'
        ''')
        report["fixed"]["invalid_images"] = cur.rowcount
        print(f"   ✅ Removidas: {cur.rowcount}")
    
    # 4. URLs da Caixa
    print("\n🔗 Verificando URLs da Caixa...")
    cur.execute('''
        SELECT COUNT(*) FROM properties 
        WHERE id LIKE 'caixa-%%'
          AND (source_url IS NULL OR source_url = '')
    ''')
    count = cur.fetchone()[0]
    report["issues"]["missing_caixa_urls"] = count
    print(f"   Caixa sem URL: {count}")
    
    if fix and count > 0:
        cur.execute('''
            UPDATE properties 
            SET source_url = CONCAT('https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=', REPLACE(id, 'caixa-', ''))
            WHERE id LIKE 'caixa-%%'
              AND (source_url IS NULL OR source_url = '')
        ''')
        report["fixed"]["missing_caixa_urls"] = cur.rowcount
        print(f"   ✅ URLs geradas: {cur.rowcount}")
    
    # 5. Estatísticas gerais
    print("\n📊 Estatísticas gerais...")
    
    cur.execute('SELECT COUNT(*) FROM properties')
    report["stats"]["total"] = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM properties WHERE image_url IS NOT NULL AND image_url != \'\'')
    report["stats"]["with_image"] = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM properties WHERE source_url IS NOT NULL AND source_url != \'\'')
    report["stats"]["with_url"] = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(DISTINCT city) FROM properties')
    report["stats"]["unique_cities"] = cur.fetchone()[0]
    
    total = report['stats']['total']
    print(f"   Total de imóveis: {total}")
    if total > 0:
        print(f"   Com imagem: {report['stats']['with_image']} ({100*report['stats']['with_image']/total:.1f}%)")
        print(f"   Com URL: {report['stats']['with_url']} ({100*report['stats']['with_url']/total:.1f}%)")
    else:
        print(f"   Com imagem: {report['stats']['with_image']}")
        print(f"   Com URL: {report['stats']['with_url']}")
    print(f"   Cidades únicas: {report['stats']['unique_cities']}")
    
    if fix:
        conn.commit()
        print("\n✅ Correções aplicadas!")
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 60)
    
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Auditoria de qualidade de dados')
    parser.add_argument('--fix', action='store_true', help='Corrigir problemas encontrados')
    parser.add_argument('--json', action='store_true', help='Saída em JSON')
    args = parser.parse_args()
    
    report = audit_data_quality(fix=args.fix)
    
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))

