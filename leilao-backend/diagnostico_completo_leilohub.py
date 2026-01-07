#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Diagnóstico Completo do LeiloHub
Executa todas as verificações solicitadas e gera relatório em Markdown.
"""

import os
import sys
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Carregar .env
load_dotenv()

# Configurações
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}[ERRO] {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}[AVISO] {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")

# ============================================================================
# PARTE 1: LEILOEIROS INTEGRADOS vs NÃO INTEGRADOS
# ============================================================================

def consultar_imoveis_por_leiloeiro(conn) -> List[Dict]:
    """Consulta imóveis agrupados por leiloeiro."""
    query = """
        SELECT 
            auctioneer_name,
            auctioneer_id,
            COUNT(*) as total_imoveis,
            MIN(created_at) as primeiro_imovel,
            MAX(created_at) as ultimo_imovel
        FROM properties
        WHERE is_active = true
        GROUP BY auctioneer_name, auctioneer_id
        ORDER BY total_imoveis DESC;
    """
    cursor = conn.execute(query)
    return cursor.fetchall()

def consultar_todos_leiloeiros(conn) -> List[Dict]:
    """Consulta todos os leiloeiros cadastrados."""
    query = """
        SELECT 
            id,
            name,
            website,
            property_count,
            is_active,
            scrape_status
        FROM auctioneers
        ORDER BY COALESCE(property_count, 0) DESC;
    """
    cursor = conn.execute(query)
    return cursor.fetchall()

def analisar_leiloeiros(conn) -> Dict:
    """Analisa leiloeiros integrados vs não integrados."""
    print_header("PARTE 1: LEILOEIROS INTEGRADOS vs NÃO INTEGRADOS")
    
    # Consultar imóveis por leiloeiro
    print_info("Consultando imóveis por leiloeiro...")
    imoveis_por_leiloeiro = consultar_imoveis_por_leiloeiro(conn)
    
    # Consultar todos os leiloeiros
    print_info("Consultando todos os leiloeiros cadastrados...")
    todos_leiloeiros = consultar_todos_leiloeiros(conn)
    
    # Criar dicionário de leiloeiros com imóveis
    leiloeiros_com_imoveis = {
        row['auctioneer_id']: {
            'name': row['auctioneer_name'],
            'id': row['auctioneer_id'],
            'total_imoveis': row['total_imoveis'],
            'primeiro_imovel': row['primeiro_imovel'],
            'ultimo_imovel': row['ultimo_imovel']
        }
        for row in imoveis_por_leiloeiro
    }
    
    # Identificar leiloeiros sem imóveis
    leiloeiros_sem_imoveis = []
    for leiloeiro in todos_leiloeiros:
        if leiloeiro['id'] not in leiloeiros_com_imoveis:
            leiloeiros_sem_imoveis.append({
                'id': leiloeiro['id'],
                'name': leiloeiro['name'],
                'website': leiloeiro['website'],
                'property_count': leiloeiro['property_count'] or 0,
                'scrape_status': leiloeiro['scrape_status']
            })
    
    # Top 10 leiloeiros por volume
    top_10 = sorted(
        leiloeiros_com_imoveis.values(),
        key=lambda x: x['total_imoveis'],
        reverse=True
    )[:10]
    
    resultado = {
        'total_leiloeiros_cadastrados': len(todos_leiloeiros),
        'leiloeiros_com_imoveis': len(leiloeiros_com_imoveis),
        'leiloeiros_sem_imoveis': len(leiloeiros_sem_imoveis),
        'leiloeiros_com_imoveis_lista': list(leiloeiros_com_imoveis.values()),
        'leiloeiros_sem_imoveis_lista': leiloeiros_sem_imoveis,
        'top_10': top_10
    }
    
    print_success(f"Leiloeiros com imóveis: {len(leiloeiros_com_imoveis)}")
    print_warning(f"Leiloeiros sem imóveis: {len(leiloeiros_sem_imoveis)}")
    print_info(f"Total de leiloeiros cadastrados: {len(todos_leiloeiros)}")
    
    return resultado

# ============================================================================
# PARTE 2: FERRAMENTA DE AUDITORIA DE QUALIDADE
# ============================================================================

def verificar_auditoria_qualidade() -> Dict:
    """Verifica se a auditoria de qualidade está implementada."""
    print_header("PARTE 2: FERRAMENTA DE AUDITORIA DE QUALIDADE")
    
    resultado = {
        'implementada': False,
        'arquivo_existe': False,
        'usada_no_pipeline': False,
        'validacoes': {
            'datas': False,
            'valores': False,
            'estado': False
        },
        'detalhes': []
    }
    
    # Verificar se o arquivo existe
    auditor_path = Path("leilao-backend/app/utils/quality_auditor.py")
    if auditor_path.exists():
        resultado['arquivo_existe'] = True
        resultado['implementada'] = True
        print_success("Arquivo quality_auditor.py encontrado")
        
        # Ler o arquivo e verificar validações
        with open(auditor_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if '_validate_dates' in content:
                resultado['validacoes']['datas'] = True
                resultado['detalhes'].append("✅ Validação de datas implementada")
            
            if '_validate_values' in content:
                resultado['validacoes']['valores'] = True
                resultado['detalhes'].append("✅ Validação de valores implementada")
            
            if '_validate_state' in content or 'VALID_STATES' in content:
                resultado['validacoes']['estado'] = True
                resultado['detalhes'].append("✅ Validação de estado implementada")
    else:
        print_error("Arquivo quality_auditor.py NÃO encontrado")
        resultado['detalhes'].append("❌ Arquivo quality_auditor.py não existe")
    
    # Verificar se está sendo usado no pipeline
    main_path = Path("leilao-backend/app/main.py")
    pipeline_path = Path("leilao-backend/app/services/scraper_pipeline.py")
    
    usada_no_main = False
    usada_no_pipeline = False
    
    if main_path.exists():
        with open(main_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'quality_auditor' in content or 'QualityAuditor' in content or 'get_quality_auditor' in content:
                usada_no_main = True
    
    if pipeline_path.exists():
        with open(pipeline_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'quality_auditor' in content or 'QualityAuditor' in content or 'get_quality_auditor' in content:
                usada_no_pipeline = True
    
    if usada_no_main or usada_no_pipeline:
        resultado['usada_no_pipeline'] = True
        resultado['detalhes'].append("✅ Auditoria está sendo usada no pipeline")
        if usada_no_main:
            resultado['detalhes'].append("  - Usada em app/main.py")
        if usada_no_pipeline:
            resultado['detalhes'].append("  - Usada em app/services/scraper_pipeline.py")
    else:
        resultado['detalhes'].append("⚠️  Auditoria NÃO está sendo usada no pipeline")
    
    return resultado

# ============================================================================
# PARTE 3: SISTEMA DE DEDUPLICAÇÃO
# ============================================================================

def verificar_deduplicacao(conn) -> Dict:
    """Verifica o sistema de deduplicação."""
    print_header("PARTE 3: SISTEMA DE DEDUPLICAÇÃO")
    
    resultado = {
        'implementada': False,
        'campo_dedup_key': False,
        'campo_is_duplicate': False,
        'duplicatas_no_banco': False,
        'total_duplicatas': 0,
        'total_com_dedup_key': 0,
        'total_sem_dedup_key': 0,
        'exemplos_duplicatas': []
    }
    
    # Verificar se o serviço existe
    dedup_path = Path("leilao-backend/app/services/deduplication.py")
    if dedup_path.exists():
        resultado['implementada'] = True
        print_success("Serviço de deduplicação encontrado")
    else:
        print_error("Serviço de deduplicação NÃO encontrado")
    
    # Verificar campos no banco
    try:
        # Verificar campo dedup_key
        query = """
            SELECT COUNT(*) as total, COUNT(dedup_key) as com_dedup
            FROM properties;
        """
        cursor = conn.execute(query)
        row = cursor.fetchone()
        resultado['total_com_dedup_key'] = row['com_dedup']
        resultado['total_sem_dedup_key'] = row['total'] - row['com_dedup']
        resultado['campo_dedup_key'] = True
        
        # Verificar campo is_duplicate
        query = """
            SELECT COUNT(*) as total_duplicatas
            FROM properties
            WHERE is_duplicate = true;
        """
        cursor = conn.execute(query)
        row = cursor.fetchone()
        resultado['total_duplicatas'] = row['total_duplicatas']
        resultado['campo_is_duplicate'] = True
        
        if resultado['total_duplicatas'] > 0:
            resultado['duplicatas_no_banco'] = True
            print_warning(f"Encontradas {resultado['total_duplicatas']} duplicatas no banco")
            
            # Buscar exemplos de duplicatas
            query = """
                SELECT source_url, COUNT(*) as qtd
                FROM properties
                GROUP BY source_url
                HAVING COUNT(*) > 1
                LIMIT 10;
            """
            cursor = conn.execute(query)
            resultado['exemplos_duplicatas'] = cursor.fetchall()
        else:
            print_success("Nenhuma duplicata encontrada no banco")
        
        print_info(f"Imóveis com dedup_key: {resultado['total_com_dedup_key']}")
        print_info(f"Imóveis sem dedup_key: {resultado['total_sem_dedup_key']}")
        
    except Exception as e:
        print_error(f"Erro ao verificar banco: {e}")
        resultado['detalhes'] = [f"❌ Erro: {str(e)}"]
    
    return resultado

# ============================================================================
# PARTE 4: AGENDAMENTO DE ATUALIZAÇÃO PERIÓDICA
# ============================================================================

def verificar_agendamento() -> Dict:
    """Verifica o agendamento de atualização periódica."""
    print_header("PARTE 4: AGENDAMENTO DE ATUALIZAÇÃO PERIÓDICA")
    
    resultado = {
        'workflows_encontrados': [],
        'workflows_com_schedule': [],
        'workflows_sem_schedule': [],
        'secrets_necessarios': [],
        'detalhes': []
    }
    
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print_error("Diretório .github/workflows não encontrado")
        return resultado
    
    # Listar workflows
    workflows = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    
    for workflow_path in workflows:
        workflow_info = {
            'nome': workflow_path.name,
            'tem_schedule': False,
            'cron': None,
            'secrets': []
        }
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Verificar schedule
            if 'schedule:' in content:
                workflow_info['tem_schedule'] = True
                # Extrair cron se possível
                import re
                cron_match = re.search(r"cron:\s*['\"]([^'\"]+)['\"]", content)
                if cron_match:
                    workflow_info['cron'] = cron_match.group(1)
                else:
                    # Tentar extrair de múltiplas linhas
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'cron:' in line:
                            if i + 1 < len(lines):
                                cron_line = lines[i + 1].strip()
                                if cron_line.startswith("'") or cron_line.startswith('"'):
                                    workflow_info['cron'] = cron_line.strip("'\"")
                                elif cron_line and not cron_line.startswith('-'):
                                    workflow_info['cron'] = cron_line
            
            # Verificar secrets
            if 'secrets.' in content:
                import re
                secrets = re.findall(r'secrets\.(\w+)', content)
                workflow_info['secrets'] = list(set(secrets))
        
        resultado['workflows_encontrados'].append(workflow_info)
        
        if workflow_info['tem_schedule']:
            resultado['workflows_com_schedule'].append(workflow_info)
            print_success(f"{workflow_path.name}: Tem schedule (cron: {workflow_info['cron']})")
        else:
            resultado['workflows_sem_schedule'].append(workflow_info)
            print_warning(f"{workflow_path.name}: Sem schedule")
    
    return resultado

# ============================================================================
# GERAR RELATÓRIO
# ============================================================================

def gerar_relatorio(
    leiloeiros: Dict,
    auditoria: Dict,
    deduplicacao: Dict,
    agendamento: Dict
) -> str:
    """Gera o relatório final em Markdown."""
    
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    relatorio = f"""# 📊 RELATÓRIO DE DIAGNÓSTICO COMPLETO - LEILOHUB

