FROM python:3.14-slim

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretório para banco de dados
RUN mkdir -p /app/data

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação
CMD python init_db.py && gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app
