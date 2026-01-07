#!/usr/bin/env python3
"""
PIPELINE NOTURNO COMPLETO - LEILOHUB
Executa todas as etapas de manutenção e atualização do sistema.
Projetado para rodar autonomamente via GitHub Actions.
"""

import os
import sys
import logging
import hashlib
import httpx
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

def get_supabase():
    """Retorna cliente Supabase."""
    from supabase import create_client
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

def log_section(title: str):
    logger.info("=" * 70)
    logger.info(f"  {title}")
    logger.info("=" * 70)

def run_step(step_name: str, func) -> Dict[str, Any]:
    """Executa um passo com tratamento de erro."""
    logger.info(f"\n{'─' * 50}")
    logger.info(f"▶ Iniciando: {step_name}")
    logger.info(f"{'─' * 50}")
    
    start_time = datetime.now()
    try:
        result = func()
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ {step_name} concluído em {elapsed:.1f}s")
        return {"status": "success", "result": result, "elapsed": elapsed}
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ {step_name} falhou após {elapsed:.1f}s: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e), "elapsed": elapsed}

# ═══════════════════════════════════════════════════════════
# ETAPA 1: GERAR DEDUP_KEY PARA NOVOS IMÓVEIS
# ═══════════════════════════════════════════════════════════

def step_generate_dedup_keys():
    """Gera dedup_key para imóveis que não têm."""
    supabase = get_supabase()
    
    response = supabase.table("properties") \
        .select("id, source_url, auctioneer_id") \
        .is_("dedup_key", "null") \
        .limit(5000) \
        .execute()
    
    if not response.data:
        logger.info("  Todos os imóveis já têm dedup_key")
        return {"updated": 0}
    
    updated = 0
    for prop in response.data:
        key_source = f"{prop.get('auctioneer_id', '')}:{prop.get('source_url', '')}"
        dedup_key = hashlib.md5(key_source.encode()).hexdigest()
        
        supabase.table("properties") \
            .update({"dedup_key": dedup_key}) \
            .eq("id", prop["id"]) \
            .execute()
        updated += 1
    
    logger.info(f"  {updated} imóveis atualizados com dedup_key")
    return {"updated": updated}

# ═══════════════════════════════════════════════════════════
# ETAPA 2: AUDITORIA DE QUALIDADE
# ═══════════════════════════════════════════════════════════

def step_audit_quality():
    """Executa auditoria de qualidade dos dados."""
    supabase = get_supabase()
    stats = {}
    
    r = supabase.table("properties").select("id", count="exact").eq("is_active", True).execute()
    stats["total_ativos"] = r.count or 0
    
    r = supabase.table("properties").select("id", count="exact") \
        .eq("is_active", True).or_("city.is.null,city.eq.").execute()
    stats["sem_cidade"] = r.count or 0
    
    r = supabase.table("properties").select("id", count="exact") \
        .eq("is_active", True) \
        .is_("evaluation_value", "null") \
        .is_("first_auction_value", "null") \
        .is_("second_auction_value", "null") \
        .execute()
    stats["sem_valores"] = r.count or 0
    
    r = supabase.table("properties").select("id", count="exact") \
        .eq("is_active", True).or_("image_url.is.null,image_url.eq.").execute()
    stats["sem_imagem"] = r.count or 0
    
    logger.info(f"  Total ativos: {stats['total_ativos']}")
    logger.info(f"  Sem cidade: {stats['sem_cidade']}")
    logger.info(f"  Sem valores: {stats['sem_valores']}")
    logger.info(f"  Sem imagem: {stats['sem_imagem']}")
    
    return stats

# ═══════════════════════════════════════════════════════════
# ETAPA 3: LIMPEZA DE DADOS RUINS
# ═══════════════════════════════════════════════════════════