**Data de Geração:** {data_hora}

---

## 1. RESUMO EXECUTIVO

### Estatísticas Gerais
- **Total de Leiloeiros Cadastrados:** {leiloeiros['total_leiloeiros_cadastrados']}
- **Leiloeiros com Imóveis:** {leiloeiros['leiloeiros_com_imoveis']}
- **Leiloeiros sem Imóveis:** {leiloeiros['leiloeiros_sem_imoveis']}
- **Taxa de Integração:** {(leiloeiros['leiloeiros_com_imoveis'] / leiloeiros['total_leiloeiros_cadastrados'] * 100) if leiloeiros['total_leiloeiros_cadastrados'] > 0 else 0:.1f}%

### Status dos Sistemas
- **Auditoria de Qualidade:** {'✅ IMPLEMENTADA' if auditoria['implementada'] else '❌ NÃO IMPLEMENTADA'}
- **Deduplicação:** {'✅ IMPLEMENTADA' if deduplicacao['implementada'] else '❌ NÃO IMPLEMENTADA'}
- **Agendamento Periódico:** {'✅ CONFIGURADO' if len(agendamento['workflows_com_schedule']) > 0 else '❌ NÃO CONFIGURADO'}

---

## 2. LEILOEIROS INTEGRADOS

### Top 10 Leiloeiros por Volume de Imóveis

