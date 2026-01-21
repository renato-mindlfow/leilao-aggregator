#!/usr/bin/env python3
"""
PREPARACAO PARA GEOCODING EM LOTE
Lista imoveis sem coordenadas e prepara batches para Nominatim
"""

import psycopg2
import json
from datetime import datetime
from pathlib import Path

DATABASE_URL = "postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeilaoAggregator2025SecurePass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
OUTPUT_DIR = Path(__file__).parent.parent / "logs" / "geocoding"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Priorização de estados
ESTADOS_PRIORITARIOS = ['SP', 'RJ', 'MG', 'PR', 'RS', 'SC', 'BA', 'PE', 'CE', 'DF']


def conectar_banco():
    """Conecta ao Supabase"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("Conexao estabelecida\n")
        return conn
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return None


def listar_sem_geocoding(conn):
    """Lista imóveis sem geocoding"""
    print("="*70)
    print("1. IMOVEIS SEM GEOCODING")
    print("="*70 + "\n")
    
    with conn.cursor() as cur:
        # Total sem geocoding
        cur.execute("""
            SELECT COUNT(*)
            FROM properties
            WHERE latitude IS NULL OR longitude IS NULL
        """)
        total_sem = cur.fetchone()[0]
        
        # Total geral
        cur.execute("SELECT COUNT(*) FROM properties")
        total = cur.fetchone()[0]
        
        print(f"Total de imoveis:           {total:,}")
        print(f"Imoveis sem geocoding:      {total_sem:,} ({total_sem/total*100:.1f}%)")
        print(f"Imoveis com geocoding:      {total-total_sem:,} ({(total-total_sem)/total*100:.1f}%)")
        print()
        
        # Por estado
        print("DISTRIBUICAO POR ESTADO:")
        print("-" * 50)
        
        cur.execute("""
            SELECT 
                state,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE latitude IS NULL) as sem_geocoding,
                COUNT(*) FILTER (WHERE latitude IS NOT NULL) as com_geocoding
            FROM properties
            WHERE state IS NOT NULL AND state != ''
            GROUP BY state
            ORDER BY total DESC
        """)
        
        for estado, total_est, sem_geo, com_geo in cur.fetchall():
            pct_sem = sem_geo / total_est * 100 if total_est > 0 else 0
            print(f"  {estado}: {total_est:>5,} imoveis | Sem geocoding: {sem_geo:>5,} ({pct_sem:.0f}%)")
        
        print()
        
        return total_sem


def preparar_batches_prioritarios(conn):
    """Prepara batches priorizando estados importantes"""
    print("="*70)
    print("2. PREPARACAO DE BATCHES PRIORITARIOS")
    print("="*70 + "\n")
    
    batches = {}
    
    with conn.cursor() as cur:
        for estado in ESTADOS_PRIORITARIOS:
            cur.execute("""
                SELECT 
                    id,
                    title,
                    city,
                    state,
                    auctioneer_name,
                    url
                FROM properties
                WHERE state = %s
                  AND (latitude IS NULL OR longitude IS NULL)
                  AND city IS NOT NULL
                  AND city != ''
                ORDER BY created_at DESC
                LIMIT 500
            """, (estado,))
            
            imoveis = []
            for row in cur.fetchall():
                imoveis.append({
                    'id': row[0],
                    'title': row[1],
                    'city': row[2],
                    'state': row[3],
                    'auctioneer': row[4],
                    'url': row[5],
                    'query': f"{row[2]}, {row[3]}, Brasil"
                })
            
            if imoveis:
                batches[estado] = imoveis
                print(f"  {estado}: {len(imoveis)} imoveis preparados")
        
        print()
        
        # Imoveis sem estado mas com cidade
        cur.execute("""
            SELECT 
                id,
                title,
                city,
                auctioneer_name,
                url
            FROM properties
            WHERE (latitude IS NULL OR longitude IS NULL)
              AND (state IS NULL OR state = '')
              AND city IS NOT NULL
              AND city != ''
            ORDER BY created_at DESC
            LIMIT 200
        """)
        
        imoveis_sem_estado = []
        for row in cur.fetchall():
            imoveis_sem_estado.append({
                'id': row[0],
                'title': row[1],
                'city': row[2],
                'state': None,
                'auctioneer': row[3],
                'url': row[4],
                'query': f"{row[2]}, Brasil"
            })
        
        if imoveis_sem_estado:
            batches['SEM_ESTADO'] = imoveis_sem_estado
            print(f"  SEM_ESTADO: {len(imoveis_sem_estado)} imoveis preparados")
        
        print()
    
    return batches


def salvar_batches(batches):
    """Salva batches em arquivos JSON"""
    print("="*70)
    print("3. SALVANDO BATCHES")
    print("="*70 + "\n")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Salvar cada batch
    for estado, imoveis in batches.items():
        filename = OUTPUT_DIR / f"batch_{estado}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'estado': estado,
                'total': len(imoveis),
                'timestamp': datetime.now().isoformat(),
                'imoveis': imoveis
            }, f, ensure_ascii=False, indent=2)
        
        print(f"  Salvo: {filename.name} ({len(imoveis)} imoveis)")
    
    # Criar batch consolidado (top 1000)
    todos_imoveis = []
    for estado in ESTADOS_PRIORITARIOS:
        if estado in batches:
            todos_imoveis.extend(batches[estado][:100])  # Top 100 por estado prioritário
    
    if todos_imoveis:
        filename_consolidado = OUTPUT_DIR / f"batch_consolidado_{timestamp}.json"
        
        with open(filename_consolidado, 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(todos_imoveis),
                'timestamp': datetime.now().isoformat(),
                'descricao': 'Top 100 imoveis por estado prioritario',
                'imoveis': todos_imoveis
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n  Consolidado: {filename_consolidado.name} ({len(todos_imoveis)} imoveis)")
    
    print()
    
    return filename_consolidado if todos_imoveis else None


def gerar_script_geocoding(batch_consolidado):
    """Gera script Python para executar geocoding"""
    print("="*70)
    print("4. GERANDO SCRIPT DE GEOCODING")
    print("="*70 + "\n")
    
    script_path = OUTPUT_DIR / "executar_geocoding.py"
    
    script_content = f"""#!/usr/bin/env python3
