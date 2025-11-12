"""
Módulo de modelos e funções de banco de dados para o gerenciador de férias
"""
import sqlite3
import bcrypt
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()

    # Habilitar foreign keys
    c.execute('PRAGMA foreign_keys = ON')

    # Tabela de usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    c.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if c.fetchone()[0] == 0:
        password_hash = hash_password('admin123')
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                  ('admin', password_hash))

    conn.commit()
    conn.close()


def hash_password(password):
    """Gera hash bcrypt da senha"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    """Verifica se a senha corresponde ao hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def verify_login(username, password):
    """Verifica credenciais de login"""
    if not username or not password:
        return False

    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()

    c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()

    if result is None:
        return False

    return verify_password(password, result[0])


def change_password(username, new_password):
    """Altera a senha do usuário"""
    if not username or not new_password or len(new_password) < 6:
        return False

    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    password_hash = hash_password(new_password)

    c.execute('UPDATE users SET password_hash = ? WHERE username = ?',
              (password_hash, username))
    conn.commit()
    rows_affected = c.rowcount
    conn.close()

    return rows_affected > 0


# Funções de gerenciamento de funcionários
def add_employee(name):
    """Adiciona um novo funcionário"""
    if not name or not name.strip():
        return False

    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    c.execute('INSERT INTO employees (name) VALUES (?)', (name.strip(),))
    conn.commit()
    conn.close()
    return True


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
    c.execute('PRAGMA foreign_keys = ON')
    c.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
    conn.commit()
    conn.close()


# Funções de gerenciamento de férias
def add_vacation(employee_id, start_date, end_date):
    """Adiciona período de férias"""
    # Validações
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    if start_date > end_date:
        return False

    conn = sqlite3.connect('vacation_manager.db')
    c = conn.cursor()
    c.execute('INSERT INTO vacations (employee_id, start_date, end_date) VALUES (?, ?, ?)',
              (employee_id, start_date, end_date))
    conn.commit()
    conn.close()
    return True


def get_vacations():
    """Retorna todas as férias com nome do funcionário"""
    conn = sqlite3.connect('vacation_manager.db')
    query = '''
        SELECT v.id, e.name, v.start_date, v.end_date, e.id as employee_id
        FROM vacations v
        JOIN employees e ON v.employee_id = e.id
        ORDER BY v.start_date ASC, e.name ASC
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


def generate_ranking_pdf():
    """Gera PDF do ranking de funcionários"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    elements = []

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )

    # Título do documento
    title = Paragraph("Relatório de Ranking de Férias", title_style)
    elements.append(title)

    # Data do relatório
    date_text = f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    date_para = Paragraph(date_text, styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 0.5*cm))

    # Obter dados do ranking
    ranking_data = get_employee_ranking()
    month_points = get_month_points()
    month_names = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    # ========== SEÇÃO 1: CLASSIFICAÇÃO ==========
    classification_heading = Paragraph("Classificação", heading_style)
    elements.append(classification_heading)

    # Tabela de classificação (apenas posição e nome)
    classification_data = [['Posição', 'Nome']]
    for idx, emp in enumerate(ranking_data, 1):
        classification_data.append([str(idx), emp['name']])

    classification_table = Table(classification_data, colWidths=[3*cm, 14*cm])
    classification_table.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),

        # Corpo
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))

    elements.append(classification_table)
    elements.append(PageBreak())

    # ========== SEÇÃO 2: DETALHES POR FUNCIONÁRIO ==========
    details_heading = Paragraph("Detalhes por Funcionário", heading_style)
    elements.append(details_heading)
    elements.append(Spacer(1, 0.3*cm))

    for idx, emp in enumerate(ranking_data, 1):
        # Nome do funcionário
        emp_name_style = ParagraphStyle(
            'EmpName',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold',
            spaceAfter=8
        )
        emp_heading = Paragraph(f"{idx}. {emp['name']}", emp_name_style)
        elements.append(emp_heading)

        # Verificar se tem férias
        if emp['month_details']:
            # Tabela de detalhes por mês
            detail_data = [['Mês', 'Dias', 'Pontos/Dia', 'Total']]

            for month, days in sorted(emp['month_details'].items()):
                points_per_day = month_points[month]
                total_points = days * points_per_day
                detail_data.append([
                    month_names[month],
                    str(days),
                    str(points_per_day),
                    str(total_points)
                ])

            # Linha de total
            detail_data.append([
                'TOTAL',
                str(emp['total_days']),
                '',
                f"{emp['total_points']} pontos"
            ])

            detail_table = Table(detail_data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm])
            detail_table.setStyle(TableStyle([
                # Cabeçalho
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#95a5a6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Corpo
                ('ALIGN', (0, 1), (0, -2), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -2), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#ecf0f1')]),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('TOPPADDING', (0, 1), (-1, -2), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -2), 6),

                # Linha de total
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, -1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
            ]))

            elements.append(detail_table)
        else:
            # Funcionário sem férias
            no_vacation_text = Paragraph("Sem períodos de férias cadastrados", styles['Italic'])
            elements.append(no_vacation_text)

        # Espaçamento entre funcionários
        elements.append(Spacer(1, 0.5*cm))

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
