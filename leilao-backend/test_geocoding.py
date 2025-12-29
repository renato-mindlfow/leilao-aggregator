"""
Testes do serviço de geocoding assíncrono.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

def test_geocoding_service():
    print("=" * 60)
    print("TESTE DO SERVIÇO DE GEOCODING")
    print("=" * 60)
    
    from app.services.async_geocoding_service import AsyncGeocodingService
    
    service = AsyncGeocodingService()
    
    # Testa geocodificação de endereço
    async def test_single():
        result = await service.geocode_address(
            address="Avenida Paulista, 1000",
            city="São Paulo",
            state="SP"
        )
        
        print(f"\nTeste: Av. Paulista, São Paulo")
        print(f"  Sucesso: {result.success}")
        print(f"  Latitude: {result.latitude}")
        print(f"  Longitude: {result.longitude}")
        print(f"  Erro: {result.error}")
        
        if result.success:
            print("✅ Geocoding funcionando!")
        else:
            print("⚠️ Geocoding falhou (pode ser rate limit)")
    
    asyncio.run(test_single())
    
    # Estatísticas
    stats = service.get_stats()
    pending = service.get_pending_count()
    
    print(f"\nEstatísticas:")
    print(f"  Pendentes: {pending}")
    print(f"  Por status: {stats}")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)

def test_image_blacklist():
    print("\n" + "=" * 60)
    print("TESTE DA BLACKLIST DE IMAGENS")
    print("=" * 60)
    
    from app.utils.image_blacklist import is_blacklisted_image, filter_images
    
    test_urls = [
        # Devem ser BLOQUEADAS
        ("https://www.caixa.gov.br/logo.png", True),
        ("https://example.com/images/logo-empresa.jpg", True),
        ("https://example.com/icon_home.png", True),
        ("https://facebook.com/share-icon.png", True),
        ("https://example.com/placeholder.jpg", True),
        ("https://example.com/image_50x50.jpg", True),
        
        # Devem ser PERMITIDAS
        ("https://example.com/imovel/foto1.jpg", False),
        ("https://cdn.leiloeiro.com/fotos/casa-123.jpg", False),
        ("https://example.com/gallery/apartamento.png", False),
    ]
    
    print("\nTestando URLs individuais:")
    for url, expected_blocked in test_urls:
        is_blocked = is_blacklisted_image(url)
        status = "✅" if is_blocked == expected_blocked else "❌"
        expected_text = "BLOQUEAR" if expected_blocked else "PERMITIR"
        result_text = "bloqueada" if is_blocked else "permitida"
        print(f"  {status} {expected_text}: {result_text} - {url[:50]}...")
    
    # Teste de filtro em lote
    all_urls = [url for url, _ in test_urls]
    filtered = filter_images(all_urls)
    
    print(f"\nTeste de filtro em lote:")
    print(f"  URLs originais: {len(all_urls)}")
    print(f"  URLs após filtro: {len(filtered)}")
    print(f"  Removidas: {len(all_urls) - len(filtered)}")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)

if __name__ == "__main__":
    test_image_blacklist()
    test_geocoding_service()

