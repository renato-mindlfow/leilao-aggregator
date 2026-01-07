#!/usr/bin/env python3
"""
BUSCA DE IMAGENS FALTANTES - LEILOHUB
Visita páginas de imóveis sem imagem e tenta extrair a URL da imagem.
"""

import os
import re
import sys
import logging
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
from typing import Optional, List, Dict
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Padrões de seletores de imagem por leiloeiro
IMAGE_SELECTORS = {
    "default": [
        'img.property-image',
        'img.imovel-image',
        'img.foto-principal',
        'img[alt*="imóvel"]',
        'img[alt*="imovel"]',
        'img[alt*="foto"]',
        '.gallery img',
        '.carousel img',
        '.slider img',
        '.foto img',
        '.image-container img',
        'figure img',
        'picture img',
        'img[src*="imovel"]',
        'img[src*="property"]',
        'img[src*="foto"]',
        'img[src*="image"]',
        '.swiper img',
        '.owl-carousel img',
    ],
    "caixa": [
        'img.foto-imovel',
        'img[src*="caixa"]',
        '.foto-detalhe img',
        '#foto-principal img',
    ],
    "superbid": [
        'img.offer-image',
        'img[src*="superbid"]',
        '.product-image img',
    ],
}

# URLs/padrões a ignorar (logos, placeholders, etc.)
IGNORE_PATTERNS = [
    'logo', 'icon', 'placeholder', 'default', 'no-image', 'sem-foto',
    'avatar', 'user', 'profile', 'banner', 'header', 'footer',
    'loading', 'spinner', 'transparent', '1x1', 'pixel',
    'facebook', 'twitter', 'instagram', 'whatsapp', 'linkedin',
    '.svg', 'base64', 'data:image'
]

def is_valid_image_url(url: str) -> bool:
    """Verifica se a URL parece ser uma imagem válida de imóvel."""
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Ignorar padrões conhecidos de não-imagens
    for pattern in IGNORE_PATTERNS:
        if pattern in url_lower:
            return False
    
    # Deve ter extensão de imagem ou ser de CDN conhecida
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    has_extension = any(ext in url_lower for ext in valid_extensions)
    
    # CDNs conhecidas
    known_cdns = ['cloudinary', 'cloudfront', 'amazonaws', 'imgix', 'cdn']
    is_cdn = any(cdn in url_lower for cdn in known_cdns)
    
    return has_extension or is_cdn

def extract_image_from_html(html: str, auctioneer_id: str = "default") -> Optional[str]:
    """Extrai URL de imagem do HTML usando múltiplos seletores."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Obter seletores específicos do leiloeiro + padrão
    selectors = IMAGE_SELECTORS.get(auctioneer_id, []) + IMAGE_SELECTORS["default"]
    
    # Tentar cada seletor
    for selector in selectors:
        try:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src and is_valid_image_url(src):
                    # Garantir URL absoluta
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif not src.startswith('http'):
                        continue  # Ignorar URLs relativas por enquanto
                    return src
        except:
            continue
    
    # Fallback: buscar qualquer imagem grande
    all_imgs = soup.find_all('img')
    for img in all_imgs:
        src = img.get('src') or img.get('data-src')
        if src and is_valid_image_url(src):
            # Verificar se parece ser imagem principal (por tamanho ou classe)
            width = img.get('width', '')
            height = img.get('height', '')
            if width and height:
                try:
                    if int(width) >= 200 and int(height) >= 150:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('http'):
                            return src
                except:
                    pass
    
    return None

def fetch_image_for_property(client: httpx.Client, prop: Dict) -> Optional[str]:
    """Busca imagem para um imóvel específico."""
    url = prop.get('source_url')
    if not url:
        return None
    
    try:
        response = client.get(url, timeout=15.0, follow_redirects=True)
        if response.status_code != 200:
            return None
        
        auctioneer_id = prop.get('auctioneer_id', 'default')
        image_url = extract_image_from_html(response.text, auctioneer_id)
        
        return image_url
    except Exception as e:
        logger.debug(f"Erro ao buscar {url}: {e}")
        return None

def main(limit: int = 500, batch_size: int = 50):
    """Busca imagens faltantes para imóveis sem image_url."""
    
    logger.info("=" * 70)
    logger.info("BUSCA DE IMAGENS FALTANTES")
    logger.info("=" * 70)
    
    # Buscar imóveis ativos sem imagem
    response = supabase.table("properties") \
        .select("id, source_url, auctioneer_id, title") \
        .eq("is_active", True) \
        .or_("image_url.is.null,image_url.eq.") \
        .limit(limit) \
        .execute()
    
    if not response.data:
        logger.info("✅ Todos os imóveis ativos já têm imagem!")
        return {"verificados": 0, "atualizados": 0}
    
    logger.info(f"Encontrados {len(response.data)} imóveis sem imagem")
    
    total_atualizados = 0
    total_verificados = 0
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for i in range(0, len(response.data), batch_size):
            batch = response.data[i:i+batch_size]
            logger.info(f"\nProcessando lote {i//batch_size + 1} ({len(batch)} imóveis)...")
            
            for prop in batch:
                total_verificados += 1
                
                image_url = fetch_image_for_property(client, prop)
                
                if image_url:
                    # Atualizar no banco
                    supabase.table("properties") \
                        .update({"image_url": image_url, "updated_at": datetime.now().isoformat()}) \
                        .eq("id", prop["id"]) \
                        .execute()
                    
                    total_atualizados += 1
                    logger.info(f"  ✅ Imagem encontrada: {prop.get('title', 'N/A')[:40]}...")
                
                # Rate limiting
                time.sleep(0.5)
            
            logger.info(f"  Lote concluído: {total_atualizados} imagens encontradas até agora")
    
    logger.info("\n" + "=" * 70)
    logger.info(f"CONCLUÍDO: {total_verificados} verificados, {total_atualizados} imagens atualizadas")
    logger.info("=" * 70)
    
    return {
        "verificados": total_verificados,
        "atualizados": total_atualizados,
        "taxa_sucesso": f"{total_atualizados*100/total_verificados:.1f}%" if total_verificados > 0 else "0%"
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500, help="Limite de imóveis a verificar")
    parser.add_argument("--batch", type=int, default=50, help="Tamanho do lote")
    args = parser.parse_args()
    
    result = main(limit=args.limit, batch_size=args.batch)
    print(f"\nResultado: {result}")

