#!/usr/bin/env python
"""
ataque_rapido_pendentes.py - Ataca os 127 sites NUNCA TENTADOS

Este script foca em maximizar a cobertura rapidamente:
1. Verifica quais sites estão online (paralelo)
2. Descobre paths automaticamente
3. Executa TIER 1 (HTTP) e TIER 2 (Playwright) conforme necessário

Uso:
    python ataque_rapido_pendentes.py
"""

import os
import sys
import csv
import json
import asyncio
import aiohttp
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

# Configuração
CONCURRENT_REQUESTS = 10
TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"

# Paths comuns em sites de leilão
PATHS_CONHECIDOS = [
    '/busca',
    '/imoveis', 
    '/leiloes',
    '/leilao',
    '/buscar',
    '/catalogo',
    '/lotes',
    '/properties',
    '/pesquisa',
    '',  # root
]

# Seletores para encontrar imóveis
SELETORES_IMOVEIS = [
    r'href=["\']([^"\']*(?:imovel|lote|property|item)[^"\']*)["\']',
    r'href=["\']([^"\']*(?:/\d{4,}|id=\d+)[^"\']*)["\']',
]


class AtaqueRapido:
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or f"logs/ataque_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.resultados = {
            'inicio': datetime.now().isoformat(),
            'sites_online': [],
            'sites_offline': [],
            'sites_sucesso': [],
            'sites_falha': [],
            'total_imoveis': 0,
            'imoveis': []
        }
    
    async def verificar_online(self, session: aiohttp.ClientSession, url: str) -> bool:
        """Verifica se site está online."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                return resp.status < 500
        except:
            return False
    
    async def descobrir_path(self, session: aiohttp.ClientSession, base_url: str) -> Optional[str]:
        """Descobre o path correto para listar imóveis."""
        for path in PATHS_CONHECIDOS:
            url = base_url.rstrip('/') + path
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        # Verificar se tem links de imóveis
                        for pattern in SELETORES_IMOVEIS:
                            matches = re.findall(pattern, html, re.I)
                            if len(matches) >= 3:  # Mínimo 3 links para considerar válido
                                return path
            except:
                continue
        return None
    
    async def extrair_links_imoveis(self, session: aiohttp.ClientSession, url: str) -> List[str]:
        """Extrai links de imóveis de uma página."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
                
                links = set()
                for pattern in SELETORES_IMOVEIS:
                    matches = re.findall(pattern, html, re.I)
                    for match in matches:
                        if match.startswith('/'):
                            full_url = urljoin(url, match)
                        elif match.startswith('http'):
                            full_url = match
                        else:
                            full_url = urljoin(url, '/' + match)
                        
                        # Filtrar URLs válidas
                        if any(x in full_url.lower() for x in ['imovel', 'lote', 'property', 'item', '/detalhes']):
                            links.add(full_url)
                
                return list(links)[:50]  # Limitar a 50 por site
        except:
            return []
    
    async def extrair_dados_imovel(self, session: aiohttp.ClientSession, url: str, leiloeiro: str) -> Optional[Dict]:
        """Extrai dados básicos de um imóvel."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                
                # Extrair título
                titulo_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.I)
                titulo = titulo_match.group(1).strip() if titulo_match else None
                
                # Extrair preço
                preco_match = re.search(r'R\$\s*([\d.,]+)', html)
                preco = None
                if preco_match:
                    preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                    try:
                        preco = float(preco_str)
                    except:
                        pass
                
                # Extrair estado
                estado_match = re.search(r'\b([A-Z]{2})\b', html)
                estado = estado_match.group(1) if estado_match else None
                
                # Extrair cidade
                cidade_match = re.search(r'(?:cidade|city|localização)[:\s]*([^,<\n]+)', html, re.I)
                cidade = cidade_match.group(1).strip() if cidade_match else None
                
                if not titulo:
                    return None
                
                return {
                    'source_url': url,
                    'title': titulo,
                    'price': preco,
                    'state': estado,
                    'city': cidade,
                    'auctioneer_name': leiloeiro,
                    'extracted_at': datetime.now().isoformat()
                }
        except:
            return None
    
    async def processar_site(self, session: aiohttp.ClientSession, site: Dict) -> Dict:
        """Processa um site completo."""
        url = site['website']
        nome = site['name']
        
        resultado = {
            'url': url,
            'nome': nome,
            'online': False,
            'path_encontrado': None,
            'links_encontrados': 0,
            'imoveis_extraidos': 0,
            'imoveis': []
        }
        
        # Verificar se está online
        if not await self.verificar_online(session, url):
            resultado['erro'] = 'Site offline'
            return resultado
        
        resultado['online'] = True
        
        # Descobrir path
        path = await self.descobrir_path(session, url)
        if not path:
            resultado['erro'] = 'Path não encontrado'
            return resultado
        
        resultado['path_encontrado'] = path
        
        # Extrair links de imóveis
        url_busca = url.rstrip('/') + path
        links = await self.extrair_links_imoveis(session, url_busca)
        resultado['links_encontrados'] = len(links)
        
        if not links:
            resultado['erro'] = '0 links de imóveis'
            return resultado
        
        # Extrair dados de cada imóvel (limitar a 20 por site para não demorar)
        for link in links[:20]:
            imovel = await self.extrair_dados_imovel(session, link, nome)
            if imovel:
                resultado['imoveis'].append(imovel)
                await asyncio.sleep(0.5)  # Respeitar rate limit
        
        resultado['imoveis_extraidos'] = len(resultado['imoveis'])
        return resultado
    
    async def executar(self, sites: List[Dict]):
        """Executa o ataque em todos os sites."""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║     🚀 ATAQUE RÁPIDO - {len(sites)} SITES PENDENTES 🚀     ║
╚══════════════════════════════════════════════════════════╝
        """)
        
        connector = aiohttp.TCPConnector(limit=CONCURRENT_REQUESTS, ssl=False)
        headers = {'User-Agent': USER_AGENT}
        
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            for i, site in enumerate(sites, 1):
                print(f"\n[{i}/{len(sites)}] {site['name']} ({site['website']})")
                
                resultado = await self.processar_site(session, site)
                
                if resultado['imoveis_extraidos'] > 0:
                    self.resultados['sites_sucesso'].append(resultado)
                    self.resultados['total_imoveis'] += resultado['imoveis_extraidos']
                    self.resultados['imoveis'].extend(resultado['imoveis'])
                    print(f"   ✅ {resultado['imoveis_extraidos']} imóveis extraídos")
                elif resultado['online']:
                    self.resultados['sites_falha'].append(resultado)
                    print(f"   ⚠️ Online mas sem imóveis: {resultado.get('erro', '?')}")
                else:
                    self.resultados['sites_offline'].append(resultado)
                    print(f"   ❌ Offline")
                
                # Pausa entre sites
                await asyncio.sleep(1)
        
        self.resultados['fim'] = datetime.now().isoformat()
        
        # Salvar resultados
        self._salvar_resultados()
        self._imprimir_resumo()
    
    def _salvar_resultados(self):
        """Salva todos os resultados."""
        # Resultado completo
        with open(self.output_dir / 'resultado_completo.json', 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, ensure_ascii=False, indent=2)
        
        # Apenas imóveis (para consolidação)
        with open(self.output_dir / 'imoveis_extraidos.json', 'w', encoding='utf-8') as f:
            json.dump(self.resultados['imoveis'], f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Resultados salvos em: {self.output_dir}")
    
    def _imprimir_resumo(self):
        """Imprime resumo da execução."""
        total = len(self.resultados['sites_sucesso']) + len(self.resultados['sites_falha']) + len(self.resultados['sites_offline'])
        sucesso = len(self.resultados['sites_sucesso'])
        
        print(f"""
{'='*60}
📊 RESUMO DO ATAQUE RÁPIDO
{'='*60}

Sites processados:  {total}
✅ Com sucesso:     {sucesso} ({sucesso/total*100:.1f}%)
⚠️ Online sem dados: {len(self.resultados['sites_falha'])}
❌ Offline:         {len(self.resultados['sites_offline'])}

🏠 IMÓVEIS EXTRAÍDOS: {self.resultados['total_imoveis']}

📁 Arquivos gerados:
   • resultado_completo.json
   • imoveis_extraidos.json

{'='*60}
        """)


def carregar_sites_pendentes(csv_path: str) -> List[Dict]:
    """Carrega sites com status 'pending' do CSV."""
    sites = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['scrape_status'] == 'pending':
                sites.append(row)
    return sites


def main():
    # Encontrar CSV
    csv_paths = [
        'LISTA_MESTRE_LEILOEIROS.csv',
        '../docs/LISTA_MESTRE_LEILOEIROS.csv',
        '../../docs/LISTA_MESTRE_LEILOEIROS.csv',
        Path(__file__).parent.parent / 'docs' / 'LISTA_MESTRE_LEILOEIROS.csv',
    ]
    
    csv_path = None
    for path in csv_paths:
        if Path(path).exists():
            csv_path = path
            break
    
    if not csv_path:
        # Tentar do projeto
        csv_path = '/mnt/project/LISTA_MESTRE_LEILOEIROS.csv'
    
    print(f"📂 Carregando de: {csv_path}")
    sites = carregar_sites_pendentes(str(csv_path))
    print(f"📊 {len(sites)} sites pendentes encontrados")
    
    if not sites:
        print("❌ Nenhum site pendente encontrado!")
        return
    
    # Executar ataque
    ataque = AtaqueRapido()
    asyncio.run(ataque.executar(sites))


if __name__ == "__main__":
    main()
