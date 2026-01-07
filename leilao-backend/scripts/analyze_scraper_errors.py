#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para analisar erros dos scrapers."""

import os
import sys
import io
from pathlib import Path
from collections import Counter

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def main():
    print("=" * 60)
    print("ANÁLISE DE ERROS DOS SCRAPERS")
    print("=" * 60)
    
    # Buscar leiloeiros com erro
    response = supabase.table("auctioneers") \
        .select("id, name, website, scrape_status, scrape_error, last_scrape") \
        .eq("scrape_status", "error") \
        .execute()
    
    if not response.data:
        print("Nenhum leiloeiro com status 'error' encontrado.")
        return
    
    print(f"\nTotal de leiloeiros com erro: {len(response.data)}")
    
    # Agrupar erros por tipo
    error_types = Counter()
    errors_detail = []
    
    for auc in response.data:
        error = auc.get("scrape_error") or "Erro não especificado"
        
        # Categorizar erro
        error_lower = error.lower()
        if "timeout" in error_lower:
            error_type = "Timeout"
        elif "404" in error or "not found" in error_lower:
            error_type = "Página não encontrada (404)"
        elif "403" in error or "forbidden" in error_lower:
            error_type = "Acesso negado (403)"
        elif "cloudflare" in error_lower:
            error_type = "Bloqueio Cloudflare"
        elif "ssl" in error_lower or "certificate" in error_lower:
            error_type = "Erro SSL/Certificado"
        elif "connection" in error_lower:
            error_type = "Erro de conexão"
        elif "dns" in error_lower or "resolve" in error_lower:
            error_type = "DNS não resolve"
        elif "no properties" in error_lower or "sem imóveis" in error_lower:
            error_type = "Sem imóveis encontrados"
        else:
            error_type = "Outro"
        
        error_types[error_type] += 1
        errors_detail.append({
            "name": auc.get("name"),
            "website": auc.get("website"),
            "error_type": error_type,
            "error": error[:100]
        })
    
    # Mostrar resumo por tipo de erro
    print("\n" + "-" * 40)
    print("RESUMO POR TIPO DE ERRO:")
    print("-" * 40)
    for error_type, count in error_types.most_common():
        print(f"  {error_type}: {count} leiloeiros")
    
    # Mostrar detalhes por categoria
    print("\n" + "-" * 40)
    print("DETALHES POR CATEGORIA:")
    print("-" * 40)
    
    for error_type in error_types.keys():
        print(f"\n### {error_type} ###")
        for detail in errors_detail:
            if detail["error_type"] == error_type:
                print(f"  - {detail['name']}: {detail['website']}")
    
    # Recomendações
    print("\n" + "=" * 60)
    print("RECOMENDAÇÕES:")
    print("=" * 60)
    
    if error_types.get("Bloqueio Cloudflare", 0) > 0:
        print("\n[*] CLOUDFLARE: Usar Playwright com stealth ou ScrapingBee")
    
    if error_types.get("DNS não resolve", 0) > 0:
        print("\n[*] DNS: Sites provavelmente offline - remover da lista ou marcar como inativo")
    
    if error_types.get("Página não encontrada (404)", 0) > 0:
        print("\n[*] 404: Verificar se URLs estao corretas ou se sites mudaram estrutura")
    
    if error_types.get("Timeout", 0) > 0:
        print("\n[*] TIMEOUT: Aumentar timeout ou usar retry com backoff")
    
    if error_types.get("Sem imóveis encontrados", 0) > 0:
        print("\n[*] SEM IMOVEIS: Verificar seletores CSS ou se leiloeiro tem imoveis ativos")
    
    # Salvar relatório
    report_path = Path(__file__).parent.parent / "RELATORIO_ERROS_SCRAPERS.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Relatório de Erros dos Scrapers\n\n")
        f.write(f"**Total de leiloeiros com erro:** {len(response.data)}\n\n")
        
        f.write("## Resumo por Tipo de Erro\n\n")
        f.write("| Tipo de Erro | Quantidade |\n")
        f.write("|--------------|------------|\n")
        for error_type, count in error_types.most_common():
            f.write(f"| {error_type} | {count} |\n")
        
        f.write("\n## Detalhes por Leiloeiro\n\n")
        for error_type in error_types.keys():
            f.write(f"\n### {error_type}\n\n")
            for detail in errors_detail:
                if detail["error_type"] == error_type:
                    f.write(f"- **{detail['name']}**: {detail['website']}\n")
                    f.write(f"  - Erro: {detail['error']}\n")
    
    print(f"\n[OK] Relatorio salvo em: {report_path}")

if __name__ == "__main__":
    main()

