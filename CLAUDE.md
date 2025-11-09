# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão Geral do Projeto

Este é um sistema de gerenciamento de férias brasileiro desenvolvido com Streamlit e SQLite. A aplicação rastreia períodos de férias de funcionários e calcula um ranking baseado em pontos, onde dias de férias valem pontos diferentes dependendo do mês (meses de alta temporada como janeiro, julho e dezembro valem mais pontos).

## Executando a Aplicação

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar a aplicação
streamlit run main.py
```

Credenciais padrão: `admin` / `admin123`

## Arquitetura

### Estrutura da Aplicação

A aplicação usa uma **arquitetura modular baseada em tabs**:

- `main.py` - Ponto de entrada que configura o Streamlit e orquestra as 4 abas principais
- `database.py` - Função de inicialização do banco de dados (atualmente incompleta/não utilizada)
- Diretório `pags/` - Contém módulos de renderização para cada aba:
  - `dashboard.py` - Visão geral do dashboard
  - `funcionarios.py` - Gerenciamento de funcionários
  - `ferias.py` - Gerenciamento de períodos de férias
  - `ranking.py` - Exibição do ranking por pontos

**Importante**: A implementação atual nos módulos `pags/` é apenas código placeholder. A implementação real e funcional existe no arquivo monolítico `oldapp.py`. A refatoração para estrutura modular (main.py + pags/) está incompleta.

### Schema do Banco de Dados

Banco de dados SQLite (`vacation_manager.db`) com 3 tabelas:

1. **users** - Autenticação (username, password_hash)
2. **employees** - Registros de funcionários (id, name, created_at)
3. **vacations** - Períodos de férias com FK para employees (id, employee_id, start_date, end_date, created_at)

O banco usa `ON DELETE CASCADE` para o relacionamento employee-vacation.

### Sistema de Ranking/Pontos

A lógica de negócio central é o **cálculo de pontos baseado em meses**:

- Cada dia de férias é multiplicado pelo valor de pontos do mês
- Meses de alta temporada (Jan, Fev, Jul, Dez): 11 pontos/dia
- Baixa temporada (Agosto): 3 pontos/dia
- Outros meses: 5-7 pontos/dia

O cálculo em `calculate_vacation_points()` (oldapp.py:200-228) itera por cada dia de um período de férias, distribui os dias entre os meses, depois multiplica pelos valores de pontos dos meses. Isso permite que férias de múltiplos meses sejam pontuadas corretamente.

O ranking ordena funcionários do **menor para o maior número de pontos** (crescente) - ganha o funcionário que tirou férias nos períodos de menor demanda.

## Notas de Desenvolvimento

### Estado Atual

- `oldapp.py` contém a aplicação completa e funcional (580 linhas)
- `main.los `pags/` representam uma tentativa incompleta de refatoração
- Todos os módulos de página atualmente renderizam apenas texto placeholder ("333333333333")
- O arquivo `database.py` tem a lógica de init mas não é importado/usado no main.py

### Para Completar a Refatoração

O código funcional de `oldapp.py` precisa ser extraído para a estrutura modular:

1. Mover funções de banco de dados do oldapp.py para database.py
2. Extrair a lógica de cada aba (dashboard, funcionarios, ferias, ranking) para os respectivos módulos em pags/
3. Mover lógica de autenticação para um módulo separado ou manter no main.py
4. Garantir que o gerenciamento de session state funcione entre os módulos

### Padrão de Tratamento de Datas

O código usa um padrão específico para formatação de datas:
- Banco de dados armazena datas como strings 'YYYY-MM-DD'
- UI exibe datas como 'dd/mm/aaaa' (formato brasileiro)
- Conversões acontecem nas funções getter usando pandas: `pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')`

### Session State

O session state do Streamlit é usado para:
- `logged_in` - Status de autenticação
- `username` - Usuário atual
- `show_employee_success` / `show_vacation_success` - Flags de mensagens de sucesso

## Testes

Não existe suite de testes atualmente. Testes manuais requerem:

1. Executar o app e testar operações CRUD de cada aba
2. Verificar cálculos de pontos com períodos de férias de múltiplos meses
3. Testar casos extremos: férias de um dia, férias atravessando ano, cascade de exclusão de funcionário