| # | Nome | ID | Total de Imóveis | Primeiro Imóvel | Último Imóvel |
|---|------|----|------------------|-----------------|---------------|
"""
    
    for i, leiloeiro in enumerate(leiloeiros['top_10'], 1):
        primeiro = leiloeiro['primeiro_imovel'].strftime('%Y-%m-%d') if leiloeiro['primeiro_imovel'] else 'N/A'
        ultimo = leiloeiro['ultimo_imovel'].strftime('%Y-%m-%d') if leiloeiro['ultimo_imovel'] else 'N/A'
        relatorio += f"| {i} | {leiloeiro['name']} | {leiloeiro['id']} | {leiloeiro['total_imoveis']:,} | {primeiro} | {ultimo} |\n"
    
    relatorio += f"""
### Todos os Leiloeiros com Imóveis ({len(leiloeiros['leiloeiros_com_imoveis_lista'])})

| Nome | ID | Total de Imóveis |
|------|----|------------------|
"""
    
    for leiloeiro in sorted(leiloeiros['leiloeiros_com_imoveis_lista'], key=lambda x: x['total_imoveis'], reverse=True):
        relatorio += f"| {leiloeiro['name']} | {leiloeiro['id']} | {leiloeiro['total_imoveis']:,} |\n"
    
    relatorio += f"""
