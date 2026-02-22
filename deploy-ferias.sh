#!/bin/bash

# =============================================================================
# Script de atualização/deploy da aplicação Docker a partir do ZIP remoto.
# Uso: ./script.sh <url-do-zip>
# Alterar o ENV e o BANCO.
# Este script deve ser movido para um diretório acima do diretório do prpjeto.
# =============================================================================

# Encerra o script imediatamente em caso de erro, variável indefinida ou falha em pipe
set -euo pipefail

# Captura erros e exibe a linha onde ocorreu a falha
trap 'echo "Erro na linha $LINENO"; exit 1' ERR

# --- Validação de argumento ---
# Verifica se a URL foi passada como parâmetro
if [ -z "$1" ]; then
    echo "Uso: $0 <url>"
    exit 1
fi

# --- Variáveis ---
url="$1"

# Extrai o nome do arquivo ZIP a partir da URL (tudo após a última barra)
zipfile=$(echo "$url" | sed 's#.*/##')

# Extrai o nome do repositório (5º campo da URL, separado por '/')
repo=$(echo "$url" | cut -d'/' -f5)

# --- Download ---
# Baixa o arquivo ZIP da URL informada
wget "$url"

# --- Extração ---
# Identifica o nome do diretório raiz dentro do ZIP
dirname=$(unzip -Z1 "$zipfile" | head -n1 | cut -d/ -f1)

# Descompacta o ZIP e remove o arquivo após a extração
unzip -o "$zipfile" &&
rm "$zipfile" &&

# --- Parada dos containers atuais ---
# Para os containers existentes (ignora erro caso não estejam rodando)
docker-compose -f "$repo/docker-compose.yml" down || true

# --- Backup do banco de dados ---
# Copia o banco SQLite para o diretório atual antes de remover o projeto antigo
cp "$repo"/data/vacation_manager.db . || true

# --- Substituição do código ---
# Remove o diretório antigo do projeto
rm -rf "$repo"

# Renomeia o diretório extraído do ZIP para o nome do repositório
mv "$dirname" "$repo"

# --- Restauração do banco de dados ---
# Recria a pasta de dados e restaura o banco (ignora erro se não existir backup)
mkdir -p "$repo"/data
cp vacation_manager.db "$repo"/data/ || true

# --- Configuração e rebuild ---
# Copia o arquivo de exemplo de variáveis de ambiente como .env
cp env.example "$repo"/.env &&

# Reconstrói as imagens Docker sem cache (garante versão limpa)
docker-compose -f "$repo"/docker-compose.yml build --no-cache &&

# Inicia os containers em modo detached (background)
docker-compose -f "$repo"/docker-compose.yml up -d

# --- Limpeza ---
# Remove imagens, containers e volumes não utilizados para liberar espaço
docker system prune -f
