#!/usr/bin/env python3
"""
ANÁLISE DE QUALIDADE DOS DADOS
Executa após consolidação para validar qualidade dos imóveis
"""

import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

DATABASE_URL = "postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeilaoAggregator2025SecurePass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


def conectar_banco():
    """Conecta ao Supabase"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("Conexao estabelecida com sucesso\n")
        return conn
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return None


def analisar_campos_obrigatorios(conn):
    """Analisa preenchimento de campos obrigatórios"""
    print("="*70)
    print("1. ANALISE DE CAMPOS OBRIGATORIOS")
    print("="*70 + "\n")
    
    with conn.cursor() as cur:
        # Total de imóveis
        cur.execute("SELECT COUNT(*) FROM properties")
        total = cur.fetchone()[0]
        print(f"Total de imoveis: {total:,}\n")
        
        # Campos obrigatórios
        campos = {
            'title': 'Titulo',
            'url': 'URL',
            'auctioneer': 'Leiloeiro',
            'category': 'Categoria',
            'state': 'Estado (UF)',
            'city': 'Cidade',
            'price': 'Preco',
            'description': 'Descricao'
        }
        
        print("Campo                  | Preenchidos | Vazios | % Qualidade")
        print("-" * 70)
        
        qualidade_geral = []
        
        for campo, nome in campos.items():
            cur.execute(f"""
                SELECT 
                    COUNT(*) FILTER (WHERE {campo} IS NOT NULL AND {campo} != '') as preenchidos,
                    COUNT(*) FILTER (WHERE {campo} IS NULL OR {campo} = '') as vazios
                FROM properties
            """)
            
            preenchidos, vazios = cur.fetchone()
            pct_qualidade = (preenchidos / total * 100) if total > 0 else 0
            qualidade_geral.append(pct_qualidade)
            
            print(f"{nome:<22} | {preenchidos:>11,} | {vazios:>6,} | {pct_qualidade:>6.1f}%")
        
        score_geral = sum(qualidade_geral) / len(qualidade_geral)
        print("-" * 70)
        print(f"SCORE GERAL DE QUALIDADE: {score_geral:.1f}%\n")


def analisar_localizacao(conn):
    """Analisa qualidade de localização"""
    print("="*70)
    print("2. ANALISE DE LOCALIZACAO")
    print("="*70 + "\n")
    
    with conn.cursor() as cur:
        # Sem estado
        cur.execute("SELECT COUNT(*) FROM properties WHERE state IS NULL OR state = ''")
        sem_estado = cur.fetchone()[0]
        
        # Sem cidade
        cur.execute("SELECT COUNT(*) FROM properties WHERE city IS NULL OR city = ''")
        sem_cidade = cur.fetchone()[0]
        
        # Sem geocoding
        cur.execute("SELECT COUNT(*) FROM properties WHERE latitude IS NULL OR longitude IS NULL")
        sem_geocoding = cur.fetchone()[0]
        
        # Total
        cur.execute("SELECT COUNT(*) FROM properties")
        total = cur.fetchone()[0]
        
        print(f"Imoveis sem Estado:     {sem_estado:,} ({sem_estado/total*100:.1f}%)")
        print(f"Imoveis sem Cidade:     {sem_cidade:,} ({sem_cidade/total*100:.1f}%)")
        print(f"Imoveis sem Geocoding:  {sem_geocoding:,} ({sem_geocoding/total*100:.1f}%)")
        print()
        
        # Distribuição por estado
        print("DISTRIBUICAO POR ESTADO (Top 10):")
        print("-" * 50)
        
        cur.execute("""
            SELECT state, COUNT(*) as total
            FROM properties
            WHERE state IS NOT NULL AND state != ''
            GROUP BY state
            ORDER BY total DESC
            LIMIT 10
        """)
        
        for estado, total_estado in cur.fetchall():
            print(f"  {estado}: {total_estado:,} imoveis")
        
        print()


def analisar_precos(conn):
    """Analisa qualidade de preços"""
    print("="*70)
    print("3. ANALISE DE PRECOS")
    print("="*70 + "\n")
    
    with conn.cursor() as cur:
        # Sem preço
        cur.execute("SELECT COUNT(*) FROM properties WHERE price IS NULL OR price = 0")
        sem_preco = cur.fetchone()[0]
        
        # Preços suspeitos (muito baixos)
        cur.execute("SELECT COUNT(*) FROM properties WHERE price > 0 AND price < 1000")
        preco_baixo = cur.fetchone()[0]
        
        # Preços suspeitos (muito altos)
        cur.execute("SELECT COUNT(*) FROM properties WHERE price > 100000000")
        preco_alto = cur.fetchone()[0]
        
        # Estatísticas
        cur.execute("""
            SELECT 
                COUNT(*) as com_preco,
                AVG(price) as media,
                MIN(price) as minimo,
                MAX(price) as maximo,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as mediana
            FROM properties
            WHERE price > 0
        """)
        
        com_preco, media, minimo, maximo, mediana = cur.fetchone()
        
        cur.execute("SELECT COUNT(*) FROM properties")
        total = cur.fetchone()[0]
        
        print(f"Imoveis com preco:       {com_preco:,} ({com_preco/total*100:.1f}%)")
        print(f"Imoveis sem preco:       {sem_preco:,} ({sem_preco/total*100:.1f}%)")
        print(f"Precos suspeitos (< R$ 1k):  {preco_baixo:,}")
        print(f"Precos suspeitos (> R$ 100M): {preco_alto:,}")
        print()
        
        if com_preco > 0:
            print("ESTATISTICAS DE PRECO:")
            print(f"  Media:    R$ {media:,.2f}")
            print(f"  Mediana:  R$ {mediana:,.2f}")
            print(f"  Minimo:   R$ {minimo:,.2f}")
            print(f"  Maximo:   R$ {maximo:,.2f}")
        
        print()


def analisar_por_leiloeiro(conn):
    """Analisa qualidade por leiloeiro"""
    print("="*70)
    print("4. SCORE DE QUALIDADE POR LEILOEIRO")
    print("="*70 + "\n")
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                auctioneer_name,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE state IS NOT NULL AND state != '') as com_estado,
                COUNT(*) FILTER (WHERE city IS NOT NULL AND city != '') as com_cidade,
                COUNT(*) FILTER (WHERE price IS NOT NULL AND price > 0) as com_preco,
                COUNT(*) FILTER (WHERE description IS NOT NULL AND description != '') as com_desc
            FROM properties
            GROUP BY auctioneer_name
            HAVING COUNT(*) >= 10
            ORDER BY COUNT(*) DESC
            LIMIT 20
        """)
        
        print(f"{'Leiloeiro':<30} | Total | Estado | Cidade | Preco | Score")
        print("-" * 80)
        
        for nome, total, com_estado, com_cidade, com_preco, com_desc in cur.fetchall():
            pct_estado = com_estado / total * 100
            pct_cidade = com_cidade / total * 100
            pct_preco = com_preco / total * 100
            
            # Score = média dos 3 principais indicadores
            score = (pct_estado + pct_cidade + pct_preco) / 3
            
            print(f"{nome[:30]:<30} | {total:>5} | {pct_estado:>5.0f}% | {pct_cidade:>5.0f}% | {pct_preco:>4.0f}% | {score:>4.0f}%")
        
        print()


