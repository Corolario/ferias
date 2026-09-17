# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão Geral do Projeto

Este é um sistema de gerenciamento de férias brasileiro desenvolvido com Flask e SQLite. A aplicação rastreia períodos de férias de funcionários e calcula um ranking baseado em pontos, onde dias de férias valem pontos diferentes dependendo do mês (meses de alta temporada como janeiro, julho e dezembro valem mais pontos).

## Executando a Aplicação

```bash
# Ativar ambiente virtual (opcional mas recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Executar a aplicação
python app.py
```

Acesse: `http://localhost:5000`

Credenciais padrão: `admin` / `admin123`

## Arquitetura

### Estrutura da Aplicação

A aplicação usa uma **arquitetura Flask MVC simplificada**:

- `app.py` - Aplicação Flask principal com todas as rotas e lógica de controle
- `models.py` - Funções de banco de dados e lógica de negócio
- `templates/` - Templates Jinja2 para renderização HTML:
  - `base.html` - Template base com navbar e estrutura comum
  - `login.html` - Página de autenticação
  - `dashboard.html` - Dashboard com métricas e próximas férias
  - `funcionarios.html` - CRUD de funcionários
  - `ferias.html` - CRUD de períodos de férias
  - `ranking.html` - Exibição do ranking por pontos
  - `configuracoes.html` - Alteração de senha
- `static/css/` - Arquivos CSS customizados
- `vacation_manager.db` - Banco de dados SQLite (criado automaticamente)

### Schema do Banco de Dados

Banco de dados SQLite (`vacation_manager.db`) com 3 tabelas:

1. **users** - Autenticação (id, username, password_hash)
2. **employees** - Registros de funcionários (id, name, created_at)
3. **vacations** - Períodos de férias com FK para employees (id, employee_id, start_date, end_date, created_at)

O banco usa `ON DELETE CASCADE` para o relacionamento employee-vacation.

### Sistema de Ranking/Pontos

A lógica de negócio central é o **cálculo de pontos baseado em meses**:

- Cada dia de férias é multiplicado pelo valor de pontos do mês
- Meses de alta temporada (Jan, Fev, Jul, Dez): 11 pontos/dia
- Baixa temporada (Agosto): 3 pontos/dia
- Outros meses: 5-7 pontos/dia

O cálculo em `calculate_vacation_points()` (models.py) itera por cada dia de um período de férias, distribui os dias entre os meses, depois multiplica pelos valores de pontos dos meses. Isso permite que férias de múltiplos meses sejam pontuadas corretamente.

O ranking ordena funcionários do **menor para o maior número de pontos** (crescente) - ganha o funcionário que tirou férias nos períodos de menor demanda.

## Rotas da Aplicação

### Autenticação
- `GET /` - Redireciona para dashboard ou login
- `GET/POST /login` - Página de login
- `GET /logout` - Encerrar sessão

### Páginas Principais (requerem autenticação)
- `GET /dashboard` - Dashboard com métricas
- `GET/POST /funcionarios` - Listar e adicionar funcionários
- `POST /funcionarios/delete/<id>` - Remover funcionário
- `GET/POST /ferias` - Listar e adicionar férias
- `POST /ferias/delete/<id>` - Remover período de férias
- `GET /ranking` - Exibir ranking de pontos
- `GET/POST /configuracoes` - Alterar senha

## Padrões de Código

### Tratamento de Datas

O código usa um padrão específico para formatação de datas:
- Banco de dados armazena datas como strings 'YYYY-MM-DD'
- UI exibe datas como 'dd/mm/aaaa' (formato brasileiro)
- Conversões acontecem nas funções getter usando pandas: `pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')`
- Input type="date" em HTML usa formato 'YYYY-MM-DD'

### Sessions

Flask sessions são usadas para:
- `username` - Usuário autenticado
- Flash messages para feedback ao usuário (success, danger, warning, info)

### Decorator de Autenticação

Rotas protegidas usam o decorator `@login_required` que:
1. Verifica se 'username' existe na sessão
2. Redireciona para login se não autenticado
3. Exibe flash message de aviso

## Tecnologias e Dependências

- **Flask 3.1.3** - Framework web
- **Pandas 3.0.5** - Processamento de dados
- **bcrypt 5.0.0** - Hash de senhas
- **Flask-WTF 1.3.0** - Proteção CSRF
- **Flask-Limiter 4.1.1** - Limite de tentativas de login
- **ReportLab 5.0.1** - Geração de PDF
- **Gunicorn 26.2.0** - Servidor WSGI de produção
- **SQLite3** - Banco de dados (built-in Python)
- **Bootstrap 5.3.8** - Framework CSS (via CDN)
- **Jinja2** - Template engine (incluído com Flask)

