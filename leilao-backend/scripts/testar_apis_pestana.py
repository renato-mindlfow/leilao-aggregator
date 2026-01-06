"""
Script para testar as APIs encontradas do Pestana Leilões
"""
import asyncio
import httpx
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def testar_apis():
    """Testa as APIs encontradas"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.pestanaleiloes.com.br/procurar-bens?tipoBem=462&lotePage=1&loteQty=50',
        'Origin': 'https://www.pestanaleiloes.com.br',
    }
    
    # APIs encontradas durante o monitoramento
    apis = [
        {
            'name': 'Leilões Privados Ambientes',
            'url': 'https://api.pestanaleiloes.com.br/sgl/v1//leiloes/privados/ambientes/0',
            'method': 'GET',
        },
        {
            'name': 'Leilões Privados Ambientes (com tipoBem)',
            'url': 'https://api.pestanaleiloes.com.br/sgl/v1//leiloes/privados/ambientes/0?tipoBem=462',
            'method': 'GET',
        },
        {
            'name': 'Lotes (tentativa 1)',
            'url': 'https://api.pestanaleiloes.com.br/sgl/v1/lotes?tipoBem=462&page=1&qty=50',
            'method': 'GET',
        },
        {
            'name': 'Lotes (tentativa 2)',
            'url': 'https://api.pestanaleiloes.com.br/sgl/v1/lotes?tipoBem=462',
            'method': 'GET',
        },
        {
            'name': 'Lotes (tentativa 3)',
            'url': 'https://api.pestanaleiloes.com.br/sgl/v1/leiloes/lotes?tipoBem=462',
            'method': 'GET',
        },
        {
            'name': 'Bens por tipo',
            'url': 'https://api.pestanaleiloes.com.br/sgl/v1/bens?tipoBem=462',
            'method': 'GET',
        },
        {
            'name': 'Leilões',
            'url': 'https://api.pestanaleiloes.com.br/sgl/v1/leiloes?tipoBem=462',
            'method': 'GET',
        },
    ]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTANDO APIS DO PESTANA LEILÕES")
    logger.info("="*60)
    
    resultados = []
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for api in apis:
            logger.info(f"\n🔍 Testando: {api['name']}")
            logger.info(f"   URL: {api['url']}")
            
            try:
                if api['method'] == 'GET':
                    response = await client.get(api['url'], headers=headers)
                else:
                    response = await client.post(api['url'], headers=headers)
                
                logger.info(f"   Status: {response.status_code}")
                
                # Tentar parsear como JSON
                try:
                    data = response.json()
                    body_str = json.dumps(data, ensure_ascii=False, indent=2)
                    
                    # Verificar se contém palavras-chave
                    body_lower = body_str.lower()
                    keywords_found = []
                    for keyword in ['lote', 'preco', 'preço', 'valor', 'lance', 'imovel', 'imóvel', 'leilao', 'leilão', 'bem']:
                        if keyword in body_lower:
                            keywords_found.append(keyword)
                    
                    if keywords_found:
                        logger.info(f"   ✅ JSON encontrado com palavras-chave: {', '.join(keywords_found)}")
                        logger.info(f"   📄 Preview: {body_str[:500]}...")
                        
                        resultados.append({
                            'name': api['name'],
                            'url': api['url'],
                            'method': api['method'],
                            'status': response.status_code,
                            'headers_request': dict(headers),
                            'headers_response': dict(response.headers),
                            'body': data,
                            'body_preview': body_str[:1000],
                            'keywords_found': keywords_found,
                        })
                    else:
                        logger.info(f"   ⚠️ JSON retornado mas sem palavras-chave de leilões")
                        logger.info(f"   📄 Preview: {body_str[:200]}...")
                except:
                    # Não é JSON
                    content_type = response.headers.get('content-type', '')
                    logger.info(f"   ⚠️ Não é JSON (Content-Type: {content_type})")
                    logger.info(f"   📄 Preview: {response.text[:200]}...")
                    
            except Exception as e:
                logger.error(f"   ❌ Erro: {e}")
    
    # Resumo
    logger.info(f"\n{'='*60}")
    logger.info(f"RESUMO")
    logger.info("="*60)
    logger.info(f"APIs com dados de leilões encontradas: {len(resultados)}")
    
    if resultados:
        logger.info(f"\n{'='*60}")
        logger.info(f"APIS COM DADOS DE LEILÕES:")
        logger.info("="*60)
        
        for i, resultado in enumerate(resultados, 1):
            logger.info(f"\n{i}. {resultado['name']}")
            logger.info(f"   URL: {resultado['url']}")
            logger.info(f"   Método: {resultado['method']}")
            logger.info(f"   Status: {resultado['status']}")
            logger.info(f"   Palavras-chave: {', '.join(resultado['keywords_found'])}")
            logger.info(f"\n   Headers da Requisição:")
            for key, value in resultado['headers_request'].items():
                logger.info(f"     {key}: {value}")
            logger.info(f"\n   Headers da Resposta:")
            for key, value in resultado['headers_response'].items():
                if key.lower() in ['content-type', 'content-length', 'server', 'date']:
                    logger.info(f"     {key}: {value}")
            logger.info(f"\n   Preview do Body:")
            logger.info(f"     {resultado['body_preview'][:500]}...")
        
        # Salvar resultados
        output_file = 'leilao-backend/scripts/pestana_apis_funcionais.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✅ Resultados salvos em {output_file}")
    else:
        logger.warning("\n⚠️ Nenhuma API funcional encontrada")
    
    return resultados

if __name__ == "__main__":
    asyncio.run(testar_apis())

