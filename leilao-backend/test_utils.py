"""
Testes para as utilidades do scraper.
Execute com: python test_utils.py
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório do backend ao path
sys.path.insert(0, str(Path(__file__).parent / "leilao-backend"))

from app.utils.fetcher import MultiLayerFetcher
from app.utils.image_extractor import extract_images
from app.utils.date_parser import parse_brazilian_date, find_auction_dates
from app.utils.normalizer import (
    normalize_category,
    normalize_state,
    normalize_city,
    normalize_money
)

def test_normalizer():
    print("=== Testando Normalizer ===")
    
    # Categorias
    assert normalize_category("APARTAMENTO") == "Apartamento"
    assert normalize_category("casa residencial") == "Casa"
    assert normalize_category("lote terreno") == "Terreno"
    assert normalize_category("sala comercial") == "Comercial"
    assert normalize_category("xyz123") == "Outros"
    print("✓ Categorias OK")
    
    # Estados
    assert normalize_state("São Paulo") == "SP"
    assert normalize_state("SP") == "SP"
    assert normalize_state("rio de janeiro") == "RJ"
    print("✓ Estados OK")
    
    # Cidades
    assert normalize_city("SAO PAULO") == "São Paulo"
    assert normalize_city("RIO DE JANEIRO") == "Rio de Janeiro"
    print("✓ Cidades OK")
    
    # Valores monetários
    assert normalize_money("R$ 100.000,00") == 100000.0
    assert normalize_money("R&#36; 50.000,00") == 50000.0
    assert normalize_money("1000000") == 1000000.0
    print("✓ Valores OK")
    
    print("\n✅ Todos os testes de Normalizer passaram!")

def test_date_parser():
    print("\n=== Testando Date Parser ===")
    
    # Formato DD/MM/YYYY
    d = parse_brazilian_date("15/01/2025")
    assert d is not None
    assert d.day == 15 and d.month == 1 and d.year == 2025
    print("✓ DD/MM/YYYY OK")
    
    # Com hora
    d = parse_brazilian_date("15/01/2025 às 14h30")
    assert d is not None
    assert d.hour == 14 and d.minute == 30
    print("✓ Com hora OK")
    
    # Por extenso
    d = parse_brazilian_date("15 de janeiro de 2025")
    assert d is not None
    assert d.day == 15 and d.month == 1 and d.year == 2025
    print("✓ Por extenso OK")
    
    # ISO
    d = parse_brazilian_date("2025-01-15T14:00:00")
    assert d is not None
    assert d.day == 15 and d.hour == 14
    print("✓ ISO OK")
    
    print("\n✅ Todos os testes de Date Parser passaram!")

def test_image_extractor():
    print("\n=== Testando Image Extractor ===")
    
    html = '''
    <html>
        <img src="/images/foto1.jpg">
        <img data-src="https://cdn.example.com/foto2.png">
        <div style="background-image: url('https://example.com/bg.webp')">
        <meta property="og:image" content="https://example.com/og.jpg">
    </html>
    '''
    
    images = extract_images(html, "https://example.com/imovel/123")
    
    assert len(images) >= 3  # Deve encontrar pelo menos 3 imagens
    assert any("foto1.jpg" in img or "foto2.png" in img or "og.jpg" in img for img in images)
    print(f"✓ Encontradas {len(images)} imagens")
    
    print("\n✅ Todos os testes de Image Extractor passaram!")

async def test_fetcher():
    print("\n=== Testando Multi-Layer Fetcher ===")
    
    fetcher = MultiLayerFetcher()
    
    # Teste com URL simples
    result = await fetcher.fetch("https://www.google.com")
    
    print(f"  Sucesso: {result.success}")
    print(f"  Layer usado: {result.layer_used.value}")
    print(f"  Tamanho: {result.content_length} chars")
    
    if result.success:
        print("\n✅ Fetcher funcionando!")
    else:
        print(f"\n⚠️ Fetcher falhou: {result.error}")

def main():
    print("=" * 60)
    print("TESTES DAS UTILIDADES DO LEILOHUB SCRAPER")
    print("=" * 60)
    
    test_normalizer()
    test_date_parser()
    test_image_extractor()
    
    # Teste assíncrono
    asyncio.run(test_fetcher())
    
    print("\n" + "=" * 60)
    print("TODOS OS TESTES CONCLUÍDOS!")
    print("=" * 60)

if __name__ == "__main__":
    main()

