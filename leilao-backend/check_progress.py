#!/usr/bin/env python3
import json
import os

file_path = "results/superbid_agregado_completo.json"
if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Total: {data.get('total_properties', 0)} imoveis")
    print(f"Paginas: {data.get('pages_scraped', 0)}")
    print(f"API Total: {data.get('api_total', 'N/A')}")
    print(f"Sucesso: {data.get('success', False)}")
    if data.get('finished_at'):
        print(f"Finalizado: {data.get('finished_at')}")
    else:
        print("Status: Em andamento...")
else:
    print("Arquivo ainda nao existe")