As versões são fixadas em `requirements.txt`; mantenha os dois lugares em sincronia.

## Desenvolvimento

### Estrutura de Arquivos

```
ferias/
├── app.py                  # Aplicação Flask principal
├── models.py               # Funções de BD e lógica
├── templates/              # Templates Jinja2
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── funcionarios.html
│   ├── ferias.html
│   ├── ranking.html
│   └── configuracoes.html
├── static/
│   └── css/
│       └── style.css       # CSS customizado
├── vacation_manager.db     # Banco de dados
├── requirements.txt        # Dependências
├── .gitignore             # Git ignore
└── README.md              # Documentação
```

### Adicionando Novas Funcionalidades

1. **Nova rota**: Adicionar em `app.py` com decorator `@login_required` se necessário
2. **Nova função de BD**: Adicionar em `models.py`
3. **Nova página**: Criar template em `templates/` estendendo `base.html`
4. **Novo estilo**: Adicionar em `static/css/style.css`

### Debug Mode

O app roda em modo debug por padrão (`debug=True` em app.py).

**IMPORTANTE**: Desativar debug em produção e configurar:
- SECRET_KEY segura (usar variável de ambiente)
- Servidor WSGI (Gunicorn, uWSGI)
- HTTPS
- Proteção CSRF

## Testes

Não existe suite de testes automatizados atualmente. Testes manuais devem verificar:

1. Autenticação (login/logout)
2. CRUD de funcionários
3. CRUD de férias com validação de datas
4. Cálculo correto de pontos no ranking
5. Cascade delete (remover funcionário remove suas férias)
6. Alteração de senha
7. Flash messages em todas as operações
8. Responsividade mobile

### Casos de Teste Importantes

- Férias de um único dia
- Férias atravessando múltiplos meses
- Férias atravessando ano novo
- Período de férias com data inicial > data final (deve ser rejeitado)
- Funcionário sem férias cadastradas (deve aparecer no ranking com 0 pontos)

## Segurança

Já implementado:
- Senhas com **bcrypt** (`hash_password`/`verify_password` em `models.py`), com salt por senha
- **Proteção CSRF** ativa via Flask-WTF (`CSRFProtect` em `app.py`)
- **SECRET_KEY** obrigatória em produção: a aplicação recusa subir com a variável ausente ou
  com um dos valores de exemplo, porque uma chave pública permite forjar cookies de sessão
- **Limite de tentativas de login** com Flask-Limiter (5 POSTs por 15 min por IP)
- Headers de segurança e cookies de sessão com `HttpOnly` e `SameSite=Lax`

### Limite de 72 bytes nas senhas

O bcrypt só considera os primeiros 72 **bytes** da senha, e a partir da versão 5.0 levanta
`ValueError` acima disso. Por isso `senha_dentro_do_limite()` valida o tamanho antes de gerar
ou conferir o hash. Lembre que acentos ocupam 2 bytes em UTF-8: uma senha de 40 caracteres
acentuados já estoura o limite.

### Identificação do visitante atrás do Cloudflare

Em produção a aplicação fica atrás de um Cloudflare Tunnel, com o `cloudflared` em outra
máquina da rede. Nesse arranjo `request.remote_addr` é sempre o mesmo IP - o do `cloudflared` -
para todos os visitantes, então o limite de tentativas usa o header `CF-Connecting-IP`
(função `client_ip()` em `app.py`). Isso é controlado por `TRUST_CF_HEADER`, que deve ficar
desligado em qualquer ambiente onde a aplicação seja acessível diretamente: quem alcança a
porta 8000 sem passar pelo Cloudflare consegue forjar esse header e escapar do limite.

Se um dia um nginx/Traefik entrar na frente no lugar do túnel, será preciso `ProxyFix` para
ler o `X-Forwarded-For`.

⚠️ **Pendências conhecidas**:
- Usuário `admin`/`admin123` criado automaticamente, sem forçar troca no primeiro acesso
- Assets do Bootstrap via CDN sem atributo `integrity` (SRI)
- Detalhes de exceção exibidos ao usuário no dashboard e na geração de PDF
- `SESSION_COOKIE_SECURE` com padrão `False`; defina `True` no `.env` (o acesso é por HTTPS)
- Debug mode ativado ao rodar `python app.py` (o container usa Gunicorn, sem debug)
