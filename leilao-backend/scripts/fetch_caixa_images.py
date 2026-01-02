"""
Job para buscar imagens dos imóveis da Caixa que não têm foto.
Executar periodicamente ou sob demanda.
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import httpx
from bs4 import BeautifulSoup

DATABASE_URL = os.getenv("DATABASE_URL")


async def fetch_caixa_image(imovel_id: str) -> str | None:
    """Busca imagem do site da Caixa."""
    url = f"https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={imovel_id}"
    
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar imagem principal
            # Analisar estrutura do HTML da Caixa para encontrar seletor correto
            
            # Tentar diferentes seletores
            selectors = [
                ('img', {'id': 'imgImovel'}),
                ('img', {'class': 'foto'}),
                ('img', {'class': 'img-responsive'}),
            ]
            
            for tag, attrs in selectors:
                img = soup.find(tag, attrs)
                if img and img.get('src'):
                    src = img['src']
                    # Converter URL relativa para absoluta
                    if src.startswith('/'):
                        src = f"https://venda-imoveis.caixa.gov.br{src}"
                    return src
            
            # Fallback: buscar qualquer imagem que pareça ser do imóvel
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if any(x in src.lower() for x in ['foto', 'imagem', 'imovel', 'property']):
                    if src.startswith('/'):
                        src = f"https://venda-imoveis.caixa.gov.br{src}"
                    return src
            
            return None
            
    except Exception as e:
        return None


async def process_batch(property_ids: list) -> dict:
    """Processa um batch de IDs."""
    results = {}
    
    for prop_id in property_ids:
        imovel_id = prop_id.replace('caixa-', '')
        image_url = await fetch_caixa_image(imovel_id)
        
        if image_url:
            results[prop_id] = image_url
            print(f"  ✅ {prop_id}: {image_url[:50]}...")
        else:
            print(f"  ⏭️ {prop_id}: sem imagem")
        
        # Rate limiting
        await asyncio.sleep(0.5)
    
    return results


def fetch_and_update_images(limit: int = 100):
    """
    Busca e atualiza imagens para imóveis da Caixa sem foto.
    
    Args:
        limit: Número máximo de imóveis a processar por execução
    """
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Buscar imóveis da Caixa sem imagem
    cur.execute('''
        SELECT id FROM properties 
        WHERE id LIKE 'caixa-%%'
          AND (image_url IS NULL OR image_url = '')
        LIMIT %s
    ''', (limit,))
    
    rows = cur.fetchall()
    property_ids = [row[0] for row in rows]
    
    if not property_ids:
        print("✅ Todos os imóveis da Caixa já têm imagem!")
        return
    
    print(f"🔍 Buscando imagens para {len(property_ids)} imóveis...")
    
    # Processar assincronamente
    results = asyncio.run(process_batch(property_ids))
    
    # Atualizar banco
    updated = 0
    for prop_id, image_url in results.items():
        cur.execute(
            'UPDATE properties SET image_url = %s WHERE id = %s',
            (image_url, prop_id)
        )
        updated += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n✅ Imagens atualizadas: {updated} de {len(property_ids)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Buscar imagens da Caixa')
    parser.add_argument('--limit', type=int, default=100, help='Limite de imóveis')
    args = parser.parse_args()
    
    fetch_and_update_images(args.limit)

