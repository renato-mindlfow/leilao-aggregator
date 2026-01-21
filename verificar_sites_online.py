#!/usr/bin/env python
"""
verificar_sites_online.py - Verifica rapidamente quais sites estão acessíveis

Uso:
    python verificar_sites_online.py --input sites.txt --output resultado.json
"""

import asyncio
import aiohttp
import json
import argparse
from datetime import datetime
from pathlib import Path


async def verificar_site(session, url, timeout=10):
    """Verifica se um site está online."""
    try:
        # Garantir que URL tem protocolo
        if not url.startswith('http'):
            url = 'https://' + url
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), ssl=False) as response:
            status = response.status
            content_length = len(await response.text())
            
            return {
                'url': url,
                'online': status < 500,
                'status': status,
                'content_length': content_length,
                'erro': None
            }
    except asyncio.TimeoutError:
        return {'url': url, 'online': False, 'erro': 'Timeout'}
    except aiohttp.ClientError as e:
        return {'url': url, 'online': False, 'erro': str(e)[:100]}
    except Exception as e:
        return {'url': url, 'online': False, 'erro': str(e)[:100]}


async def verificar_em_lote(urls, max_concurrent=20):
    """Verifica múltiplos sites em paralelo."""
    connector = aiohttp.TCPConnector(limit=max_concurrent, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [verificar_site(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Verifica sites online')
    parser.add_argument('--input', '-i', required=True, help='Arquivo com URLs (uma por linha)')
    parser.add_argument('--output', '-o', required=True, help='Arquivo JSON de saída')
    parser.add_argument('--concurrent', '-c', type=int, default=20, help='Conexões simultâneas')
    args = parser.parse_args()
    
    # Carregar URLs
    with open(args.input, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"🔍 Verificando {len(urls)} sites...")
    inicio = datetime.now()
    
    # Executar verificação
    resultados = asyncio.run(verificar_em_lote(urls, args.concurrent))
    
    tempo = (datetime.now() - inicio).total_seconds()
    
    # Análise
    online = [r for r in resultados if r['online']]
    offline = [r for r in resultados if not r['online']]
    
    print(f"\n📊 RESULTADO ({tempo:.1f}s):")
    print(f"   ✅ Online: {len(online)} ({len(online)/len(urls)*100:.1f}%)")
    print(f"   ❌ Offline: {len(offline)} ({len(offline)/len(urls)*100:.1f}%)")
    
    # Salvar resultado
    output = {
        'verificado_em': datetime.now().isoformat(),
        'total': len(urls),
        'online': len(online),
        'offline': len(offline),
        'tempo_segundos': tempo,
        'sites_online': [r['url'] for r in online],
        'sites_offline': [{'url': r['url'], 'erro': r['erro']} for r in offline],
        'detalhes': resultados
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Resultado salvo em: {args.output}")
    
    # Salvar apenas URLs online em arquivo texto
    online_txt = Path(args.output).with_suffix('.txt')
    with open(online_txt, 'w') as f:
        f.write('\n'.join([r['url'] for r in online]))
    print(f"✅ URLs online salvas em: {online_txt}")


if __name__ == "__main__":
    main()
