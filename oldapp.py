import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Gerenciador de Férias",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Estilos CSS minimalistas
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Funções de banco de dados
def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    # Tabela de funcionários
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de férias
    c.execute('''
        CREATE TABLE IF NOT EXISTS vacations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE
        )
    ''')
    
    # Criar usuário admin padrão se não existir
    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)', 
              ('admin', password_hash))
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Gera hash SHA256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    """Verifica credenciais de login"""
    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    password_hash = hash_password(password)
    
    c.execute('SELECT id FROM users WHERE username = ? AND password_hash = ?', 
              (username, password_hash))
    result = c.fetchone()
    conn.close()
    
    return result is not None

def change_password(username, new_password):
    """Altera a senha do usuário"""
    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    password_hash = hash_password(new_password)
    
    c.execute('UPDATE users SET password_hash = ? WHERE username = ?', 
              (password_hash, username))
    conn.commit()
    conn.close()

# Funções de gerenciamento de funcionários
def add_employee(name):
    """Adiciona um novo funcionário"""
    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    c.execute('INSERT INTO employees (name) VALUES (?)', (name,))
    conn.commit()
    conn.close()

def get_employees():
    """Retorna lista de funcionários"""
    conn = sqlite3.connect('vacation_manager.db')
    df = pd.read_sql_query('SELECT * FROM employees ORDER BY name', conn)
    conn.close()
    return df

def delete_employee(employee_id):
    """Remove um funcionário e suas férias"""
    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    c.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
    conn.commit()
    conn.close()

# Funções de gerenciamento de férias
def add_vacation(employee_id, start_date, end_date):
    """Adiciona período de férias"""
    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    c.execute('INSERT INTO vacations (employee_id, start_date, end_date) VALUES (?, ?, ?)',
              (employee_id, start_date, end_date))
    conn.commit()
    conn.close()

