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
    conn = sqlite3.connect('/data/vacation_manager.db')
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

    # Criar usuário admin padrão se não existir (INSERT OR IGNORE evita race condition)
    password_hash = hash_password('admin123')
    c.execute('INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)',
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

    conn = sqlite3.connect('/data/vacation_manager.db')
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

    conn = sqlite3.connect('/data/vacation_manager.db')
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

    conn = sqlite3.connect('/data/vacation_manager.db')
    c = conn.cursor()
    c.execute('INSERT INTO employees (name) VALUES (?)', (name.strip(),))
    conn.commit()
    conn.close()
    return True


def get_employees():
    """Retorna lista de funcionários"""
    conn = sqlite3.connect('/data/vacation_manager.db')
    df = pd.read_sql_query('SELECT * FROM employees ORDER BY name', conn)
    conn.close()
    return df


def delete_employee(employee_id):
    """Remove um funcionário e suas férias"""
    conn = sqlite3.connect('/data/vacation_manager.db')
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

    conn = sqlite3.connect('/data/vacation_manager.db')
    c = conn.cursor()
    c.execute('INSERT INTO vacations (employee_id, start_date, end_date) VALUES (?, ?, ?)',
              (employee_id, start_date, end_date))
    conn.commit()
    conn.close()
    return True


def get_vacations():
    """Retorna todas as férias com nome do funcionário"""
    conn = sqlite3.connect('/data/vacation_manager.db')
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
    conn = sqlite3.connect('/data/vacation_manager.db')
    c = conn.cursor()
    c.execute('DELETE FROM vacations WHERE id = ?', (vacation_id,))
    conn.commit()
    conn.close()


def update_vacation(vacation_id, employee_id, start_date, end_date):
    """Atualiza um período de férias"""
    # Validações
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    if start_date > end_date:
        return False

    conn = sqlite3.connect('/data/vacation_manager.db')
    c = conn.cursor()
    c.execute('''UPDATE vacations
                 SET employee_id = ?, start_date = ?, end_date = ?
                 WHERE id = ?''',
              (employee_id, start_date, end_date, vacation_id))
    conn.commit()
    rows_affected = c.rowcount
    conn.close()
    return rows_affected > 0


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
    conn = sqlite3.connect('/data/vacation_manager.db')

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


def get_vacations_by_year_month():
    """
    Organiza todas as férias por ano e mês de INÍCIO
    Retorna um dicionário estruturado: {ano: {mês: [lista de férias]}}
    Cada período é mostrado completo, sem divisão por mês
    """
    conn = sqlite3.connect('/data/vacation_manager.db')

    # Buscar todas as férias com nome do funcionário
    query = '''
        SELECT e.name, v.start_date, v.end_date
        FROM vacations v
        JOIN employees e ON v.employee_id = e.id
        ORDER BY v.start_date ASC
    '''

    vacations_df = pd.read_sql_query(query, conn)
    conn.close()

    # Estrutura para organizar: {ano: {mês: [lista de férias]}}
    vacations_by_year_month = {}

    for _, row in vacations_df.iterrows():
        name = row['name']
        start_date = datetime.strptime(row['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(row['end_date'], '%Y-%m-%d').date()

        # Calcular número de dias do período completo
        num_days = (end_date - start_date).days + 1

        # Pegar ano e mês de INÍCIO
        year = start_date.year
        month = start_date.month

        # Criar estrutura se não existir
        if year not in vacations_by_year_month:
            vacations_by_year_month[year] = {}

        if month not in vacations_by_year_month[year]:
            vacations_by_year_month[year][month] = []

        # Adicionar período completo
        vacations_by_year_month[year][month].append({
            'name': name,
            'start_date': start_date,
            'end_date': end_date,
            'days': num_days
        })

    return vacations_by_year_month


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

    # Tabela de classificação (posição, nome e pontos)
    classification_data = [['Classificação', 'Nome', 'Pontos']]
    for idx, emp in enumerate(ranking_data, 1):
        classification_data.append([str(idx), emp['name'], str(emp['total_points'])])

    classification_table = Table(classification_data, colWidths=[3*cm, 11*cm, 3*cm])
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
    
    # ========== SEÇÃO 2: TABELA DE FÉRIAS ==========
    vacation_table_heading = Paragraph("Tabela de Férias", heading_style)
    elements.append(vacation_table_heading)
    elements.append(Spacer(1, 0.3*cm))

    # Obter férias organizadas por ano/mês
    vacations_by_year_month = get_vacations_by_year_month()

    # Se houver férias cadastradas
    if vacations_by_year_month:
        # Iterar por cada ano (ordenado)
        for year in sorted(vacations_by_year_month.keys()):
            # Criar tabela para este ano
            year_vacation_data = []

            # Primeira linha (cabeçalho): Ano, Nome, Início, Fim, Dias
            year_vacation_data.append([str(year), 'Nome', 'Início', 'Fim', 'Dias'])

            # Variável para controlar mês anterior
            previous_month = None

            # Iterar por cada mês (ordenado)
            for month in sorted(vacations_by_year_month[year].keys()):
                month_name = month_names[month]

                # Adicionar cada período de férias deste mês
                for idx, vacation in enumerate(vacations_by_year_month[year][month]):
                    name = vacation['name']
                    start_date_str = vacation['start_date'].strftime('%d/%m/%y')
                    end_date_str = vacation['end_date'].strftime('%d/%m/%y')
                    days = str(vacation['days'])

                    # Se é o primeiro período do mês, mostra o nome do mês
                    # Senão, deixa em branco
                    if idx == 0:
                        if month == previous_month:
                            month_display = ''
                        else:
                            month_display = month_name
                            previous_month = month
                    else:
                        month_display = ''

                    year_vacation_data.append([month_display, name, start_date_str, end_date_str, days])

            # Criar tabela do ano
            year_table = Table(year_vacation_data, colWidths=[3*cm, 6*cm, 3*cm, 3*cm, 2*cm])

            # Estilos da tabela
            table_style = [
                # Cabeçalho (primeira linha)
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Corpo - todas as linhas
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]

            year_table.setStyle(TableStyle(table_style))
            elements.append(year_table)
            elements.append(Spacer(1, 0.5*cm))

    else:
        no_vacations_text = Paragraph("Nenhum período de férias cadastrado.", styles['Italic'])
        elements.append(no_vacations_text)

    elements.append(PageBreak())

    # ========== SEÇÃO 3: DETALHES POR FUNCIONÁRIO ==========
    details_heading = Paragraph("Detalhes por Funcionário", heading_style)
    elements.append(details_heading)
    elements.append(Spacer(1, 0.3*cm))

    # Buscar férias de cada funcionário
    conn = sqlite3.connect('/data/vacation_manager.db')
    vacations_query = '''
        SELECT employee_id, start_date, end_date
        FROM vacations
        ORDER BY start_date ASC
    '''
    all_vacations_df = pd.read_sql_query(vacations_query, conn)
    conn.close()

    for idx, emp in enumerate(ranking_data, 1):
        # Buscar o employee_id do funcionário
        conn = sqlite3.connect('/data/vacation_manager.db')
        emp_id_query = 'SELECT id FROM employees WHERE name = ?'
        emp_id_result = pd.read_sql_query(emp_id_query, conn, params=(emp['name'],))
        conn.close()

        if emp_id_result.empty:
            continue

        employee_id = emp_id_result.iloc[0]['id']

        # Filtrar férias deste funcionário
        emp_vacations = all_vacations_df[all_vacations_df['employee_id'] == employee_id]

        # Verificar se tem férias
        if not emp_vacations.empty:
            # Criar tabela completa para este funcionário
            table_data = []

            # Cabeçalho da tabela
            table_data.append([
                f"{idx}. {emp['name']}",
                'Dias',
                'Pts/mês',
                'Total'
            ])

            grand_total_days = 0
            grand_total_points = 0

            # Para cada período de férias
            for period_idx, (_, vacation) in enumerate(emp_vacations.iterrows(), 1):
                start_date = datetime.strptime(vacation['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(vacation['end_date'], '%Y-%m-%d').date()

                # Calcular pontos e breakdown por mês deste período
                period_points, days_by_month = calculate_vacation_points(start_date, end_date)
                period_days = (end_date - start_date).days + 1

                # Formatar datas no formato brasileiro
                start_date_br = start_date.strftime('%d/%m/%y')
                end_date_br = end_date.strftime('%d/%m/%y')

                # Linha do período
                table_data.append([
                    f"Período {period_idx} ({start_date_br} - {end_date_br})",
                    str(period_days),
                    '',
                    str(period_points)
                ])

                # Breakdown por mês
                for month, days in sorted(days_by_month.items()):
                    # Calcular datas do mês
                    month_start = start_date
                    month_end = end_date

                    # Encontrar primeiro e último dia do período neste mês
                    current = start_date
                    first_day_in_month = None
                    last_day_in_month = None

                    while current <= end_date:
                        if current.month == month:
                            if first_day_in_month is None:
                                first_day_in_month = current.day
                            last_day_in_month = current.day
                        current = current + timedelta(days=1)

                    points_per_day = month_points[month]
                    month_total_points = days * points_per_day

                    table_data.append([
                        f"{month_names[month]} ({first_day_in_month:02d} - {last_day_in_month:02d})",
                        str(days),
                        str(points_per_day),
                        str(month_total_points)
                    ])

                grand_total_days += period_days
                grand_total_points += period_points

            # Linha de total geral
            table_data.append([
                'Total',
                str(grand_total_days),
                '',
                str(grand_total_points)
            ])

            # Criar tabela
            detail_table = Table(table_data, colWidths=[10*cm, 2*cm, 2*cm, 2*cm])

            # Estilos da tabela
            table_style = [
                # Cabeçalho (primeira linha)
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Corpo - todas as outras linhas exceto a última
                ('ALIGN', (0, 1), (0, -2), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -2), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

                # Linha de total (última linha)
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, -1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
            ]

            # Identificar linhas de período (começam com "Período")
            # e aplicar background cinza claro
            for row_idx, row in enumerate(table_data[1:-1], 1):  # Pula cabeçalho e total
                if row[0].startswith('Período'):
                    table_style.append(
                        ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#ecf0f1'))
                    )
                    table_style.append(
                        ('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold')
                    )

            detail_table.setStyle(TableStyle(table_style))
            elements.append(detail_table)
        else:
            # Funcionário sem férias
            no_vacation_text = Paragraph(f"{idx}. {emp['name']} - Sem períodos de férias cadastrados", styles['Italic'])
            elements.append(no_vacation_text)

        # Espaçamento entre funcionários
        elements.append(Spacer(1, 0.5*cm))

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
