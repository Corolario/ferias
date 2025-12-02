# ==========================================
# Dockerfile de Produção - Python 3.14
# ==========================================
FROM python:3.14-slim

# Metadados da imagem
LABEL maintainer="seu-email@example.com" \
      description="Sistema de Gerenciamento de Férias - Produção" \
      version="1.0"

# Variáveis de ambiente para produção
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=False \
    PORT=8000

# Instalar dependências de sistema necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Criar diretórios necessários
RUN mkdir -p /app /data && \
    chown -R appuser:appuser /app /data

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements.txt primeiro (melhor uso de cache Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY --chown=appuser:appuser . .

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
