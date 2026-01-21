@echo off
echo.
echo ============================================================
echo      SITES COM PATHS DESCOBERTOS
echo ============================================================
echo.
python -c "import json; d=json.load(open('logs/descoberta_paths/checkpoint_20.json')); sites=[r for r in d['resultados'] if r['sucesso']]; print(f'Total: {len(sites)} sites\n'); [print(f'{i}. {s[\"nome\"]}\n   URL: {s[\"url_completa_descoberta\"]}\n   Links: {s[\"links_encontrados\"]}\n') for i,s in enumerate(sites[:10],1)]"
echo.
echo ============================================================
echo.
pause