---

## 3. LEILOEIROS PENDENTES (SEM IMÓVEIS)

**Total:** {len(leiloeiros['leiloeiros_sem_imoveis_lista'])} leiloeiros

### Lista Completa para Priorização

| # | Nome | ID | Website | Status Scraping | Property Count |
|---|------|----|---------|-----------------|----------------|
"""
    
    for i, leiloeiro in enumerate(leiloeiros['leiloeiros_sem_imoveis_lista'], 1):
        website = leiloeiro.get('website', 'N/A')[:50] if leiloeiro.get('website') else 'N/A'
        relatorio += f"| {i} | {leiloeiro['name']} | {leiloeiro['id']} | {website} | {leiloeiro.get('scrape_status', 'N/A')} | {leiloeiro.get('property_count', 0)} |\n"
    
    relatorio += f"""
---

## 4. STATUS DA AUDITORIA DE QUALIDADE

**Status:** {'✅ IMPLEMENTADA' if auditoria['implementada'] else '❌ NÃO IMPLEMENTADA'}

### Detalhes

"""
    
    if auditoria['implementada']:
        relatorio += "- ✅ Arquivo `quality_auditor.py` existe\n"
        relatorio += f"- {'✅' if auditoria['validacoes']['datas'] else '❌'} Validação de datas de leilão\n"
        relatorio += f"- {'✅' if auditoria['validacoes']['valores'] else '❌'} Validação de valores (1ª praça > 2ª praça)\n"
        relatorio += f"- {'✅' if auditoria['validacoes']['estado'] else '❌'} Validação de estado (não aceitar 'XX')\n"
        relatorio += f"- {'✅' if auditoria['usada_no_pipeline'] else '⚠️'} Está sendo usada no pipeline\n"
    else:
        relatorio += "- ❌ Arquivo `quality_auditor.py` NÃO existe\n"
        relatorio += "- ❌ Sistema de auditoria não está implementado\n"
    
    relatorio += f"""
### O que falta implementar?