def get_vacations():
    """Retorna todas as férias com nome do funcionário"""
    conn = sqlite3.connect('vacation_manager.db')
    query = '''
        SELECT v.id, e.name, v.start_date, v.end_date, e.id as employee_id
        FROM vacations v
        JOIN employees e ON v.employee_id = e.id
        ORDER BY v.start_date DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Formatar datas para dd/mm/aaaa
    if not df.empty:
        df['start_date'] = pd.to_datetime(df['start_date']).dt.strftime('%d/%m/%Y')
        df['end_date'] = pd.to_datetime(df['end_date']).dt.strftime('%d/%m/%Y')
    
    return df

def delete_vacation(vacation_id):
    """Remove um período de férias"""
    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    c.execute('DELETE FROM vacations WHERE id = ?', (vacation_id,))
    conn.commit()
    conn.close()

def get_employee_vacations(employee_id):
    """Retorna férias de um funcionário específico"""
    conn = sqlite3.connect('vacation_manager.db')
    query = '''
        SELECT id, start_date, end_date
        FROM vacations
        WHERE employee_id = ?
        ORDER BY start_date DESC
    '''
    df = pd.read_sql_query(query, conn, params=(employee_id,))
    conn.close()
    
    # Formatar datas para dd/mm/aaaa
    if not df.empty:
        df['start_date'] = pd.to_datetime(df['start_date']).dt.strftime('%d/%m/%Y')
        df['end_date'] = pd.to_datetime(df['end_date']).dt.strftime('%d/%m/%Y')
    
    return df

# Funções de ranking
def get_month_points():
    """Retorna a tabela de pontos por mês"""
    return {
        1: 11,   # Janeiro
        2: 11,   # Fevereiro
        3: 7,    # Março
        4: 5,    # Abril
        5: 5,    # Maio
        6: 6,    # Junho
        7: 11,   # Julho
        8: 3,    # Agosto
        9: 5,    # Setembro
        10: 6,   # Outubro
        11: 6,   # Novembro
        12: 11   # Dezembro
    }

def calculate_vacation_points(start_date, end_date):
    """Calcula pontos de um período de férias distribuindo por mês"""
    month_points = get_month_points()
    total_points = 0
    days_by_month = {}
    
    # Converter para datetime se necessário
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    current_date = start_date
    
    # Iterar por cada dia do período
    while current_date <= end_date:
        month = current_date.month
        
        if month not in days_by_month:
            days_by_month[month] = 0
        days_by_month[month] += 1
        
        current_date = current_date.replace(day=current_date.day + 1) if current_date.day < 28 else current_date.replace(month=current_date.month + 1 if current_date.month < 12 else 1, day=1, year=current_date.year + (1 if current_date.month == 12 else 0))
    
    # Calcular pontos por mês
    for month, days in days_by_month.items():
        total_points += days * month_points[month]
    
    return total_points, days_by_month

def get_employee_ranking():
    """Calcula o ranking de todos os funcionários"""
    conn = sqlite3.connect('vacation_manager.db')
    
    # Buscar todos os funcionários
    employees_query = 'SELECT id, name FROM employees ORDER BY name'
    employees_df = pd.read_sql_query(employees_query, conn)
    
    # Buscar todas as férias
    vacations_query = '''
        SELECT employee_id, start_date, end_date
        FROM vacations
    '''
    vacations_df = pd.read_sql_query(vacations_query, conn)
    conn.close()
    
    ranking_data = []
    
    for _, emp in employees_df.iterrows():
        employee_id = emp['id']
        employee_name = emp['name']
        
        # Filtrar férias do funcionário
        emp_vacations = vacations_df[vacations_df['employee_id'] == employee_id]
        
        total_points = 0
        total_days = 0
        month_details = {}
        
        # Calcular pontos de cada período de férias
        for _, vac in emp_vacations.iterrows():
            points, days_by_month = calculate_vacation_points(vac['start_date'], vac['end_date'])
            total_points += points
            
            # Somar dias totais
            start = datetime.strptime(vac['start_date'], '%Y-%m-%d').date()
            end = datetime.strptime(vac['end_date'], '%Y-%m-%d').date()
            total_days += (end - start).days + 1
            
            # Agregar dias por mês
            for month, days in days_by_month.items():
                if month not in month_details:
                    month_details[month] = 0
                month_details[month] += days
        
        ranking_data.append({
            'name': employee_name,
            'total_points': total_points,
            'total_days': total_days,
            'month_details': month_details
        })
    
    # Ordenar por pontos (crescente - menor para maior)
    ranking_data.sort(key=lambda x: x['total_points'])
    
    return ranking_data

# Inicializar banco de dados
init_db()

# Inicializar estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Tela de Login
def login_page():
    st.title("🏖️ Gerenciador de Férias")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Login")
        username = st.text_input("Usuário", key="login_username")
        password = st.text_input("Senha", type="password", key="login_password")
        
        if st.button("Entrar", type="primary"):
            if verify_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos")
        
        st.info("💡 Credenciais padrão: admin / admin123")

# Tela Principal
def main_page():
    # Header com logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏖️ Gerenciador de Férias")
    with col2:
        if st.button("🚪 Sair"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
     
    # Tabs principais
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "👥 Funcionários", "📅 Férias", "🏆 Ranking", "⚙️ Configurações"])
    
    # TAB 1: Dashboard
    with tab1:
        st.subheader("Visão Geral")
        
        employees_df = get_employees()
        vacations_df = get_vacations()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Funcionários", len(employees_df))
        
        with col2:
            st.metric("Períodos de Férias", len(vacations_df))
        
        with col3:
            # Férias ativas (em andamento)
            today = date.today()
            if not vacations_df.empty:
                # Converter strings dd/mm/aaaa de volta para objetos date
                vacations_df['start_date_obj'] = pd.to_datetime(vacations_df['start_date'], format='%d/%m/%Y').dt.date
                vacations_df['end_date_obj'] = pd.to_datetime(vacations_df['end_date'], format='%d/%m/%Y').dt.date
                
                active = vacations_df[
                    (vacations_df['start_date_obj'] <= today) & 
                    (vacations_df['end_date_obj'] >= today)
                ]
                st.metric("Férias Ativas", len(active))
            else:
                st.metric("Férias Ativas", 0)
        
        st.markdown("---")
        
        # Próximas férias
        st.subheader("📅 Próximas Férias")
        if not vacations_df.empty:
            # Converter strings dd/mm/aaaa de volta para comparação
            vacations_df['start_date_obj'] = pd.to_datetime(vacations_df['start_date'], format='%d/%m/%Y').dt.date
            vacations_df['end_date_obj'] = pd.to_datetime(vacations_df['end_date'], format='%d/%m/%Y').dt.date
            
            upcoming = vacations_df[vacations_df['start_date_obj'] >= today].head(5)
            if not upcoming.empty:
                for _, row in upcoming.iterrows():
                    days_until = (row['start_date_obj'] - today).days
                    st.info(f"**{row['name']}**: {row['start_date']} até {row['end_date']} ({days_until} dias)")
            else:
                st.info("Nenhuma féria programada")
        else:
            st.info("Nenhuma féria cadastrada")
    
    # TAB 2: Funcionários
    with tab2:
        st.subheader("Gerenciar Funcionários")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("##### Adicionar Funcionário")
            new_name = st.text_input("Nome do Funcionário", key="new_employee")
            
            # Inicializar estado de mensagem se não existir
            if 'show_employee_success' not in st.session_state:
                st.session_state.show_employee_success = False
                st.session_state.employee_success_msg = ""
            
            if st.button("➕ Adicionar", type="primary"):
                if new_name.strip():
                    add_employee(new_name.strip())
                    st.session_state.show_employee_success = True
                    st.session_state.employee_success_msg = f"✅ {new_name} adicionado com sucesso!"
                    st.rerun()
                else:
                    st.error("Digite um nome válido")
            
            # Mostrar mensagem de sucesso
            if st.session_state.show_employee_success:
                st.success(st.session_state.employee_success_msg)
                st.session_state.show_employee_success = False
        
        with col2:
            st.markdown("##### Lista de Funcionários")
            employees_df = get_employees()
            
            if not employees_df.empty:
                for _, emp in employees_df.iterrows():
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        st.write(f"**{emp['name']}**")
                    with col_b:
                        if st.button("🗑️", key=f"del_emp_{emp['id']}"):
                            delete_employee(emp['id'])
                            st.rerun()
            else:
                st.info("Nenhum funcionário cadastrado")
    
    # TAB 3: Férias
    with tab3:
        st.subheader("Gerenciar Férias")
        
        employees_df = get_employees()
        
        if employees_df.empty:
            st.warning("⚠️ Cadastre funcionários primeiro na aba 'Funcionários'")
        else:
            col1, col2 = st.columns([1, 2], border=True)
            
            with col1:
                st.markdown("##### Adicionar Período de Férias")
                
                selected_emp = st.selectbox(
                    "Funcionário",
                    options=employees_df['id'].tolist(),
                    format_func=lambda x: employees_df[employees_df['id'] == x]['name'].values[0]
                )
                
                start_date = st.date_input("Data Inicial", key="vac_start", format="DD/MM/YYYY")
                end_date = st.date_input("Data Final", key="vac_end", format="DD/MM/YYYY")
                
                # Inicializar estado de mensagem se não existir
                if 'show_vacation_success' not in st.session_state:
                    st.session_state.show_vacation_success = False
                
                if st.button("➕ Adicionar Férias", type="primary"):
                    if start_date <= end_date:
                        add_vacation(selected_emp, start_date, end_date)
                        st.session_state.show_vacation_success = True
                        st.rerun()
                    else:
                        st.error("Data inicial deve ser anterior à data final")
                
                # Mostrar mensagem de sucesso
                if st.session_state.show_vacation_success:
                    st.success("✅ Férias adicionadas com sucesso!")
                    st.session_state.show_vacation_success = False
            
            with col2:
                st.markdown("##### Períodos de Férias Cadastrados")
                vacations_df = get_vacations()
                
                if not vacations_df.empty:
                    for _, vac in vacations_df.iterrows():
                        col_a, col_b = st.columns([4, 1], border=True)
                        with col_a:
                            st.write(f"**{vac['name']}**: {vac['start_date']} até {vac['end_date']}")
                        with col_b:
                            if st.button("🗑️", key=f"del_vac_{vac['id']}"):
                                delete_vacation(vac['id'])
                                st.rerun()
                else:
                    st.info("Nenhum período de férias cadastrado")
    
    # TAB 4: Ranking
    with tab4:
        st.subheader("🏆 Ranking de Pontos")
        
        st.info("📋 **Sistema de Pontuação**: Cada dia de férias vale pontos diferentes dependendo do mês. "
                "Meses de alta temporada (Janeiro, Fevereiro, Julho, Dezembro) valem 11 pontos por dia.")
        
        ranking_data = get_employee_ranking()
        
        if ranking_data:
            # Tabela de pontos por mês (referência)
            with st.expander("📅 Ver Tabela de Pontos por Mês"):
                month_points = get_month_points()
                month_names = {
                    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
                }
                
                col1, col2, col3, col4 = st.columns(4)
                for i, (month, points) in enumerate(month_points.items()):
                    with [col1, col2, col3, col4][i % 4]:
                        st.metric(month_names[month], f"{points} pts")
            
            st.markdown("---")
            st.markdown("### 🥇 Classificação")
            
            # Exibir ranking
            for idx, emp_data in enumerate(ranking_data, 1):
                with st.container():
                    col1, col2, col3 = st.columns([1, 3, 2])
                    
                    with col1:
                        # Medalhas para top 3
                        if idx == 1:
                            st.markdown("# 🥇")
                        elif idx == 2:
                            st.markdown("# 🥈")
                        elif idx == 3:
                            st.markdown("# 🥉")
                        else:
                            st.markdown(f"### #{idx}")
                    
                    with col2:
                        st.markdown(f"### {emp_data['name']}")
                        st.write(f"Total de dias de férias: **{emp_data['total_days']}**")
                    
                    with col3:
                        st.markdown(f"### {emp_data['total_points']:,} pontos")
                        
                        # Detalhes por mês (expandível)
                        if emp_data['month_details']:
                            with st.expander("Ver detalhes por mês"):
                                month_names = {
                                    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                                    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                                    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
                                }
                                month_points = get_month_points()
                                
                                for month, days in sorted(emp_data['month_details'].items()):
                                    points_for_month = days * month_points[month]
                                    st.write(f"**{month_names[month]}**: {days} dias × {month_points[month]} pts = {points_for_month} pontos")
                    
                    st.markdown("---")
        else:
            st.info("Nenhum funcionário cadastrado ainda. Adicione funcionários e registre férias para ver o ranking!")
    
    # TAB 5: Configurações
    with tab5:
        st.subheader("Alterar Senha")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            current_password = st.text_input("Senha Atual", type="password", key="current_pass")
            new_password = st.text_input("Nova Senha", type="password", key="new_pass")
            confirm_password = st.text_input("Confirmar Nova Senha", type="password", key="confirm_pass")
            
            if st.button("🔒 Alterar Senha", type="primary"):
                if verify_login(st.session_state.username, current_password):
                    if new_password == confirm_password:
                        if len(new_password) >= 6:
                            change_password(st.session_state.username, new_password)
                            st.success("✅ Senha alterada com sucesso!")
                        else:
                            st.error("A nova senha deve ter pelo menos 6 caracteres")
                    else:
                        st.error("As senhas não coincidem")
                else:
                    st.error("Senha atual incorreta")

# Controle de fluxo
if st.session_state.logged_in:
    main_page()
else:
    login_page()
