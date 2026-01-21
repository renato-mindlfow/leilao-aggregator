#!/usr/bin/env python3
"""
Script completo de consolidação, normalização e persistência no Supabase
Fases: 1) Consolidar JSONs 2) Deduplicar 3) Normalizar 4) Validar Imagens 5) Persistir
"""
import json
import os
import re
import hashlib
import sys
from glob import glob
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import logging

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# FASE 1: CONSOLIDAÇÃO E DEDUPLICAÇÃO
# ============================================================================

def carregar_todos_imoveis() -> List[Dict]:
    """Carrega todos os imóveis de todos os tiers."""
    todos = []
    
    # Caminhos dos arquivos (usar o mais recente de cada tipo)
    paths = {
        "TIER 1": "logs/extracao_fase2/tier1/tier1_resultados_20260120_140955.json",
        "TIER 2 (original)": "logs/extracao_fase2/tier2/tier2_resultados_20260120_165411.json",
        "TIER 2 (corrigido)": "logs/extracao_fase2/tier2/tier2_paths_corrigidos_20260120_173543.json",
    }
    
    for nome, filepath in paths.items():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Extrair lista de imóveis (estrutura varia por arquivo)
                imoveis_arquivo = []
                
                if isinstance(data, list):
                    imoveis_arquivo = data
                elif isinstance(data, dict):
                    # Tentar várias chaves possíveis
                    if 'imoveis' in data:
                        imoveis_arquivo = data['imoveis']
                    elif 'properties' in data:
                        imoveis_arquivo = data['properties']
                    elif 'resultados' in data:
                        # TIER 2: extrair de cada resultado
                        for resultado in data['resultados']:
                            if resultado.get('sucesso') and resultado.get('imoveis'):
                                imoveis_arquivo.extend(resultado['imoveis'])
                
                if imoveis_arquivo:
                    todos.extend(imoveis_arquivo)
                    logger.info(f"✅ {nome}: {len(imoveis_arquivo)} imóveis")
                else:
                    logger.warning(f"⚠️ {nome}: 0 imóveis (estrutura não reconhecida)")
                    
        except FileNotFoundError:
            logger.error(f"❌ Arquivo não encontrado: {filepath}")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar {nome}: {e}")
    
    logger.info(f"\n📊 Total bruto carregado: {len(todos)} imóveis")
    return todos

def deduplicar_imoveis(imoveis: List[Dict]) -> List[Dict]:
    """Remove duplicatas por URL e título normalizado."""
    
    vistos_url = set()
    vistos_titulo = set()
    unicos = []
    duplicatas = 0
    
    for imovel in imoveis:
        # Chave primária: URL
        url = (imovel.get('url') or imovel.get('source_url') or '').strip().lower()
        
        # Chave secundária: título + localização
        titulo_raw = imovel.get('title') or imovel.get('texto_card') or ''
        titulo = str(titulo_raw)[:100].strip().lower() if titulo_raw else ''
        cidade = str(imovel.get('city', '')).strip().lower()
        estado = str(imovel.get('state', '')).strip().upper()
        chave_titulo = f"{titulo}|{cidade}|{estado}"
        
        # Verificar duplicata por URL
        if url and url in vistos_url:
            duplicatas += 1
            continue
        
        # Verificar duplicata por título+localização (se não tiver URL)
        if not url and titulo and chave_titulo in vistos_titulo:
            duplicatas += 1
            continue
        
        # Marcar como visto
        if url:
            vistos_url.add(url)
        if titulo and chave_titulo:
            vistos_titulo.add(chave_titulo)
        
        unicos.append(imovel)
    
    logger.info(f"📊 Deduplicação: {len(imoveis)} → {len(unicos)} ({duplicatas} duplicatas removidas)")
    return unicos

# ============================================================================
# FASE 2: NORMALIZAÇÃO DE DADOS
# ============================================================================