def step_cleanup_bad_data():
    """Desativa imóveis com dados críticos faltando."""
    supabase = get_supabase()
    total_desativados = 0
    
    # Desativar sem cidade E sem estado
    r = supabase.table("properties") \
        .select("id") \
        .eq("is_active", True) \
        .or_("city.is.null,city.eq.") \
        .or_("state.is.null,state.eq.") \
        .limit(500) \
        .execute()
    
    if r.data:
        for prop in r.data:
            supabase.table("properties") \
                .update({"is_active": False, "deactivated_at": datetime.now().isoformat()}) \
                .eq("id", prop["id"]) \
                .execute()
        total_desativados += len(r.data)
        logger.info(f"  {len(r.data)} desativados (sem cidade/estado)")
    
    # Desativar sem valores
    r = supabase.table("properties") \
        .select("id") \
        .eq("is_active", True) \
        .is_("evaluation_value", "null") \
        .is_("first_auction_value", "null") \
        .is_("second_auction_value", "null") \
        .limit(500) \
        .execute()
    
    if r.data:
        for prop in r.data:
            supabase.table("properties") \
                .update({"is_active": False, "deactivated_at": datetime.now().isoformat()}) \
                .eq("id", prop["id"]) \
                .execute()
        total_desativados += len(r.data)
        logger.info(f"  {len(r.data)} desativados (sem valores)")
    
    return {"desativados": total_desativados}

# ═══════════════════════════════════════════════════════════
# ETAPA 4: VERIFICAÇÃO DE LINKS QUEBRADOS
# ═══════════════════════════════════════════════════════════

def step_check_broken_links():
    """Verifica amostra de links para detectar expirados."""
    supabase = get_supabase()
    
    response = supabase.table("properties") \
        .select("id, source_url") \
        .eq("auctioneer_id", "caixa") \
        .eq("is_active", True) \
        .limit(100) \
        .execute()
    
    if not response.data:
        return {"verificados": 0, "quebrados": 0}
    
    quebrados = 0
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for prop in response.data:
            try:
                url = prop.get("source_url")
                if not url:
                    continue
                r = client.head(url)
                if r.status_code == 404:
                    supabase.table("properties") \
                        .update({"is_active": False, "deactivated_at": datetime.now().isoformat()}) \
                        .eq("id", prop["id"]) \
                        .execute()
                    quebrados += 1
            except:
                pass
    
    logger.info(f"  Verificados: {len(response.data)}, Quebrados: {quebrados}")
    return {"verificados": len(response.data), "quebrados": quebrados}

# ═══════════════════════════════════════════════════════════
# ETAPA 5: BUSCA DE IMAGENS FALTANTES
# ═══════════════════════════════════════════════════════════

def step_fetch_missing_images():
    """Busca imagens para imóveis que não têm."""
    # Importar o script de busca de imagens
    try:
        # Adicionar o diretório scripts ao path
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        
        from fetch_missing_images import main as fetch_images
        result = fetch_images(limit=300, batch_size=30)
        return result
    except ImportError as e:
        # Executar versão inline simplificada
        logger.info(f"  Executando busca de imagens inline (import falhou: {e})...")
        supabase = get_supabase()
        
        response = supabase.table("properties") \
            .select("id, source_url, auctioneer_id, title") \
            .eq("is_active", True) \
            .or_("image_url.is.null,image_url.eq.") \
            .limit(200) \
            .execute()
        
        if not response.data:
            return {"verificados": 0, "atualizados": 0}
        
        atualizados = 0
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
            for prop in response.data[:100]:  # Limitar para não demorar muito
                try:
                    url = prop.get("source_url")
                    if not url:
                        continue
                    
                    r = client.get(url)
                    if r.status_code != 200:
                        continue
                    
                    # Buscar imagem no HTML
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, 'html.parser')
                    
                    # Tentar encontrar imagem
                    for img in soup.find_all('img'):
                        src = img.get('src') or img.get('data-src')
                        if src and 'http' in src and not any(x in src.lower() for x in ['logo', 'icon', 'placeholder']):
                            supabase.table("properties") \
                                .update({"image_url": src}) \
                                .eq("id", prop["id"]) \
                                .execute()
                            atualizados += 1
                            break
                    
                    import time
                    time.sleep(0.5)
                except:
                    pass
        
        logger.info(f"  Verificados: {len(response.data)}, Atualizados: {atualizados}")
        return {"verificados": len(response.data), "atualizados": atualizados}

