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
# Baixa o ZIP sempre com o mesmo nome: sem "-O", uma sobra de execução anterior
# faria o wget salvar ".zip.1" e o script seguiria usando o arquivo antigo.
wget -O "$zipfile" "$url"

# --- Extração ---
# Identifica o nome do diretório raiz dentro do ZIP. Lê a listagem inteira
# antes de cortar: com "| head -n1" o unzip morria de SIGPIPE ao continuar
# escrevendo depois que o head fechava o pipe, e o pipefail derrubava o script.
listagem=$(unzip -Z1 "$zipfile")
dirname=${listagem%%/*}

# Descompacta o ZIP e remove o arquivo após a extração
unzip -o "$zipfile" &&
rm "$zipfile" &&

# --- Parada dos containers atuais ---
# Para os containers existentes (ignora erro caso não estejam rodando)
docker-compose -f "$repo/docker-compose.yml" down || true

# --- Backup do banco de dados e das configurações ---
# Copia o banco SQLite antes de remover o projeto antigo. Sem "|| true": se o
# banco existe e a cópia falha, o deploy precisa parar em vez de seguir e apagá-lo.
if [ -f "$repo"/data/vacation_manager.db ]; then
    cp "$repo"/data/vacation_manager.db .
fi

# Preserva o .env de produção, que seria destruído junto com o diretório antigo.
# É ele que guarda a SECRET_KEY: perdê-la desloga todos os usuários.
if [ -f "$repo"/.env ]; then
    cp "$repo"/.env .env.backup
fi

# --- Substituição do código ---
# Remove o diretório antigo do projeto
rm -rf "$repo"

# Renomeia o diretório extraído do ZIP para o nome do repositório
mv "$dirname" "$repo"

# --- Restauração do banco de dados ---
# Recria a pasta de dados e restaura o banco (ignora erro se não existir backup)
mkdir -p "$repo"/data
cp vacation_manager.db "$repo"/data/ || true

# --- Configuração ---
# Restaura o .env preservado. Só no primeiro deploy ele é criado a partir do
# exemplo, já com uma SECRET_KEY própria gerada na hora.
if [ -f .env.backup ]; then
    cp .env.backup "$repo"/.env
else
    cp "$repo"/.env.example "$repo"/.env
    echo "AVISO: .env criado a partir do exemplo. Revise os demais valores."
fi

# Garante uma SECRET_KEY real em todo deploy. Sem ela o docker-compose novo
# recusa subir - e nesse ponto o diretório antigo já foi removido.
if ! grep -qE '^SECRET_KEY=.+' "$repo"/.env \
   || grep -qE '^SECRET_KEY=(change-this-in-production|your-secret-key-here-change-in-production)$' "$repo"/.env; then
    # 64 caracteres hex só com coreutils (não depende de python no host)
    chave=$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')
    sed -i '/^SECRET_KEY=/d' "$repo"/.env
    # garante quebra de linha no fim antes de acrescentar
    [ -s "$repo"/.env ] && [ -n "$(tail -c1 "$repo"/.env)" ] && echo >> "$repo"/.env
    echo "SECRET_KEY=$chave" >> "$repo"/.env
    echo "AVISO: SECRET_KEY gerada. Todos os usuários precisarão fazer login de novo."
fi

# --- Rebuild ---

# Reconstrói as imagens Docker sem cache (garante versão limpa)
docker-compose -f "$repo"/docker-compose.yml build --no-cache &&

# Inicia os containers em modo detached (background)
docker-compose -f "$repo"/docker-compose.yml up -d

# --- Limpeza ---
# Remove imagens, containers e volumes não utilizados para liberar espaço
docker system prune -f
