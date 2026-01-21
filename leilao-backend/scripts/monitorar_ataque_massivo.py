#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor the progress of the massive attack in real-time
"""

import json
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
import sys
import codecs

# Fix encoding for Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def limpar_tela():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def formatar_duracao(segundos):
    """Formata duração em horas:minutos:segundos"""
    return str(timedelta(seconds=int(segundos)))

def encontrar_ultimo_log():
    """Encontra o diretório de logs mais recente"""
    logs_base = Path(__file__).parent.parent / "logs" / "ataque_massivo"
    
    if not logs_base.exists():
        return None
    
    # Pegar o diretório mais recente
    diretorios = sorted([d for d in logs_base.iterdir() if d.is_dir()], reverse=True)
    
    if diretorios:
        return diretorios[0]
    
    return None

def carregar_resultados(logs_dir):
    """Carrega os resultados parciais das ondas"""
    resultados = {}
    
    for i in range(1, 4):
        arquivo = logs_dir / f"onda{i}_parcial.json"
        if arquivo.exists():
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    resultados[f"onda{i}"] = json.load(f)
            except:
                pass
    
    # Tentar carregar resultado final se existir
    arquivo_final = logs_dir / "resultados_ataque_massivo_FINAL.json"
    if arquivo_final.exists():
        try:
            with open(arquivo_final, 'r', encoding='utf-8') as f:
                resultados['final'] = json.load(f)
        except:
            pass
    
    return resultados

def mostrar_dashboard(logs_dir):
    """Mostra dashboard com progresso em tempo real"""
    
    while True:
        limpar_tela()
        
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 20 + "🚀 MONITOR DE ATAQUE MASSIVO 🚀" + " " * 26 + "║")
        print("╠" + "═" * 78 + "╣")
        
        resultados = carregar_resultados(logs_dir)
        
        if not resultados:
            print("║  ⏳ Aguardando início da execução...                                      ║")
            print("╚" + "═" * 78 + "╝")
            time.sleep(5)
            continue
        
        # Estatísticas globais
        total_processados = 0
        total_sucesso = 0
        total_falhas = 0
        total_imoveis = 0
        
        print("║                                                                              ║")
        print("║  📊 PROGRESSO POR ONDA:                                                      ║")
        print("║" + "─" * 78 + "║")
        
        for onda_key in ['onda1', 'onda2', 'onda3']:
            if onda_key in resultados:
                dados = resultados[onda_key]['resultados']
                total = dados.get('total', 0)
                processados = len(dados.get('detalhes', []))
                sucesso_t1 = dados.get('sucesso_tier1', 0)
                sucesso_t2 = dados.get('sucesso_tier2', 0)
                falhas = dados.get('falha', 0)
                imoveis = dados.get('imoveis', 0)
                
                sucesso_total = sucesso_t1 + sucesso_t2
                taxa = (sucesso_total / processados * 100) if processados > 0 else 0
                progresso = (processados / total * 100) if total > 0 else 0
                
                nome_onda = resultados[onda_key].get('nome', onda_key.upper())
                
                print(f"║                                                                              ║")
                print(f"║  {onda_key.upper()}: {nome_onda[:50]:<50}  ║")
                print(f"║    Progresso: {processados}/{total} sites ({progresso:.0f}%)                       {'':>{70-len(str(processados))-len(str(total))-20}}║")
                
                # Barra de progresso
                barra_len = 60
                preenchido = int(barra_len * progresso / 100)
                barra = "█" * preenchido + "░" * (barra_len - preenchido)
                print(f"║    [{barra}]  ║")
                
                print(f"║    ✅ Sucesso: {sucesso_total} ({taxa:.0f}%) | T1: {sucesso_t1} | T2: {sucesso_t2}                 {'':>{60-len(str(sucesso_total))-len(str(sucesso_t1))-len(str(sucesso_t2))-20}}║")
                print(f"║    ❌ Falhas: {falhas}                                                        {'':>{70-len(str(falhas))-15}}║")
                print(f"║    🏘️  Imóveis: {imoveis:,}                                                     {'':>{70-len(str(imoveis))-15}}║")
                
                total_processados += processados
                total_sucesso += sucesso_total
                total_falhas += falhas
                total_imoveis += imoveis
        
        print("║" + "─" * 78 + "║")
        print("║                                                                              ║")
        print("║  🎯 TOTAIS ACUMULADOS:                                                       ║")
        print(f"║    Sites processados: {total_processados}                                             {'':>{70-len(str(total_processados))-22}}║")
        print(f"║    Sites com sucesso: {total_sucesso}                                             {'':>{70-len(str(total_sucesso))-22}}║")
        print(f"║    Sites com falha:   {total_falhas}                                             {'':>{70-len(str(total_falhas))-22}}║")
        print(f"║    Total de imóveis:  {total_imoveis:,}                                        {'':>{70-len(str(total_imoveis))-22}}║")
        
        if total_processados > 0:
            taxa_global = (total_sucesso / total_processados * 100)
            print(f"║    Taxa de sucesso:   {taxa_global:.1f}%                                        {'':>{70-6}}║")
        
        print("║                                                                              ║")
        print("║" + "─" * 78 + "║")
        
        # Verificar se terminou
        if 'final' in resultados:
            fim = datetime.fromisoformat(resultados['final']['fim'])
            inicio = datetime.fromisoformat(resultados['final']['inicio'])
            duracao = (fim - inicio).total_seconds()
            
            print("║                                                                              ║")
            print("║  ✅ ATAQUE MASSIVO CONCLUÍDO!                                                ║")
            print(f"║    Duração total: {formatar_duracao(duracao)}                                     {'':>{70-len(formatar_duracao(duracao))-18}}║")
            print("║                                                                              ║")
            print("╚" + "═" * 78 + "╝")
            print(f"\n📁 Logs salvos em: {logs_dir}\n")
            break
        else:
            print("║                                                                              ║")
            print("║  ⏳ Em execução... (Atualizando a cada 10 segundos)                         ║")
            print("║     Pressione Ctrl+C para sair do monitor (o ataque continuará)             ║")
            print("║                                                                              ║")
            print("╚" + "═" * 78 + "╝")
            print(f"\n📁 Logs: {logs_dir}")
            print(f"🕐 Última atualização: {datetime.now().strftime('%H:%M:%S')}\n")
            
            time.sleep(10)

def main():
    """Função principal"""
    print("🔍 Procurando logs de ataque massivo...")
    
    logs_dir = encontrar_ultimo_log()
    
    if not logs_dir:
        print("❌ Nenhum log encontrado. Certifique-se de que o ataque massivo está em execução.")
        print("   Execute: python scripts/executar_ataque_massivo.py")
        sys.exit(1)
    
    print(f"✅ Logs encontrados: {logs_dir}")
    print("📊 Iniciando monitor...\n")
    
    time.sleep(2)
    
    try:
        mostrar_dashboard(logs_dir)
    except KeyboardInterrupt:
        print("\n\n⚠️ Monitor interrompido. O ataque massivo continua em execução.")
        print(f"📁 Logs: {logs_dir}\n")

if __name__ == "__main__":
    main()
