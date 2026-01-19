"""
Testa arquitetura LLM (GPT-4o-mini) para extração de imóveis.
Versão simplificada sem Crawl4AI (usa requests + BeautifulSoup + OpenAI).
"""
import os
import sys
import io
import json
import asyncio
from datetime import datetime
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

# Verificar dependências
try:
    import openai
    print("✓ openai importado com sucesso")
except ImportError as e:
    print(f"✗ Erro ao importar openai: {e}")
    print("  Execute: pip install openai")
    sys.exit(1)

try:
    import requests
    from bs4 import BeautifulSoup
    print("✓ requests e beautifulsoup4 importados")
except ImportError:
    print("✗ Instale: pip install requests beautifulsoup4")
    sys.exit(1)

# Verificar API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("✗ OPENAI_API_KEY não configurada no .env")
    print("  Adicione ao .env: OPENAI_API_KEY=sk-...")
    sys.exit(1)
print("✓ OPENAI_API_KEY configurada")

# Inicializar cliente OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Leiloeiros para testar
LEILOEIROS_TESTE = [
    {"nome": "Viva Leilões", "url": "https://www.vivaleiloes.com.br"},
    {"nome": "Unileilões", "url": "https://www.unileiloes.com.br"},
    {"nome": "De Paula Online", "url": "https://www.depaulaonline.com.br"},
    {"nome": "Picelli Leilões", "url": "https://www.picellileiloes.com.br"},
    {"nome": "Alliance Leilões", "url": "https://www.allianceleiloes.com.br"},
    {"nome": "Morales Leilões", "url": "https://www.moralesleiloes.com.br"},
    {"nome": "Spencer Leilões", "url": "https://www.spencerleiloes.com.br"},
    {"nome": "Biasi Leilões", "url": "https://www.biasileiloes.com.br"},
    {"nome": "Ana Brasil Leilões", "url": "https://www.anabrasilleiloes.com.br"},
    {"nome": "Horizonte Leilões", "url": "https://www.horizonteleiloes.com.br"},
]


def extrair_html(url: str, timeout: int = 30) -> tuple[str, str]:
    """Extrai HTML da página usando requests."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # Usar BeautifulSoup para limpar e extrair texto relevante
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remover scripts, styles, etc
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()
        
        # Extrair texto limpo
        text = soup.get_text(separator='\n', strip=True)
        
        # Limitar tamanho para não exceder limite da API
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text_cleaned = '\n'.join(lines[:500])  # Primeiras 500 linhas
        
        return text_cleaned, None
    except Exception as e:
        return None, str(e)


def extrair_imoveis_llm(html_text: str, url: str, nome: str) -> dict:
    """
    Extrai imóveis usando GPT-4o-mini.
    Arquitetura recomendada: LLM para parsing estruturado.
    """
    resultado = {
        "leiloeiro": nome,
        "url": url,
        "sucesso": False,
        "imoveis": [],
        "erro": None,
        "metodo": "requests_beautifulsoup_gpt4o_mini",
        "tokens_usados": 0
    }
    
    try:
        # Prompt otimizado para extração de imóveis
        prompt = f"""Analise o seguinte conteúdo de uma página de leilões de imóveis e extraia TODOS os imóveis disponíveis.

Para cada imóvel encontrado, extraia:
- titulo: título ou descrição do imóvel
- endereco: endereço completo (se disponível)
- cidade: cidade
- estado: estado (sigla UF como SP, RJ, MG)
- tipo: tipo do imóvel (Apartamento, Casa, Terreno, Comercial, Rural)
- area: área em m² (número)
- valor_avaliacao: valor de avaliação em R$ (número)
- valor_minimo: lance mínimo em R$ (número)
- desconto: percentual de desconto (número entre 0-100)
- data_leilao: data do leilão (DD/MM/YYYY)
- modalidade: Judicial, Extrajudicial ou Venda Direta
- url_imovel: URL específica do imóvel (se houver)

IMPORTANTE:
- Se um campo não estiver disponível, use null
- Retorne APENAS JSON válido, sem texto adicional
- Foque em imóveis reais, ignore anúncios e banners
- Se não houver imóveis, retorne {{"imoveis": []}}

CONTEÚDO DA PÁGINA:
{html_text[:8000]}

Responda APENAS com JSON no formato:
{{"imoveis": [...]}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um extrator de dados estruturados de páginas web. Responda APENAS com JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=4000
        )
        
        resultado["tokens_usados"] = response.usage.total_tokens
        
        # Extrair resposta
        resposta = response.choices[0].message.content.strip()
        
        # Tentar parsear JSON
        # Remover markdown code blocks se houver
        if resposta.startswith("```json"):
            resposta = resposta[7:]
        if resposta.startswith("```"):
            resposta = resposta[3:]
        if resposta.endswith("```"):
            resposta = resposta[:-3]
        resposta = resposta.strip()
        
        data = json.loads(resposta)
        imoveis = data.get("imoveis", [])
        
        resultado["imoveis"] = imoveis
        resultado["sucesso"] = len(imoveis) > 0
        
        if not imoveis:
            resultado["erro"] = "LLM não encontrou imóveis no conteúdo"
            
    except json.JSONDecodeError as e:
        resultado["erro"] = f"Erro ao parsear JSON da LLM: {e}"
    except Exception as e:
        resultado["erro"] = str(e)
    
    return resultado