def normalizar_titulo(texto: str) -> str:
    """Converte para Title Case inteligente."""
    if not texto:
        return texto
    
    # Palavras que devem ficar minúsculas (exceto início)
    excecoes = {'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'na', 'no', 'nas', 'nos', 'para', 'por', 'com', 'a', 'o'}
    
    palavras = texto.lower().split()
    resultado = []
    
    for i, palavra in enumerate(palavras):
        if i == 0 or palavra not in excecoes:
            resultado.append(palavra.capitalize())
        else:
            resultado.append(palavra)
    
    return ' '.join(resultado)

def normalizar_estado(estado: str) -> str:
    """Normaliza UF para 2 letras maiúsculas."""
    if not estado:
        return None
    
    estado = str(estado).strip().upper()
    
    # Mapeamento de nomes completos para siglas
    mapa_estados = {
        'ACRE': 'AC', 'ALAGOAS': 'AL', 'AMAPA': 'AP', 'AMAZONAS': 'AM',
        'BAHIA': 'BA', 'CEARA': 'CE', 'DISTRITO FEDERAL': 'DF', 'ESPIRITO SANTO': 'ES',
        'GOIAS': 'GO', 'MARANHAO': 'MA', 'MATO GROSSO': 'MT', 'MATO GROSSO DO SUL': 'MS',
        'MINAS GERAIS': 'MG', 'PARA': 'PA', 'PARAIBA': 'PB', 'PARANA': 'PR',
        'PERNAMBUCO': 'PE', 'PIAUI': 'PI', 'RIO DE JANEIRO': 'RJ', 'RIO GRANDE DO NORTE': 'RN',
        'RIO GRANDE DO SUL': 'RS', 'RONDONIA': 'RO', 'RORAIMA': 'RR', 'SANTA CATARINA': 'SC',
        'SAO PAULO': 'SP', 'SERGIPE': 'SE', 'TOCANTINS': 'TO', 'SÃO PAULO': 'SP', 
        'ESPÍRITO SANTO': 'ES', 'PARÁ': 'PA', 'PARANÁ': 'PR', 'GOIÁS': 'GO',
        'RONDÔNIA': 'RO', 'PIAUÍ': 'PI', 'CEARÁ': 'CE', 'AMAPÁ': 'AP',
        'MARANHÃO': 'MA', 'PARAÍBA': 'PB'
    }
    
    # Se já é sigla válida
    estados_validos = set(mapa_estados.values())
    if len(estado) == 2 and estado in estados_validos:
        return estado
    
    # Tentar mapear nome completo
    if estado in mapa_estados:
        return mapa_estados[estado]
    
    # Inválido
    if estado == 'XX' or len(estado) != 2:
        return None
    
    return estado if len(estado) == 2 else None

def normalizar_categoria(categoria: str) -> str:
    """Normaliza categoria para padrão."""
    if not categoria:
        return 'Outro'
    
    categoria = str(categoria).strip().lower()
    
    mapa_categorias = {
        'apartamento': 'Apartamento', 'apto': 'Apartamento', 'apt': 'Apartamento',
        'casa': 'Casa', 'residencia': 'Casa', 'residencial': 'Casa',
        'terreno': 'Terreno', 'lote': 'Terreno',
        'comercial': 'Comercial', 'loja': 'Comercial', 'sala': 'Comercial',
        'galpao': 'Comercial', 'galpão': 'Comercial',
        'rural': 'Rural', 'fazenda': 'Rural', 'sitio': 'Rural', 'sítio': 'Rural',
        'chacara': 'Rural', 'chácara': 'Rural',
        'industrial': 'Industrial',
        'garagem': 'Garagem', 'vaga': 'Garagem',
    }
    
    for chave, valor in mapa_categorias.items():
        if chave in categoria:
            return valor
    
    return 'Outro'

def extrair_localizacao(imovel: Dict) -> Tuple[str, str, str]:
    """Extrai cidade, estado e bairro de várias fontes possíveis."""
    
    # Tentar extrair da URL primeiro
    url = imovel.get('url', imovel.get('source_url', ''))
    
    # Campos diretos
    cidade = imovel.get('city', imovel.get('cidade', ''))
    estado = imovel.get('state', imovel.get('estado', imovel.get('uf', '')))
    bairro = imovel.get('neighborhood', imovel.get('bairro', ''))
    
    # Se tiver texto_card, tentar extrair
    if not (cidade or estado):
        texto = imovel.get('texto_card', imovel.get('title', ''))
        if texto:
            # Procurar padrão "Cidade - UF"
            match = re.search(r'([A-Za-zÀ-ÿ\s]+)\s*[-/,]\s*([A-Z]{2})', texto)
            if match:
                if not cidade:
                    cidade = match.group(1).strip()
                if not estado:
                    estado = match.group(2).strip()
    
    return cidade, estado, bairro

def normalizar_imovel(imovel: Dict) -> Dict:
    """Aplica todas as normalizações em um imóvel."""
    
    # Extrair localização de várias fontes
    cidade, estado, bairro = extrair_localizacao(imovel)
    
    # Title Case
    titulo_raw = imovel.get('title') or imovel.get('texto_card') or ''
    titulo = str(titulo_raw)[:150] if titulo_raw else ''
    if titulo:
        imovel['title'] = normalizar_titulo(titulo)
    
    if cidade:
        imovel['city'] = normalizar_titulo(str(cidade))
    
    if bairro:
        imovel['neighborhood'] = normalizar_titulo(str(bairro))
    
    # Estado (UF)
    if estado:
        imovel['state'] = normalizar_estado(estado)
    
    # Categoria
    categoria = imovel.get('category', imovel.get('tipo', ''))
    imovel['category'] = normalizar_categoria(categoria)
    
    # URL fonte
    if 'url' in imovel and 'source_url' not in imovel:
        imovel['source_url'] = imovel['url']
    
    # Preço
    preco = imovel.get('preco', imovel.get('price', imovel.get('first_auction_value')))
    if preco:
        if isinstance(preco, str):
            try:
                preco = preco.replace('R$', '').replace('.', '').replace(',', '.').strip()
                imovel['first_auction_value'] = float(preco) if preco else None
            except:
                pass
        else:
            imovel['first_auction_value'] = float(preco)
    
    # Tier/Source
    imovel['source'] = imovel.get('tier', 'scraper_fase2')
    
    return imovel

# ============================================================================
# FASE 3: VALIDAÇÃO DE IMAGENS (Simplificada)
# ============================================================================

def validar_imagens_simples(imoveis: List[Dict]) -> List[Dict]:
    """Validação simples de URLs de imagens."""
    
    # Padrões de URLs inválidas conhecidas
    blacklist_patterns = [
        'logo', 'placeholder', 'default', 'no-image', 'sem-imagem',
        'avatar', 'favicon', 'icon', 'thumb', 'blank'
    ]
    
    stats = {'validas': 0, 'invalidas': 0, 'sem_imagem': 0}
    
    for imovel in imoveis:
        url = imovel.get('image_url', '')
        
        if not url:
            stats['sem_imagem'] += 1
            continue
        
        url_lower = url.lower()
        is_invalid = any(pattern in url_lower for pattern in blacklist_patterns)
        
        if is_invalid:
            stats['invalidas'] += 1
            imovel['image_url'] = None
        else:
            stats['validas'] += 1
    
    logger.info(f"\n📊 Validação de imagens:")
    logger.info(f"   ✅ Válidas: {stats['validas']}")
    logger.info(f"   ❌ Inválidas: {stats['invalidas']}")
    logger.info(f"   ⚪ Sem imagem: {stats['sem_imagem']}")
    
    return imoveis

# ============================================================================
# FASE 4: PERSISTÊNCIA NO SUPABASE
# ============================================================================

def gerar_id_unico(imovel: Dict) -> str:
    """Gera ID único baseado na URL ou título+localização."""
    url = imovel.get('source_url', '')
    if url:
        return hashlib.md5(url.encode()).hexdigest()[:32]
    
    # Fallback: título + cidade + estado
    chave = f"{imovel.get('title', '')}|{imovel.get('city', '')}|{imovel.get('state', '')}"
    return hashlib.md5(chave.encode()).hexdigest()[:32]

def mapear_para_schema(imovel: Dict) -> Dict:
    """Mapeia imóvel para schema da tabela properties."""
    
    now = datetime.utcnow().isoformat()
    
    return {
        'id': gerar_id_unico(imovel),
        'title': imovel.get('title'),
        'category': imovel.get('category', 'Outro'),
        'auction_type': imovel.get('auction_type', 'Extrajudicial'),
        'state': imovel.get('state'),
        'city': imovel.get('city'),
        'neighborhood': imovel.get('neighborhood'),
        'address': imovel.get('address'),
        'description': imovel.get('description', imovel.get('texto_card')),
        'area_total': imovel.get('area_total'),
        'area_privativa': imovel.get('area_privativa'),
        'evaluation_value': imovel.get('evaluation_value'),
        'first_auction_value': imovel.get('first_auction_value'),
        'first_auction_date': imovel.get('first_auction_date'),
        'second_auction_value': imovel.get('second_auction_value'),
        'second_auction_date': imovel.get('second_auction_date'),
        'discount_percentage': imovel.get('discount_percentage'),
        'image_url': imovel.get('image_url'),
        'auctioneer_id': imovel.get('auctioneer_id'),
        'auctioneer_name': imovel.get('auctioneer_name', imovel.get('dominio')),
        'auctioneer_url': imovel.get('auctioneer_url', imovel.get('url_base')),
        'source_url': imovel.get('source_url'),
        'source': imovel.get('source', 'scraper_fase2'),
        'is_active': True,
        'is_duplicate': False,
        'created_at': now,
        'updated_at': now,
        'last_seen_at': now,
    }

def inserir_no_supabase(imoveis: List[Dict], batch_size: int = 100) -> Tuple[int, int]:
    """Insere imóveis no Supabase em lotes."""
    
    try:
        from supabase import create_client, Client
        from dotenv import load_dotenv
        
        load_dotenv()
        
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("❌ SUPABASE_URL e SUPABASE_SERVICE_KEY não configurados no .env")
            logger.info("⚠️ Pulando persistência no Supabase")
            return 0, 0
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Conectado ao Supabase")
        
    except ImportError:
        logger.error("❌ Biblioteca supabase não instalada (pip install supabase)")
        logger.info("⚠️ Pulando persistência no Supabase")
        return 0, 0
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao Supabase: {e}")
        return 0, 0
    
    total = len(imoveis)
    inseridos = 0
    erros = 0
    
    logger.info(f"\n🚀 Iniciando inserção de {total} imóveis em lotes de {batch_size}...")
    
    for i in range(0, total, batch_size):
        batch = imoveis[i:i+batch_size]
        registros = [mapear_para_schema(im) for im in batch]
        
        try:
            # Upsert: insere ou atualiza se já existir
            response = supabase.table('properties').upsert(
                registros,
                on_conflict='id'
            ).execute()
            
            inseridos += len(batch)
            logger.info(f"✅ Lote {i//batch_size + 1}: {len(batch)} imóveis ({inseridos}/{total})")
            
        except Exception as e:
            erros += len(batch)
            logger.error(f"❌ Erro no lote {i//batch_size + 1}: {e}")
    
    logger.info(f"\n📊 Resultado final do Supabase:")
    logger.info(f"   ✅ Inseridos: {inseridos}")
    logger.info(f"   ❌ Erros: {erros}")
    logger.info(f"   📊 Total: {total}")
    
    return inseridos, erros

# ============================================================================
# MAIN - EXECUÇÃO COMPLETA
# ============================================================================

def main():
    logger.info("="*80)
    logger.info("🚀 CONSOLIDAÇÃO, NORMALIZAÇÃO E PERSISTÊNCIA - FASE 2")
    logger.info("="*80)
    
    # FASE 1: Consolidação e Deduplicação
    logger.info("\n📋 FASE 1: CONSOLIDAÇÃO E DEDUPLICAÇÃO")
    logger.info("-"*80)
    
    imoveis_brutos = carregar_todos_imoveis()
    imoveis_unicos = deduplicar_imoveis(imoveis_brutos)
    
    # FASE 2: Normalização
    logger.info("\n📋 FASE 2: NORMALIZAÇÃO DE DADOS")
    logger.info("-"*80)
    
    imoveis_normalizados = [normalizar_imovel(im) for im in imoveis_unicos]
    logger.info(f"✅ Normalizados: {len(imoveis_normalizados)} imóveis")
    
    # FASE 3: Validação de Imagens
    logger.info("\n📋 FASE 3: VALIDAÇÃO DE IMAGENS")
    logger.info("-"*80)
    
    imoveis_validados = validar_imagens_simples(imoveis_normalizados)
    
    # Salvar consolidado
    output_file = "logs/extracao_fase2/imoveis_consolidados_final.json"
    resultado = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_imoveis": len(imoveis_validados),
            "fonte": "TIER 1 + TIER 2 (original + corrigido)",
            "deduplicado": True,
            "normalizado": True,
            "imagens_validadas": True
        },
        "imoveis": imoveis_validados
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ Arquivo consolidado salvo: {output_file}")
    
    # FASE 4: Persistência no Supabase
    logger.info("\n📋 FASE 4: PERSISTÊNCIA NO SUPABASE")
    logger.info("-"*80)
    
    inseridos, erros = inserir_no_supabase(imoveis_validados)
    
    # Relatório Final
    logger.info("\n"+"="*80)
    logger.info("📊 RELATÓRIO FINAL")
    logger.info("="*80)
    logger.info(f"Imóveis brutos carregados: {len(imoveis_brutos)}")
    logger.info(f"Imóveis únicos (deduplicados): {len(imoveis_unicos)}")
    logger.info(f"Imóveis normalizados: {len(imoveis_normalizados)}")
    logger.info(f"Imóveis validados: {len(imoveis_validados)}")
    logger.info(f"Imóveis no Supabase: {inseridos}")
    logger.info(f"Erros no Supabase: {erros}")
    logger.info(f"\nArquivo final: {output_file}")
    logger.info("="*80)
    logger.info("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
    logger.info("="*80)

if __name__ == "__main__":
    main()