def analisar_duplicatas(conn):
    """Analisa possíveis duplicatas"""
    print("="*70)
    print("5. ANALISE DE DUPLICATAS")
    print("="*70 + "\n")
    
    with conn.cursor() as cur:
        # Duplicatas por URL
        cur.execute("""
            SELECT COUNT(*) 
            FROM (
                SELECT url, COUNT(*) as cnt
                FROM properties
                GROUP BY url
                HAVING COUNT(*) > 1
            ) duplicatas
        """)
        
        duplicatas_url = cur.fetchone()[0]
        
        # Duplicatas por título similar
        cur.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT title, COUNT(*) as cnt
                FROM properties
                WHERE title IS NOT NULL
                GROUP BY title
                HAVING COUNT(*) > 1
            ) duplicatas_titulo
        """)
        
        duplicatas_titulo = cur.fetchone()[0]
        
        print(f"URLs duplicadas:        {duplicatas_url}")
        print(f"Titulos duplicados:     {duplicatas_titulo}")
        
        if duplicatas_url > 0:
            print("\nEXEMPLOS DE URLs DUPLICADAS:")
            cur.execute("""
                SELECT url, COUNT(*) as cnt
                FROM properties
                GROUP BY url
                HAVING COUNT(*) > 1
                ORDER BY cnt DESC
                LIMIT 5
            """)
            
            for url, cnt in cur.fetchall():
                print(f"  {url}: {cnt} ocorrencias")
        
        print()


def analisar_recentes(conn):
    """Analisa imóveis adicionados recentemente"""
    print("="*70)
    print("6. IMOVEIS RECENTES (ULTIMAS 24H)")
    print("="*70 + "\n")
    
    with conn.cursor() as cur:
        # Últimas 24h
        cur.execute("""
            SELECT COUNT(*)
            FROM properties
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        
        ultimas_24h = cur.fetchone()[0]
        
        # Última semana
        cur.execute("""
            SELECT COUNT(*)
            FROM properties
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        
        ultima_semana = cur.fetchone()[0]
        
        print(f"Novos nas ultimas 24h:  {ultimas_24h:,}")
        print(f"Novos na ultima semana: {ultima_semana:,}")
        print()
        
        # Por leiloeiro (últimas 24h)
        if ultimas_24h > 0:
            print("NOVOS POR LEILOEIRO (24h):")
            print("-" * 50)
            
            cur.execute("""
                SELECT auctioneer_name, COUNT(*) as total
                FROM properties
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY auctioneer_name
                ORDER BY total DESC
                LIMIT 10
            """)
            
            for nome, total in cur.fetchall():
                print(f"  {nome}: {total} imoveis")
        
        print()


def gerar_recomendacoes(conn):
    """Gera recomendações de melhoria"""
    print("="*70)
    print("7. RECOMENDACOES DE MELHORIA")
    print("="*70 + "\n")
    
    with conn.cursor() as cur:
        recomendacoes = []
        
        # Sem localização
        cur.execute("SELECT COUNT(*) FROM properties WHERE state IS NULL OR state = ''")
        sem_estado = cur.fetchone()[0]
        
        if sem_estado > 100:
            recomendacoes.append(
                f"1. LOCALIZACAO: {sem_estado:,} imoveis sem estado\n"
                f"   Acao: Melhorar extracao de localizacao dos scrapers"
            )
        
        # Sem preço
        cur.execute("SELECT COUNT(*) FROM properties WHERE price IS NULL OR price = 0")
        sem_preco = cur.fetchone()[0]
        
        if sem_preco > 100:
            recomendacoes.append(
                f"2. PRECOS: {sem_preco:,} imoveis sem preco\n"
                f"   Acao: Melhorar extracao de precos dos scrapers"
            )
        
        # Sem geocoding
        cur.execute("SELECT COUNT(*) FROM properties WHERE latitude IS NULL")
        sem_geocoding = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM properties")
        total = cur.fetchone()[0]
        
        if sem_geocoding > total * 0.8:
            recomendacoes.append(
                f"3. GEOCODING: {sem_geocoding:,} imoveis sem coordenadas ({sem_geocoding/total*100:.1f}%)\n"
                f"   Acao: Executar script de geocoding em lote"
            )
        
        # Descrições vazias
        cur.execute("SELECT COUNT(*) FROM properties WHERE description IS NULL OR description = ''")
        sem_desc = cur.fetchone()[0]
        
        if sem_desc > total * 0.5:
            recomendacoes.append(
                f"4. DESCRICOES: {sem_desc:,} imoveis sem descricao ({sem_desc/total*100:.1f}%)\n"
                f"   Acao: Melhorar extracao de descricoes"
            )
        
        if recomendacoes:
            for rec in recomendacoes:
                print(rec)
                print()
        else:
            print("Nenhuma recomendacao critica. Qualidade dos dados esta boa!")
            print()


def main():
    """Função principal"""
    print("\n" + "="*70)
    print("ANALISE DE QUALIDADE DOS DADOS - LEILOHUB")
    print("="*70 + "\n")
    
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Conectar
    conn = conectar_banco()
    if not conn:
        return
    
    try:
        # Executar análises
        analisar_campos_obrigatorios(conn)
        analisar_localizacao(conn)
        analisar_precos(conn)
        analisar_por_leiloeiro(conn)
        analisar_duplicatas(conn)
        analisar_recentes(conn)
        gerar_recomendacoes(conn)
        
        print("="*70)
        print("ANALISE COMPLETADA")
        print("="*70 + "\n")
        
    finally:
        conn.close()
        print("Conexao fechada\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nErro fatal: {e}")
        import traceback
        traceback.print_exc()