def main():
    print("=" * 70)
    print("TESTE: ARQUITETURA LLM (GPT-4o-mini) PARA EXTRAÇÃO DE IMÓVEIS")
    print("Método: Requests + BeautifulSoup + OpenAI GPT-4o-mini")
    print("=" * 70)
    print(f"\nInício: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Leiloeiros a testar: {len(LEILOEIROS_TESTE)}")
    print("-" * 70)
    
    resultados = []
    sucessos = 0
    total_imoveis = 0
    total_tokens = 0
    
    for i, leiloeiro in enumerate(LEILOEIROS_TESTE, 1):
        print(f"\n[{i}/{len(LEILOEIROS_TESTE)}] {leiloeiro['nome']}")
        print(f"    URL: {leiloeiro['url']}")
        
        # Extrair HTML
        print("    Extraindo HTML...")
        html_text, erro_html = extrair_html(leiloeiro['url'])
        
        if erro_html:
            print(f"    ✗ FALHA HTTP: {erro_html}")
            resultados.append({
                "leiloeiro": leiloeiro['nome'],
                "url": leiloeiro['url'],
                "sucesso": False,
                "imoveis": [],
                "erro": f"Erro HTTP: {erro_html}",
                "metodo": "requests_failed"
            })
            continue
        
        print(f"    HTML extraído: {len(html_text)} caracteres")
        
        # Extrair com LLM
        print("    Extraindo imóveis com GPT-4o-mini...")
        resultado = extrair_imoveis_llm(html_text, leiloeiro['url'], leiloeiro['nome'])
        resultados.append(resultado)
        
        total_tokens += resultado.get("tokens_usados", 0)
        
        if resultado["sucesso"]:
            sucessos += 1
            qtd = len(resultado["imoveis"])
            total_imoveis += qtd
            print(f"    ✓ SUCESSO: {qtd} imóveis extraídos")
            print(f"    Tokens: {resultado['tokens_usados']}")
            
            # Mostrar primeiro imóvel como exemplo
            if resultado["imoveis"]:
                primeiro = resultado["imoveis"][0]
                titulo = primeiro.get('titulo', 'N/A')
                if titulo and len(titulo) > 60:
                    titulo = titulo[:60] + "..."
                print(f"    Exemplo: {titulo}")
                cidade = primeiro.get('cidade', 'N/A')
                estado = primeiro.get('estado', 'N/A')
                print(f"             {cidade}/{estado}")
        else:
            print(f"    ✗ FALHA: {resultado['erro']}")
        
        # Pequena pausa entre requests
        time.sleep(1)
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    
    taxa_sucesso = (sucessos / len(LEILOEIROS_TESTE)) * 100 if LEILOEIROS_TESTE else 0
    print(f"\nTaxa de sucesso: {sucessos}/{len(LEILOEIROS_TESTE)} ({taxa_sucesso:.1f}%)")
    print(f"Total de imóveis extraídos: {total_imoveis}")
    print(f"Total de tokens usados: {total_tokens:,}")
    
    # Custo estimado (GPT-4o-mini: $0.15/1M input, $0.60/1M output)
    custo_estimado = (total_tokens / 1_000_000) * 0.375  # média entre input e output
    print(f"Custo estimado: ${custo_estimado:.4f}")
    
    print("\n\nResultados por leiloeiro:")
    for r in resultados:
        status = "✓" if r["sucesso"] else "✗"
        qtd = len(r["imoveis"]) if r["sucesso"] else 0
        print(f"  {status} {r['leiloeiro']}: {qtd} imóveis")
    
    # Salvar resultados
    output_file = f"resultados_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "data_teste": datetime.now().isoformat(),
            "arquitetura": "requests_beautifulsoup_gpt4o_mini",
            "modelo_llm": "gpt-4o-mini",
            "total_leiloeiros": len(LEILOEIROS_TESTE),
            "sucessos": sucessos,
            "taxa_sucesso": taxa_sucesso,
            "total_imoveis": total_imoveis,
            "total_tokens": total_tokens,
            "custo_estimado_usd": custo_estimado,
            "resultados": resultados
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nResultados salvos em: {output_file}")
    
    # Comparação
    print("\n" + "=" * 70)
    print("COMPARAÇÃO COM SITUAÇÃO ATUAL")
    print("=" * 70)
    print(f"\nSituação atual (scrapers manuais): 9 leiloeiros funcionando (1.8%)")
    print(f"Teste LLM (GPT-4o-mini):           {sucessos} de 10 ({taxa_sucesso:.1f}%)")
    
    if taxa_sucesso >= 70:
        print("\n✓ ARQUITETURA LLM VALIDADA!")
        print("  Recomendação: Migrar para arquitetura baseada em LLM")
        print(f"  Custo por leiloeiro: ~${custo_estimado/len(LEILOEIROS_TESTE):.4f}")
    elif taxa_sucesso >= 50:
        print("\n⚠ ARQUITETURA PARCIALMENTE FUNCIONAL")
        print("  Recomendação: Investigar falhas antes de migrar")
    else:
        print("\n✗ ARQUITETURA COM PROBLEMAS")
        print("  Recomendação: Investigar causa das falhas")
    
    # Análise de falhas
    falhas = [r for r in resultados if not r["sucesso"]]
    if falhas:
        print("\n\nAnálise de Falhas:")
        tipos_erro = {}
        for f in falhas:
            erro = f.get("erro", "Desconhecido")
            erro_tipo = erro.split(":")[0] if ":" in erro else erro
            tipos_erro[erro_tipo] = tipos_erro.get(erro_tipo, 0) + 1
        
        for tipo, count in sorted(tipos_erro.items(), key=lambda x: -x[1]):
            print(f"  - {tipo}: {count} casos")
    
    print("\n" + "=" * 70)
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
