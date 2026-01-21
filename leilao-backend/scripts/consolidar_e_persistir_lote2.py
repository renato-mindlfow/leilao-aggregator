#!/usr/bin/env python3
"""
CONSOLIDAÇÃO E PERSISTÊNCIA - LOTE 2
Carrega extrações, deduplica, normaliza e persiste no Supabase
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse

# Credenciais Supabase
DATABASE_URL = "postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeilaoAggregator2025SecurePass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

BASE_DIR = Path(__file__).parent.parent
EXTRACTIONS_DIR = BASE_DIR / "logs" / "extracao_paths_descobertos"

# UFs brasileiras válidas
UFS_VALIDAS = {
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
    'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
}


def normalizar_titulo(titulo: str) -> str:
    """Normaliza título para Title Case"""
    if not titulo:
        return ""
    
    # Remover espaços extras
    titulo = re.sub(r'\s+', ' ', titulo.strip())
    
    # Title Case
    palavras_minusculas = {'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'a', 'o'}
    palavras = titulo.split()
    
    resultado = []
    for i, palavra in enumerate(palavras):
        if i == 0 or palavra.lower() not in palavras_minusculas:
            resultado.append(palavra.capitalize())
        else:
            resultado.append(palavra.lower())
    
    return ' '.join(resultado)


def extrair_uf_de_texto(texto: str) -> str:
    """Extrai UF de um texto (endereço, localização, etc)"""
    if not texto:
        return None
    
    # Procurar padrão "Cidade - UF" ou "UF - Cidade"
    matches = re.findall(r'\b([A-Z]{2})\b', texto.upper())
    
    for match in matches:
        if match in UFS_VALIDAS:
            return match
    
    return None


def extrair_cidade_de_texto(texto: str) -> str:
    """Extrai cidade de um texto"""
    if not texto:
        return None
    
    # Procurar padrão "Cidade - UF"
    match = re.search(r'([A-Za-zÀ-ú\s]+)\s*[-/,]\s*([A-Z]{2})', texto)
    if match:
        cidade = match.group(1).strip()
        return normalizar_titulo(cidade)
    
    return None


def normalizar_categoria(categoria: str) -> str:
    """Normaliza categoria de imóvel"""
    if not categoria:
        return "Outros"
    
    categoria_lower = categoria.lower()
    
    # Mapeamento de categorias
    if any(x in categoria_lower for x in ['casa', 'residencial']):
        return "Casa"
    elif any(x in categoria_lower for x in ['apartamento', 'apto']):
        return "Apartamento"
    elif any(x in categoria_lower for x in ['terreno', 'lote']):
        return "Terreno"
    elif any(x in categoria_lower for x in ['comercial', 'loja', 'sala']):
        return "Comercial"
    elif any(x in categoria_lower for x in ['rural', 'fazenda', 'sítio']):
        return "Rural"
    elif any(x in categoria_lower for x in ['industrial', 'galpão']):
        return "Industrial"
    else:
        return "Outros"


def extrair_preco(texto: str) -> float:
    """Extrai preço de texto (R$ 1.234.567,89)"""
    if not texto:
        return None
    
    # Procurar padrão R$ 1.234.567,89
    match = re.search(r'R\$\s*([\d.,]+)', texto)
    if match:
        preco_str = match.group(1).replace('.', '').replace(',', '.')
        try:
            return float(preco_str)
        except:
            return None
    
    return None


def carregar_extractions(diretorio: Path) -> List[Dict]:
    """Carrega todos os arquivos de extração do diretório"""
    print(f"\n{'='*70}")
    print("📂 CARREGANDO ARQUIVOS DE EXTRAÇÃO")
    print(f"{'='*70}\n")
    
    if not diretorio.exists():
        print(f"❌ Diretório não encontrado: {diretorio}")
        return []
    
    arquivos_json = sorted(diretorio.glob("extracao_*.json"))
    
    if not arquivos_json:
        print(f"❌ Nenhum arquivo de extração encontrado em {diretorio}")
        return []
    
    print(f"📄 Encontrados {len(arquivos_json)} arquivo(s):\n")
    
    todos_resultados = []
    
    for arquivo in arquivos_json:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            resultados = data.get('resultados', [])
            sucessos = sum(1 for r in resultados if r.get('sucesso'))
            total_imoveis = sum(r.get('total_imoveis', 0) for r in resultados if r.get('sucesso'))
            
            print(f"  ✅ {arquivo.name}")
            print(f"     Sites: {len(resultados)} | Sucessos: {sucessos} | Imóveis: {total_imoveis}")
            
            todos_resultados.extend(resultados)
            
        except Exception as e:
            print(f"  ❌ Erro ao carregar {arquivo.name}: {e}")
    
    print(f"\n{'='*70}")
    print(f"📊 Total consolidado: {len(todos_resultados)} resultados de sites")
    print(f"{'='*70}\n")
    
    return todos_resultados


def extrair_imoveis_de_resultados(resultados: List[Dict]) -> List[Dict]:
    """Extrai e normaliza imóveis dos resultados de extração"""
    print(f"\n{'='*70}")
    print("🔨 NORMALIZANDO IMÓVEIS")
    print(f"{'='*70}\n")
    
    imoveis_normalizados = []
    urls_vistas = set()
    
    for resultado in resultados:
        if not resultado.get('sucesso'):
            continue
        
        site_id = resultado.get('site_id')
        nome_site = resultado.get('nome')
        url_site = resultado.get('url')
        imoveis = resultado.get('imoveis', [])
        
        print(f"📍 {nome_site} ({len(imoveis)} imóveis)")
        
        for imovel_url in imoveis:
            # Validar URL
            if not imovel_url or imovel_url in urls_vistas:
                continue
            
            # Garantir URL absoluta
            if not imovel_url.startswith('http'):
                parsed = urlparse(url_site)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                imovel_url = base_url + imovel_url
            
            urls_vistas.add(imovel_url)
            
            # Extrair domínio para usar como auctioneer
            parsed = urlparse(imovel_url)
            dominio = parsed.netloc.replace('www.', '')
            
            # Criar registro normalizado
            imovel_normalizado = {
                'title': f"Imóvel em Leilão - {nome_site}",
                'description': f"Imóvel disponível para leilão através de {nome_site}",
                'url': imovel_url,
                'source_url': url_site,
                'auctioneer': dominio,
                'auctioneer_name': nome_site,
                'category': 'Imóveis',
                'property_type': 'Outros',
                'city': None,
                'state': None,
                'price': None,
                'evaluation_value': None,
                'minimum_bid': None,
                'discount_percentage': None,
                'auction_date': None,
                'images': [],
                'raw_data': {
                    'site_id': site_id,
                    'extracted_at': datetime.now().isoformat()
                }
            }
            
            imoveis_normalizados.append(imovel_normalizado)
    
    print(f"\n✅ {len(imoveis_normalizados)} imóveis normalizados")
    print(f"{'='*70}\n")
    
    return imoveis_normalizados


def carregar_imoveis_existentes(conn) -> Set[str]:
    """Carrega URLs de imóveis já existentes no Supabase"""
    print(f"\n{'='*70}")
    print("📊 CARREGANDO IMÓVEIS EXISTENTES DO SUPABASE")
    print(f"{'='*70}\n")
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM properties")
            total = cur.fetchone()[0]
            print(f"   Total de imóveis no banco: {total:,}")
            
            cur.execute("SELECT url FROM properties")
            urls = {row[0] for row in cur.fetchall()}
            print(f"   URLs únicas carregadas: {len(urls):,}")
            
            return urls
            
    except Exception as e:
        print(f"❌ Erro ao carregar imóveis existentes: {e}")
        return set()


def deduplicar_imoveis(novos_imoveis: List[Dict], urls_existentes: Set[str]) -> List[Dict]:
    """Remove duplicatas (por URL) e filtra imóveis já existentes"""
    print(f"\n{'='*70}")
    print("🔍 DEDUPLICAÇÃO")
    print(f"{'='*70}\n")
    
    print(f"   Imóveis novos (brutos): {len(novos_imoveis):,}")
    print(f"   URLs já no banco: {len(urls_existentes):,}")
    
    # Remover duplicatas internas
    urls_vistas_local = set()
    imoveis_unicos = []
    
    for imovel in novos_imoveis:
        url = imovel.get('url')
        if url and url not in urls_vistas_local:
            urls_vistas_local.add(url)
            imoveis_unicos.append(imovel)
    
    print(f"   Após deduplicação interna: {len(imoveis_unicos):,}")
    
    # Filtrar os que já existem no banco
    imoveis_novos = [
        imovel for imovel in imoveis_unicos
        if imovel.get('url') not in urls_existentes
    ]
    
    duplicatas_banco = len(imoveis_unicos) - len(imoveis_novos)
    
    print(f"   Duplicatas encontradas no banco: {duplicatas_banco:,}")
    print(f"   ✅ Imóveis novos para inserir: {len(imoveis_novos):,}")
    print(f"{'='*70}\n")
    
    return imoveis_novos


def inserir_imoveis_supabase(conn, imoveis: List[Dict]) -> int:
    """Insere imóveis no Supabase usando UPSERT"""
    print(f"\n{'='*70}")
    print("💾 INSERINDO NO SUPABASE")
    print(f"{'='*70}\n")
    
    if not imoveis:
        print("⚠️ Nenhum imóvel para inserir")
        return 0
    
    print(f"   Preparando inserção de {len(imoveis):,} imóveis...")
    
    # Preparar valores para inserção em lotes
    batch_size = 100
    total_inseridos = 0
    
    insert_query = """
        INSERT INTO properties (
            title, description, url, source_url, auctioneer, auctioneer_name,
            category, property_type, city, state, price, evaluation_value,
            minimum_bid, discount_percentage, auction_date, images, raw_data,
            created_at, updated_at
        )
        VALUES %s
        ON CONFLICT (url) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            auctioneer = EXCLUDED.auctioneer,
            auctioneer_name = EXCLUDED.auctioneer_name,
            updated_at = NOW()
        RETURNING id
    """
    
    try:
        with conn.cursor() as cur:
            for i in range(0, len(imoveis), batch_size):
                batch = imoveis[i:i+batch_size]
                
                valores = [
                    (
                        imovel['title'],
                        imovel['description'],
                        imovel['url'],
                        imovel['source_url'],
                        imovel['auctioneer'],
                        imovel['auctioneer_name'],
                        imovel['category'],
                        imovel['property_type'],
                        imovel['city'],
                        imovel['state'],
                        imovel['price'],
                        imovel['evaluation_value'],
                        imovel['minimum_bid'],
                        imovel['discount_percentage'],
                        imovel['auction_date'],
                        json.dumps(imovel['images']) if imovel['images'] else None,
                        json.dumps(imovel['raw_data']) if imovel['raw_data'] else None,
                        datetime.now(),
                        datetime.now()
                    )
                    for imovel in batch
                ]
                
                execute_values(cur, insert_query, valores)
                total_inseridos += len(batch)
                
                print(f"   ✅ Lote {i//batch_size + 1}: {len(batch)} imóveis inseridos ({total_inseridos}/{len(imoveis)})")
            
            conn.commit()
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao inserir: {e}")
        raise
    
    print(f"\n{'='*70}")
    print(f"✅ Total inserido com sucesso: {total_inseridos:,} imóveis")
    print(f"{'='*70}\n")
    
    return total_inseridos


def gerar_relatorio_final(
    total_extraido: int,
    total_normalizado: int,
    total_existente: int,
    total_novo: int,
    total_inserido: int
):
    """Gera relatório final da consolidação"""
    print(f"\n{'='*70}")
    print("📊 RELATÓRIO FINAL - CONSOLIDAÇÃO E PERSISTÊNCIA")
    print(f"{'='*70}\n")
    
    print(f"📥 EXTRAÇÃO:")
    print(f"   Imóveis extraídos (brutos):     {total_extraido:,}")
    print(f"   Imóveis normalizados:           {total_normalizado:,}")
    print()
    
    print(f"🔍 DEDUPLICAÇÃO:")
    print(f"   Imóveis já no banco:            {total_existente:,}")
    print(f"   Duplicatas eliminadas:          {total_normalizado - total_novo:,}")
    print(f"   Imóveis novos identificados:    {total_novo:,}")
    print()
    
    print(f"💾 PERSISTÊNCIA:")
    print(f"   Imóveis inseridos no Supabase:  {total_inserido:,}")
    print(f"   Taxa de sucesso:                {total_inserido/total_novo*100:.1f}%" if total_novo > 0 else "N/A")
    print()
    
    print(f"📈 IMPACTO:")
    antigos = total_existente
    novos_adicionados = total_inserido
    total_final = antigos + novos_adicionados
    crescimento = (novos_adicionados / antigos * 100) if antigos > 0 else 0
    
    print(f"   Antes:  {antigos:,} imóveis")
    print(f"   Depois: {total_final:,} imóveis")
    print(f"   Crescimento: +{novos_adicionados:,} ({crescimento:.1f}%)")
    
    print(f"\n{'='*70}\n")


def main():
    """Função principal"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║      📊 CONSOLIDAÇÃO E PERSISTÊNCIA - LOTE 2               ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  1. Carrega extrações (Lote 1 + Lote 2)                     ║
    ║  2. Normaliza e deduplica                                    ║
    ║  3. Une com dados existentes do Supabase                    ║
    ║  4. Insere novos imóveis via UPSERT                         ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    inicio = datetime.now()
    
    # 1. Carregar extrações
    resultados = carregar_extractions(EXTRACTIONS_DIR)
    
    if not resultados:
        print("❌ Nenhum resultado encontrado para processar")
        return
    
    # 2. Extrair e normalizar imóveis
    imoveis_extraidos = []
    for resultado in resultados:
        if resultado.get('sucesso') and resultado.get('imoveis'):
            imoveis_extraidos.extend(resultado['imoveis'])
    
    total_extraido = len(imoveis_extraidos)
    
    imoveis_normalizados = extrair_imoveis_de_resultados(resultados)
    total_normalizado = len(imoveis_normalizados)
    
    # 3. Conectar ao Supabase
    print(f"🔌 Conectando ao Supabase...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print(f"✅ Conexão estabelecida\n")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return
    
    try:
        # 4. Carregar imóveis existentes
        urls_existentes = carregar_imoveis_existentes(conn)
        total_existente = len(urls_existentes)
        
        # 5. Deduplicar
        imoveis_novos = deduplicar_imoveis(imoveis_normalizados, urls_existentes)
        total_novo = len(imoveis_novos)
        
        # 6. Inserir no Supabase
        if imoveis_novos:
            resposta = input(f"\n⚠️ Confirma inserção de {total_novo:,} novos imóveis no Supabase? (s/n): ")
            
            if resposta.lower() == 's':
                total_inserido = inserir_imoveis_supabase(conn, imoveis_novos)
            else:
                print("\n⚠️ Inserção cancelada pelo usuário")
                total_inserido = 0
        else:
            print("\n⚠️ Nenhum imóvel novo para inserir")
            total_inserido = 0
        
        # 7. Relatório final
        fim = datetime.now()
        duracao = (fim - inicio).total_seconds()
        
        gerar_relatorio_final(
            total_extraido,
            total_normalizado,
            total_existente,
            total_novo,
            total_inserido
        )
        
        print(f"⏱️ Duração total: {duracao//60:.0f}m {duracao%60:.0f}s\n")
        
    finally:
        conn.close()
        print("🔌 Conexão fechada")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
