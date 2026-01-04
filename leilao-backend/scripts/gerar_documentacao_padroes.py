"""
Gera documentação de padrões identificados
"""
import os
import sys
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def gerar_documentacao():
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    doc = f"""# 📊 Padrões de Scraping - LeiloHub

**Gerado em:** {datetime.now().isoformat()}

## Resumo Geral

"""
    
    # Estatísticas gerais
    cur.execute("SELECT COUNT(*) FROM auctioneers")
    total = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) FROM auctioneers WHERE scrape_status = 'success'")
    sucesso = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) FROM auctioneers WHERE scrape_config IS NOT NULL")
    com_config = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) FROM properties")
    imoveis = cur.fetchone()['count']
    
    doc += f"""
| Métrica | Valor |
|---------|-------|
| Total de leiloeiros | {total} |
| Com scraping funcionando | {sucesso} |
| Com config descoberto | {com_config} |
| Total de imóveis | {imoveis} |
| Taxa de sucesso | {sucesso/total*100:.1f}% |

## Padrões de Sites

### Tipos de Site Identificados
"""
    
    cur.execute("""
        SELECT 
            scrape_config->>'site_type' as tipo,
            COUNT(*) as count
        FROM auctioneers
        WHERE scrape_config IS NOT NULL
        GROUP BY 1
    """)
    
    for row in cur.fetchall():
        doc += f"- **{row['tipo']}**: {row['count']} sites\n"
    
    doc += """
### Padrões de Sucesso

Os sites que funcionam geralmente têm:
1. URL direta para listagem de imóveis
2. Estrutura HTML consistente
3. Paginação via query parameter (?page=N)
4. Dados estruturados em cards/listas

### Padrões de Falha

Os sites que falham geralmente têm:
1. Proteção Cloudflare agressiva
2. Conteúdo carregado via JavaScript
3. APIs internas não documentadas
4. Rate limiting

## Erros Comuns

"""
    
    cur.execute("""
        SELECT 
            SUBSTRING(scrape_error, 1, 100) as erro,
            COUNT(*) as count
        FROM auctioneers
        WHERE scrape_error IS NOT NULL
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 10
    """)
    
    doc += "| Erro | Ocorrências |\n|------|-------------|\n"
    for row in cur.fetchall():
        erro = row['erro'] or 'N/A'
        doc += f"| {erro} | {row['count']} |\n"
    
    doc += """
## Recomendações

1. **Para sites list_based**: Usar URL de listagem direta
2. **Para sites filter_based**: Iterar por cada filtro de categoria
3. **Para sites com Cloudflare**: Usar Jina.ai como fallback
4. **Para sites com JavaScript**: Considerar ScrapingBee

## Próximos Passos

1. Aumentar cobertura de descoberta (mais leiloeiros)
2. Implementar fallbacks específicos por tipo de erro
3. Criar adaptadores customizados para sites problemáticos
4. Monitorar taxa de sucesso diariamente
"""
    
    conn.close()
    
    # Salvar
    output_path = os.path.join(os.path.dirname(__file__), '..', 'PADROES_SCRAPING.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(doc)
    
    print(f"Documentação salva em {output_path}")
    print(doc)

if __name__ == "__main__":
    gerar_documentacao()

