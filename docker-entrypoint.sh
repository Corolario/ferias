#!/bin/bash
set -e

# Corrigir permissões do diretório /data para appuser
chown -R appuser:appuser /data

# Executar comando como appuser
exec gosu appuser "$@"
