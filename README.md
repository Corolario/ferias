# Gerenciador de Férias

Sistema de gerenciamento de férias desenvolvido com Flask.

## Sobre o Projeto

A aplicação rastreia períodos de férias de funcionários e calcula um ranking baseado em pontos, onde dias de férias valem pontos diferentes dependendo do mês.

### Sistema de Pontuação

- **Alta temporada** (Janeiro, Fevereiro, Julho, Dezembro): 11 pontos/dia
- **Baixa temporada** (Agosto): 3 pontos/dia
- **Temporada média**: 5-7 pontos/dia

O ranking ordena funcionários do **menor para o maior número de pontos** (crescente) - ganha o funcionário que tirou férias nos períodos de menor demanda.

## Estrutura do Projeto

```
ferias/
├── app.py                  # Aplicação principal Flask
├── models.py               # Modelos e funções de banco de dados
├── templates/              # Templates HTML (Jinja2)
│   ├── base.html          # Template base com navbar
│   ├── login.html         # Página de login
│   ├── dashboard.html     # Dashboard principal
│   ├── funcionarios.html  # Gestão de funcionários
│   ├── ferias.html        # Gestão de férias
│   ├── ranking.html       # Ranking de pontos
│   └── configuracoes.html # Alteração de senha
├── static/                 # Arquivos estáticos
│   └── css/
│       └── style.css      # Estilos customizados
├── vacation_manager.db    # Banco de dados SQLite (criado automaticamente)
├── requirements.txt        # Dependências do projeto
├── .gitignore             # Arquivos ignorados pelo Git
└── README.md              # Este arquivo
```

## Instalação

### 1. Ativar ambiente virtual (recomendado)

```bash
# Criar ambiente virtual (se ainda não existir)
python -m venv .venv

# Ativar ambiente virtual
# Linux/Mac:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

## Executando a Aplicação

```bash
python app.py
```

A aplicação estará disponível em: **http://localhost:5000**

### Credenciais Padrão

- **Usuário:** `admin`
- **Senha:** `admin123`

## Funcionalidades

### 🏠 Dashboard
- Métricas principais (total de funcionários, períodos de férias, férias ativas)
- Lista das próximas férias programadas
- Contador de dias até cada período de férias

### 👥 Funcionários
- Adicionar novos funcionários
- Listar todos os funcionários
- Remover funcionários (com cascade de férias)

### 📅 Férias
- Cadastrar períodos de férias
- Visualizar todos os períodos cadastrados
- Remover períodos de férias

### 🏆 Ranking
- Visualização do ranking de pontos
- Tabela de referência de pontos por mês
- Detalhamento de pontos por funcionário
- Breakdown de dias e pontos por mês (expansível)

### ⚙️ Configurações
- Alteração de senha do usuário
- Validação de senha atual
- Requisito de senha mínima (6 caracteres)

## Tecnologias Utilizadas

- **Backend:** Flask 3.1.0
- **Banco de Dados:** SQLite3
- **Frontend:** Bootstrap 5.3.0, Bootstrap Icons
- **Template Engine:** Jinja2
- **Data Processing:** Pandas 2.2.3
- **Autenticação:** Sessions + SHA256 hash

## Segurança

⚠️ **IMPORTANTE para Produção:**

1. **Altere a SECRET_KEY** em `app.py`:
   ```python
   app.secret_key = 'sua-chave-secreta-segura-aqui'
   ```

2. **Use HTTPS** em produção

3. **Configure um servidor WSGI** (Gunicorn, uWSGI):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

4. **Considere usar um hash mais robusto** como bcrypt ou Argon2 no lugar de SHA256

5. **Adicione proteção CSRF** com Flask-WTF

6. **Configure variáveis de ambiente** para credenciais sensíveis

## Desenvolvimento

### Modo Debug

O modo debug está ativado por padrão em `app.py`:

```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**DESATIVE em produção** alterando para `debug=False`

### Estrutura do Banco de Dados

#### Tabela `users`
- `id` (INTEGER, PK)
- `username` (TEXT, UNIQUE)
- `password_hash` (TEXT)

#### Tabela `employees`
- `id` (INTEGER, PK)
- `name` (TEXT)
- `created_at` (TIMESTAMP)

#### Tabela `vacations`
- `id` (INTEGER, PK)
- `employee_id` (INTEGER, FK → employees.id, ON DELETE CASCADE)
- `start_date` (DATE)
- `end_date` (DATE)
- `created_at` (TIMESTAMP)

## Próximos Passos / Melhorias Futuras

- [ ] Adicionar API REST para integração com outros sistemas
- [ ] Implementar exportação de relatórios (PDF, Excel)
- [ ] Adicionar gráficos interativos (Chart.js)
- [ ] Implementar sistema de permissões (admin, user)
- [ ] Adicionar notificações por email
- [ ] Implementar filtros e busca avançada
- [ ] Adicionar testes automatizados (pytest)
- [ ] Dockerizar a aplicação
- [ ] Migrar para PostgreSQL para produção

## Suporte

Para questões ou problemas, consulte o arquivo `CLAUDE.md` no repositório.

## Licença

Este projeto foi desenvolvido para fins educacionais e de demonstração.
