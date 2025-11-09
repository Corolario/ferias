"""
Módulo de modelos e funções de banco de dados para o gerenciador de férias
"""
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd


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

        # Avançar um dia
        from datetime import timedelta
        current_date = current_date + timedelta(days=1)

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
