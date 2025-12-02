# ==========================================
# Stage 1: Builder - Instalar dependências
# ==========================================
FROM python:3.13-slim AS builder

# Definir variáveis de ambiente para build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependências de sistema necessárias para build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar apenas requirements.txt primeiro (cache Docker)
COPY requirements.txt .

# Instalar dependências Python em um diretório separado
RUN pip install --user --no-warn-script-location -r requirements.txt


# ==========================================
# Stage 2: Runtime - Imagem final
# ==========================================
FROM python:3.13-slim

# Metadados da imagem
LABEL maintainer="seu-email@example.com" \
      description="Sistema de Gerenciamento de Férias - Produção" \
      version="1.0"

# Variáveis de ambiente para produção
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=False \
    PORT=8000 \
    WORKERS=4 \
    TIMEOUT=120

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Criar diretórios necessários
RUN mkdir -p /app /data && \
    chown -R appuser:appuser /app /data

# Definir diretório de trabalho
WORKDIR /app

# Copiar dependências Python do builder
COPY --from=builder /root/.local /home/appuser/.local

# Copiar código da aplicação
COPY --chown=appuser:appuser . .

# Atualizar PATH para incluir binários locais do usuário
ENV PATH=/home/appuser/.local/bin:$PATH

# Mudar para usuário não-root
USER appuser

# Expor porta da aplicação
EXPOSE 8000

# Volume para persistência do banco de dados
VOLUME ["/data"]

# Health check para monitoramento
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/login', timeout=5)"

# Script de inicialização com Gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:app"]