# ═══════════════════════════════════════════════════════════
# ETAPA 6: GERAR RELATÓRIO
# ═══════════════════════════════════════════════════════════

def step_generate_report(results: dict):
    """Gera relatório da execução."""
    supabase = get_supabase()
    
    r = supabase.table("properties").select("id", count="exact").eq("is_active", True).execute()
    total_ativos = r.count or 0
    
    r = supabase.table("properties").select("id", count="exact").eq("is_active", False).execute()
    total_inativos = r.count or 0
    
    r = supabase.table("properties").select("id", count="exact") \
        .eq("is_active", True).or_("image_url.is.null,image_url.eq.").execute()
    sem_imagem = r.count or 0
    
    report = f"""# 📊 RELATÓRIO DE EXECUÇÃO NOTURNA - LEILOHUB
**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Resumo da Execução

| Etapa | Status | Tempo |
|-------|--------|-------|
"""
    
    for step_name, step_result in results.items():
        status = "✅" if step_result.get("status") == "success" else "❌"
        elapsed = step_result.get("elapsed", 0)
        report += f"| {step_name} | {status} | {elapsed:.1f}s |\n"
    
    report += f"""
## Estado Final do Banco

| Métrica | Valor |
|---------|-------|
| Imóveis Ativos | {total_ativos:,} |
| Imóveis Inativos | {total_inativos:,} |
| Sem Imagem | {sem_imagem:,} |
| **Total** | **{total_ativos + total_inativos:,}** |

## Detalhes por Etapa

"""
    
    for step_name, step_result in results.items():
        report += f"### {step_name}\n"
        if step_result.get("status") == "error":
            report += f"❌ Erro: {step_result.get('error')}\n"
        else:
            report += f"✅ Resultado: {step_result.get('result')}\n"
        report += "\n"
    
    report_path = os.path.join(os.path.dirname(__file__), f"RELATORIO_NOTURNO_{datetime.now().strftime('%Y%m%d_%H%M')}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"  Relatório salvo: {report_path}")
    return {"report_path": report_path, "total_ativos": total_ativos, "sem_imagem": sem_imagem}

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    """Executa o pipeline noturno completo."""
    start_time = datetime.now()
    
    log_section("PIPELINE NOTURNO COMPLETO - LEILOHUB")
    logger.info(f"Iniciado em: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    results["1_Dedup_Keys"] = run_step("Gerar Dedup Keys", step_generate_dedup_keys)
    results["2_Auditoria"] = run_step("Auditoria de Qualidade", step_audit_quality)
    results["3_Limpeza"] = run_step("Limpeza de Dados Ruins", step_cleanup_bad_data)
    results["4_Links"] = run_step("Verificar Links Quebrados", step_check_broken_links)
    results["5_Imagens"] = run_step("Buscar Imagens Faltantes", step_fetch_missing_images)
    results["6_Relatorio"] = run_step("Gerar Relatório", lambda: step_generate_report(results))
    
    elapsed_total = (datetime.now() - start_time).total_seconds()
    
    log_section("EXECUÇÃO CONCLUÍDA")
    logger.info(f"Tempo total: {elapsed_total:.1f}s ({elapsed_total/60:.1f} min)")
    
    sucessos = sum(1 for r in results.values() if r.get("status") == "success")
    falhas = sum(1 for r in results.values() if r.get("status") == "error")
    
    logger.info(f"Etapas com sucesso: {sucessos}")
    logger.info(f"Etapas com falha: {falhas}")
    
    return 0 if falhas == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

