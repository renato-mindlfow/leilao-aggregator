#!/bin/bash

# Script de deploy para Fly.io

echo "=========================================="
echo "DEPLOY LEILOHUB PARA FLY.IO"
echo "=========================================="

# Verifica se flyctl está instalado
if ! command -v flyctl &> /dev/null; then
    echo "Erro: flyctl não está instalado"
    echo "Instale com: curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Verifica autenticação
flyctl auth whoami || {
    echo "Erro: Não autenticado no Fly.io"
    echo "Execute: flyctl auth login"
    exit 1
}

# Configura secrets (se necessário)
echo ""
echo "Configurando secrets..."

if [ -f .env ]; then
    source .env
    
    if [ -n "$SUPABASE_URL" ]; then
        flyctl secrets set SUPABASE_URL="$SUPABASE_URL" --app leilohub-backend
    fi
    
    if [ -n "$SUPABASE_KEY" ]; then
        flyctl secrets set SUPABASE_KEY="$SUPABASE_KEY" --app leilohub-backend
    fi
    
    if [ -n "$SCRAPINGBEE_API_KEY" ]; then
        flyctl secrets set SCRAPINGBEE_API_KEY="$SCRAPINGBEE_API_KEY" --app leilohub-backend
    fi
    
    if [ -n "$OPENAI_API_KEY" ]; then
        flyctl secrets set OPENAI_API_KEY="$OPENAI_API_KEY" --app leilohub-backend
    fi
fi

# Deploy
echo ""
echo "Iniciando deploy..."
flyctl deploy --app leilohub-backend

# Status
echo ""
echo "Status do deploy:"
flyctl status --app leilohub-backend

echo ""
echo "=========================================="
echo "DEPLOY CONCLUÍDO!"
echo "=========================================="
echo ""
echo "URL: https://leilohub-backend.fly.dev"
echo "Dashboard: https://fly.io/apps/leilohub-backend"

