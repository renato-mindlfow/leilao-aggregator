"""
Pipeline de importação de links de leilão usando Gemini API para extração de dados.
"""
import os
import json
import logging
import httpx
from typing import Optional, Dict, List
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configurar API key do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


async def extract_data_with_gemini(html_content: str, url: str) -> dict:
    """Extrai dados estruturados do HTML usando Gemini."""
    
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY não configurada")
        return {"error": "GEMINI_API_KEY não configurada"}
    
    system_prompt = """Você é um especialista em extração de dados de páginas de leilão de imóveis.
Analise o HTML fornecido e extraia as seguintes informações em formato JSON:
- auction_date_1: Data do 1º leilão (formato ISO 8601)
- auction_value_1: Valor do 1º leilão (número)
- auction_date_2: Data do 2º leilão (formato ISO 8601)  
- auction_value_2: Valor do 2º leilão (número)
- city: Cidade do imóvel
- state: Estado (sigla UF)
- neighborhood: Bairro
- address: Endereço completo
- property_description: Descrição do imóvel
- modality: Modalidade (judicial ou extrajudicial)
- market_value: Valor de mercado se disponível

Retorne APENAS o JSON, sem markdown ou explicações."""

    user_prompt = f"""URL: {url}

HTML da página:
{html_content[:50000]}

Extraia os dados do leilão em formato JSON."""

    try:
        # Criar modelo (sem system_instruction no construtor)
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        
        # Combinar prompts (nova forma de passar system instruction)
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Gerar resposta
        response = model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=4096,
            )
        )
        
        # Processar resposta
        text = response.text.strip()
        
        # Remover markdown se presente
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return json.loads(text.strip())
        
    except Exception as e:
        logger.error(f"Erro ao extrair dados com Gemini: {e}")
        return {"error": str(e)}


async def fetch_and_extract(url: str) -> Dict:
    """Busca HTML de uma URL e extrai dados usando Gemini."""
    
    logger.info(f"Initial fetch for {url}: starting")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            html_content = response.text
            
        logger.info(f"Initial fetch for {url}: success=True")
        
        # Tentar extração com Gemini
        try:
            extracted = await extract_data_with_gemini(html_content, url)
            
            d1 = extracted.get("auction_date_1")
            v1 = extracted.get("auction_value_1")
            d2 = extracted.get("auction_date_2")
            v2 = extracted.get("auction_value_2")
            
            logger.info(f"Gemini extraction for {url}: d1={d1}, v1={v1}, d2={d2}, v2={v2}")
            
            return extracted
            
        except Exception as e:
            logger.error(f"Gemini extraction error: {e}")
            logger.info(f"Gemini extraction for {url}: d1=None, v1=None, d2=None, v2=None")
            return {"error": str(e)}
            
    except Exception as e:
        logger.error(f"Erro ao buscar URL {url}: {e}")
        return {"error": str(e)}


async def process_urls(urls: List[str]) -> List[Dict]:
    """Processa uma lista de URLs e extrai dados."""
    results = []
    for url in urls:
        result = await fetch_and_extract(url)
        results.append({"url": url, **result})
    return results