"""
    
    if not auditoria['implementada']:
        relatorio += "- [ ] Criar classe `QualityAuditor`\n"
        relatorio += "- [ ] Implementar validação de datas\n"
        relatorio += "- [ ] Implementar validação de valores\n"
        relatorio += "- [ ] Implementar validação de estado\n"
        relatorio += "- [ ] Integrar no pipeline de scraping\n"
    elif not auditoria['usada_no_pipeline']:
        relatorio += "- [ ] Integrar `QualityAuditor` no pipeline de scraping\n"
        relatorio += "- [ ] Garantir que todos os imóveis passem pela auditoria antes de salvar\n"
    
    relatorio += f"""
---

## 5. STATUS DA DEDUPLICAÇÃO

**Status:** {'✅ IMPLEMENTADA' if deduplicacao['implementada'] else '❌ NÃO IMPLEMENTADA'}

### Detalhes

- {'✅' if deduplicacao['campo_dedup_key'] else '❌'} Campo `dedup_key` existe na tabela
- {'✅' if deduplicacao['campo_is_duplicate'] else '❌'} Campo `is_duplicate` existe na tabela
- **Total de imóveis com dedup_key:** {deduplicacao['total_com_dedup_key']:,}
- **Total de imóveis sem dedup_key:** {deduplicacao['total_sem_dedup_key']:,}
- **Total de duplicatas marcadas:** {deduplicacao['total_duplicatas']:,}

### Duplicatas no Banco

"""
    
    if deduplicacao['duplicatas_no_banco']:
        relatorio += f"⚠️ **ATENÇÃO:** Encontradas {deduplicacao['total_duplicatas']} duplicatas no banco!\n\n"
        relatorio += "**Exemplos de URLs duplicadas:**\n\n"
        relatorio += "| URL | Quantidade |\n"
        relatorio += "|-----|------------|\n"
        for dup in deduplicacao['exemplos_duplicatas'][:10]:
            url = dup['source_url'][:80] + '...' if len(dup['source_url']) > 80 else dup['source_url']
            relatorio += f"| {url} | {dup['qtd']} |\n"
    else:
        relatorio += "✅ Nenhuma duplicata encontrada no banco.\n"
    
    relatorio += f"""
### O que falta implementar?

"""
    
    if not deduplicacao['implementada']:
        relatorio += "- [ ] Criar serviço de deduplicação\n"
        relatorio += "- [ ] Implementar geração de `dedup_key`\n"
        relatorio += "- [ ] Implementar verificação antes de inserir novos imóveis\n"
    
    if deduplicacao['total_sem_dedup_key'] > 0:
        relatorio += f"- [ ] Gerar `dedup_key` para {deduplicacao['total_sem_dedup_key']:,} imóveis existentes\n"
    
    if deduplicacao['duplicatas_no_banco']:
        relatorio += f"- [ ] Limpar {deduplicacao['total_duplicatas']} duplicatas do banco\n"
    
    relatorio += f"""
---

## 6. STATUS DO AGENDAMENTO PERIÓDICO

**Status:** {'✅ CONFIGURADO' if len(agendamento['workflows_com_schedule']) > 0 else '❌ NÃO CONFIGURADO'}

### Workflows Encontrados

**Total:** {len(agendamento['workflows_encontrados'])} workflows

"""
    
    for workflow in agendamento['workflows_encontrados']:
        status = "✅" if workflow['tem_schedule'] else "❌"
        cron = workflow['cron'] or "N/A"
        relatorio += f"#### {status} {workflow['nome']}\n\n"
        relatorio += f"- **Schedule:** {'Sim' if workflow['tem_schedule'] else 'Não'}\n"
        relatorio += f"- **Cron:** `{cron}`\n"
        if workflow['secrets']:
            relatorio += f"- **Secrets necessários:** {', '.join(workflow['secrets'])}\n"
        relatorio += "\n"
    
    relatorio += f"""
### O que falta configurar?

"""
    
    if len(agendamento['workflows_sem_schedule']) > 0:
        relatorio += "**Workflows sem schedule:**\n"
        for workflow in agendamento['workflows_sem_schedule']:
            relatorio += f"- [ ] Adicionar schedule ao workflow `{workflow['nome']}`\n"
    
    # Verificar secrets necessários
    todos_secrets = set()
    for workflow in agendamento['workflows_encontrados']:
        todos_secrets.update(workflow['secrets'])
    
    if todos_secrets:
        relatorio += "\n**Secrets necessários no GitHub:**\n"
        for secret in sorted(todos_secrets):
            relatorio += f"- [ ] Verificar se `{secret}` está configurado\n"
    
    relatorio += f"""
