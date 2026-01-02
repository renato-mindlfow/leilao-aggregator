# Dockerfile otimizado para LeiloHub

FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copia arquivos de dependências primeiro (para cache do Docker)
COPY pyproject.toml poetry.lock* ./

# Instala Poetry e dependências
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --only=main --no-interaction --no-ansi || poetry install --only=main --no-interaction --no-ansi --no-root

# Copia código da aplicação
COPY . .

# Expõe porta
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