\"\"\"
EXECUTAR GEOCODING EM LOTE
Usa Nominatim para geocodificar imoveis
\"\"\"

import json
import time
import psycopg2
from geopy.geocoders import Nominatim
from pathlib import Path

DATABASE_URL = "postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeilaoAggregator2025SecurePass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
BATCH_FILE = Path(__file__).parent / "{batch_consolidado.name if batch_consolidado else 'batch_consolidado.json'}"

# Configurar Nominatim
geolocator = Nominatim(user_agent="leilohub_geocoder/1.0")

def carregar_batch():
    \"\"\"Carrega batch de imoveis\"\"\"
    with open(BATCH_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['imoveis']

def geocodificar_imovel(imovel):
    \"\"\"Geocodifica um imovel\"\"\"
    try:
        location = geolocator.geocode(imovel['query'], timeout=10)
        
        if location:
            return {{
                'latitude': location.latitude,
                'longitude': location.longitude,
                'endereco_completo': location.address
            }}
        else:
            return None
            
    except Exception as e:
        print(f"  Erro: {{str(e)[:50]}}")
        return None

def atualizar_banco(conn, imovel_id, geo_data):
    \"\"\"Atualiza coordenadas no banco\"\"\"
    with conn.cursor() as cur:
        cur.execute(\"\"\"
            UPDATE properties
            SET latitude = %s,
                longitude = %s,
                updated_at = NOW()
            WHERE id = %s
        \"\"\", (geo_data['latitude'], geo_data['longitude'], imovel_id))
    conn.commit()

def main():
    print("\\n" + "="*70)
    print("GEOCODING EM LOTE - NOMINATIM")
    print("="*70 + "\\n")
    
    # Carregar batch
    imoveis = carregar_batch()
    print(f"Carregados: {{len(imoveis)}} imoveis\\n")
    
    # Conectar ao banco
    conn = psycopg2.connect(DATABASE_URL)
    print("Conectado ao Supabase\\n")
    
    sucessos = 0
    falhas = 0
    
    try:
        for i, imovel in enumerate(imoveis, 1):
            print(f"[{{i}}/{{len(imoveis)}}] {{imovel['city']}}, {{imovel['state']}}")
            
            geo_data = geocodificar_imovel(imovel)
            
            if geo_data:
                atualizar_banco(conn, imovel['id'], geo_data)
                print(f"  OK: {{geo_data['latitude']}}, {{geo_data['longitude']}}")
                sucessos += 1
            else:
                print(f"  FALHA: Localizacao nao encontrada")
                falhas += 1
            
            # Respeitar rate limit do Nominatim (1 req/sec)
            time.sleep(1.1)
            
            # A cada 50, mostrar progresso
            if i % 50 == 0:
                print(f"\\n--- Progresso: {{i}}/{{len(imoveis)}} | Sucessos: {{sucessos}} | Falhas: {{falhas}} ---\\n")
        
    finally:
        conn.close()
    
    print("\\n" + "="*70)
    print("GEOCODING COMPLETADO")
    print("="*70)
    print(f"Total:    {{len(imoveis)}}")
    print(f"Sucessos: {{sucessos}} ({{sucessos/len(imoveis)*100:.1f}}%)")
    print(f"Falhas:   {{falhas}} ({{falhas/len(imoveis)*100:.1f}}%)")
    print("="*70 + "\\n")

if __name__ == "__main__":
    main()
"""
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"  Script gerado: {script_path.name}")
    print(f"\n  Para executar:")
    print(f"  1. Instalar geopy: pip install geopy")
    print(f"  2. Executar: python {script_path}")
    print(f"\n  ATENCAO: Nominatim tem limite de 1 req/seg")
    print(f"  Tempo estimado: ~{len(batches.get('SP', [])[:100]) if batches else 0} minutos")
    print()


def gerar_relatorio(total_sem_geo):
    """Gera relatório final"""
    print("="*70)
    print("5. RESUMO E RECOMENDACOES")
    print("="*70 + "\n")
    
    print(f"Total sem geocoding: {total_sem_geo:,} imoveis")
    print()
    
    print("ESTRATEGIA RECOMENDADA:")
    print()
    print("1. FASE 1 - Estados Prioritarios (SP, RJ, MG, PR, RS)")
    print("   Execute: python logs/geocoding/executar_geocoding.py")
    print("   Tempo: ~15-20 minutos (1000 imoveis)")
    print()
    print("2. FASE 2 - Demais Estados")
    print("   Execute batches individuais por estado")
    print("   Tempo: ~2-3 horas (todos os estados)")
    print()
    print("3. FASE 3 - Imoveis Sem Estado")
    print("   Execute batch SEM_ESTADO")
    print("   Tempo: ~5-10 minutos")
    print()
    
    print("ALTERNATIVAS:")
    print("  - Google Maps API (paga, mais rapida, mais precisa)")
    print("  - HERE API (freemium, bons limites)")
    print("  - OpenCage API (freemium)")
    print()


def main():
    """Função principal"""
    print("\n" + "="*70)
    print("PREPARACAO PARA GEOCODING EM LOTE")
    print("="*70 + "\n")
    
    # Conectar
    conn = conectar_banco()
    if not conn:
        return
    
    try:
        # Listar imoveis sem geocoding
        total_sem_geo = listar_sem_geocoding(conn)
        
        if total_sem_geo == 0:
            print("Todos os imoveis ja tem geocoding!")
            return
        
        # Preparar batches
        batches = preparar_batches_prioritarios(conn)
        
        # Salvar batches
        batch_consolidado = salvar_batches(batches)
        
        # Gerar script de execução
        gerar_script_geocoding(batch_consolidado)
        
        # Relatório final
        gerar_relatorio(total_sem_geo)
        
        print("="*70)
        print("PREPARACAO COMPLETADA")
        print("="*70 + "\n")
        
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nErro fatal: {e}")
        import traceback
        traceback.print_exc()