---

## 7. RECOMENDAÇÕES DE PRÓXIMOS PASSOS

### Prioridade ALTA 🔴

"""
    
    if leiloeiros['leiloeiros_sem_imoveis'] > 0:
        relatorio += f"1. **Integrar leiloeiros pendentes:** {leiloeiros['leiloeiros_sem_imoveis']} leiloeiros sem imóveis precisam ser integrados\n"
    
    if deduplicacao['duplicatas_no_banco']:
        relatorio += f"2. **Limpar duplicatas:** {deduplicacao['total_duplicatas']} duplicatas encontradas no banco precisam ser removidas\n"
    
    if not auditoria['implementada'] or not auditoria['usada_no_pipeline']:
        relatorio += "3. **Implementar/Integrar auditoria de qualidade:** Garantir que todos os imóveis passem pela validação antes de salvar\n"
    
    relatorio += f"""
### Prioridade MÉDIA 🟡

"""
    
    if deduplicacao['total_sem_dedup_key'] > 0:
        relatorio += f"1. **Gerar dedup_key para imóveis existentes:** {deduplicacao['total_sem_dedup_key']:,} imóveis sem dedup_key\n"
    
    if len(agendamento['workflows_sem_schedule']) > 0:
        relatorio += f"2. **Configurar schedules:** {len(agendamento['workflows_sem_schedule'])} workflows sem agendamento\n"
    
    relatorio += f"""
### Prioridade BAIXA 🟢

1. **Monitorar qualidade dos dados:** Implementar alertas para dados inválidos
2. **Otimizar performance:** Revisar índices do banco de dados
3. **Documentação:** Atualizar documentação técnica do sistema

---

## 8. ESTATÍSTICAS DETALHADAS

### Distribuição de Imóveis por Leiloeiro

```
Total de Leiloeiros com Imóveis: {leiloeiros['leiloeiros_com_imoveis']}
Total de Leiloeiros sem Imóveis: {leiloeiros['leiloeiros_sem_imoveis']}
Taxa de Integração: {(leiloeiros['leiloeiros_com_imoveis'] / leiloeiros['total_leiloeiros_cadastrados'] * 100) if leiloeiros['total_leiloeiros_cadastrados'] > 0 else 0:.1f}%
```

### Status da Deduplicação

```
Imóveis com dedup_key: {deduplicacao['total_com_dedup_key']:,}
Imóveis sem dedup_key: {deduplicacao['total_sem_dedup_key']:,}
Duplicatas marcadas: {deduplicacao['total_duplicatas']:,}
```

### Status do Agendamento

```
Workflows com schedule: {len(agendamento['workflows_com_schedule'])}
Workflows sem schedule: {len(agendamento['workflows_sem_schedule'])}
```

---

**Relatório gerado automaticamente em {data_hora}**
"""
    
    return relatorio

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal."""
    print_header("DIAGNÓSTICO COMPLETO DO LEILOHUB")
    
    if not DATABASE_URL:
        print_error("DATABASE_URL não configurada no .env")
        sys.exit(1)
    
    try:
        # Conectar ao banco
        print_info("Conectando ao banco de dados...")
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        print_success("Conexão estabelecida com sucesso!")
        
        # Executar diagnósticos
        leiloeiros = analisar_leiloeiros(conn)
        auditoria = verificar_auditoria_qualidade()
        deduplicacao = verificar_deduplicacao(conn)
        agendamento = verificar_agendamento()
        
        # Fechar conexão
        conn.close()
        
        # Gerar relatório
        print_header("GERANDO RELATÓRIO FINAL")
        relatorio = gerar_relatorio(leiloeiros, auditoria, deduplicacao, agendamento)
        
        # Salvar relatório
        relatorio_path = Path("leilao-backend/RELATORIO_DIAGNOSTICO_COMPLETO.md")
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(relatorio)
        
        print_success(f"Relatório salvo em: {relatorio_path}")
        print_info("Diagnóstico completo finalizado!")
        
    except Exception as e:
        print_error(f"Erro durante o diagnóstico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

