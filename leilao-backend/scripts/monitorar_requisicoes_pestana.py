"""
Script para monitorar requisições de rede do site Pestana Leilões
e identificar APIs que retornam JSON com dados de leilões
"""
import asyncio
import json
import logging
from playwright.async_api import async_playwright
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def monitorar_requisicoes():
    """Monitora requisições de rede do site Pestana"""
    
    url = "https://www.pestanaleiloes.com.br/procurar-bens?tipoBem=462&lotePage=1&loteQty=50"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"MONITORANDO REQUISIÇÕES DE REDE - PESTANA LEILÕES")
    logger.info(f"URL: {url}")
    logger.info("="*60)
    
    apis_encontradas = []
    todas_requisicoes = []
    
    async with async_playwright() as p:
        # Configurar browser com stealth
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
        )
        
        page = await context.new_page()
        
        # Injetar scripts de stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)
        
        # Interceptar todas as requisições e respostas
        async def handle_request(request):
            url_req = request.url
            method = request.method
            headers = request.headers
            
            # Filtrar apenas requisições que podem ser APIs
            if any(keyword in url_req.lower() for keyword in ['api', 'json', 'ajax', 'rest', 'graphql', 'lote', 'imovel', 'leilao', 'bem']):
                todas_requisicoes.append({
                    'type': 'request',
                    'url': url_req,
                    'method': method,
                    'headers': headers,
                })
                logger.info(f"\n📤 REQUEST: {method} {url_req}")
        
        async def handle_response(response):
            url_resp = response.url
            status = response.status
            content_type = response.headers.get('content-type', '')
            
            # Verificar se é JSON
            if 'application/json' in content_type or 'text/json' in content_type:
                try:
                    body = await response.text()
                    # Tentar parsear JSON
                    try:
                        data = json.loads(body)
                        body_str = json.dumps(data, ensure_ascii=False)
                    except:
                        body_str = body
                    
                    # Procurar por palavras-chave
                    body_lower = body_str.lower()
                    if any(keyword in body_lower for keyword in ['lote', 'preco', 'preço', 'valor', 'lance', 'imovel', 'imóvel', 'leilao', 'leilão']):
                        headers = response.headers
                        
                        api_info = {
                            'url': url_resp,
                            'method': response.request.method,
                            'status': status,
                            'content_type': content_type,
                            'headers_request': dict(response.request.headers),
                            'headers_response': dict(headers),
                            'body_preview': body_str[:500] if len(body_str) > 500 else body_str,
                            'body_full_length': len(body_str),
                        }
                        
                        apis_encontradas.append(api_info)
                        
                        logger.info(f"\n{'='*60}")
                        logger.info(f"✅ API JSON ENCONTRADA!")
                        logger.info(f"URL: {url_resp}")
                        logger.info(f"Status: {status}")
                        logger.info(f"Content-Type: {content_type}")
                        logger.info(f"Body Preview: {body_str[:200]}...")
                        logger.info("="*60)
                        
                except Exception as e:
                    logger.debug(f"Erro ao processar resposta JSON: {e}")
        
        # Registrar handlers
        page.on('request', handle_request)
        page.on('response', handle_response)
        
        # Navegar para a página
        logger.info("\n🌐 Navegando para a página...")
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            logger.info("✅ Página carregada")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar página: {e}")
        
        # Aguardar um pouco para capturar requisições assíncronas
        logger.info("\n⏳ Aguardando requisições assíncronas...")
        await asyncio.sleep(10)
        
        # Tentar fazer scroll para carregar mais conteúdo
        logger.info("📜 Fazendo scroll para carregar mais conteúdo...")
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if(totalHeight >= scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
        
        # Aguardar mais requisições após scroll
        await asyncio.sleep(5)
        
        # Tentar clicar em elementos que podem carregar mais dados
        logger.info("🔍 Procurando botões ou links que carregam mais dados...")
        try:
            # Procurar por botões de "carregar mais" ou paginação
            load_more_buttons = await page.query_selector_all("button, a[href*='page'], a[href*='lotePage']")
            for i, btn in enumerate(load_more_buttons[:3]):  # Limitar a 3 cliques
                try:
                    await btn.click()
                    await asyncio.sleep(2)
                    logger.info(f"  Clicou em botão/link {i+1}")
                except:
                    pass
        except Exception as e:
            logger.debug(f"Erro ao clicar em elementos: {e}")
        
        # Aguardar mais requisições após cliques
        await asyncio.sleep(3)
        
        await browser.close()
    
    # Resumo final
    logger.info(f"\n{'='*60}")
    logger.info(f"RESUMO DAS REQUISIÇÕES")
    logger.info("="*60)
    logger.info(f"Total de requisições monitoradas: {len(todas_requisicoes)}")
    logger.info(f"APIs JSON encontradas: {len(apis_encontradas)}")
    
    if apis_encontradas:
        logger.info(f"\n{'='*60}")
        logger.info(f"APIS JSON COM DADOS DE LEILÕES ENCONTRADAS:")
        logger.info("="*60)
        
        for i, api in enumerate(apis_encontradas, 1):
            logger.info(f"\n{i}. URL: {api['url']}")
            logger.info(f"   Método: {api['method']}")
            logger.info(f"   Status: {api['status']}")
            logger.info(f"   Headers da Requisição:")
            for key, value in api['headers_request'].items():
                if key.lower() in ['authorization', 'x-api-key', 'x-auth-token', 'cookie', 'referer', 'origin', 'accept', 'content-type']:
                    logger.info(f"     {key}: {value}")
            logger.info(f"   Preview do Body: {api['body_preview'][:300]}...")
        
        # Salvar em arquivo JSON
        output_file = 'leilao-backend/scripts/pestana_apis_encontradas.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(apis_encontradas, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✅ Dados salvos em {output_file}")
        
        # Criar resumo formatado
        logger.info(f"\n{'='*60}")
        logger.info(f"RESUMO FORMATADO PARA USO:")
        logger.info("="*60)
        
        for api in apis_encontradas:
            logger.info(f"\n📌 API: {api['url']}")
            logger.info(f"   Método: {api['method']}")
            logger.info(f"   Headers necessários:")
            important_headers = {}
            for key, value in api['headers_request'].items():
                if key.lower() in ['authorization', 'x-api-key', 'x-auth-token', 'cookie', 'referer', 'origin', 'accept', 'content-type', 'user-agent']:
                    important_headers[key] = value
                    logger.info(f"     {key}: {value}")
            
            # Salvar headers importantes
            api['important_headers'] = important_headers
    else:
        logger.warning("\n⚠️ Nenhuma API JSON com dados de leilões encontrada")
        logger.info("   Possíveis razões:")
        logger.info("   1. Site usa WebSockets para carregar dados")
        logger.info("   2. Dados são carregados via JavaScript inline")
        logger.info("   3. API requer autenticação específica")
        logger.info("   4. Dados estão em formato diferente (HTML, XML, etc)")
    
    return apis_encontradas

if __name__ == "__main__":
    asyncio.run(monitorar_requisicoes())

