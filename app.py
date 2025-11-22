"""
Aplicação Flask para Gerenciamento de Férias
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_wtf.csrf import CSRFProtect
from flask_bootstrap import Bootstrap5
from datetime import date, datetime, timedelta
from functools import wraps
import os
import secrets
from dotenv import load_dotenv
import models

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configurações de segurança
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Proteção CSRF
csrf = CSRFProtect(app)

# Inicializar Bootstrap
bootstrap = Bootstrap5(app)

# Inicializar banco de dados
models.init_db()


# Headers de segurança
@app.after_request
def set_security_headers(response):
    """Adiciona headers de segurança HTTP"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


# Decorator para rotas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Rotas de autenticação
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se já estiver logado, redireciona
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Validações básicas
        if not username or not password:
            flash('Usuário e senha são obrigatórios', 'danger')
            return render_template('login.html')

        if models.verify_login(username, password):
            session.clear()
            session['username'] = username
            session.permanent = True
            flash(f'Bem-vindo, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha incorretos', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    username = session.get('username', 'Usuário')
    session.clear()
    flash(f'Até logo, {username}!', 'info')
    return redirect(url_for('login'))


# Rota do Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    try:
        employees_df = models.get_employees()
        vacations_df = models.get_vacations()

        total_employees = len(employees_df)
        total_vacations = len(vacations_df)

        # Férias ativas (em andamento)
        today = date.today()
        active_vacations = 0
        vacations_by_year_month = {}

        if not vacations_df.empty:
            # Converter strings dd/mm/aaaa para objetos datetime do pandas primeiro
            import pandas as pd
            vacations_df['start_date_dt'] = pd.to_datetime(vacations_df['start_date'], format='%d/%m/%Y')
            vacations_df['end_date_dt'] = pd.to_datetime(vacations_df['end_date'], format='%d/%m/%Y')

            # Calcular número de dias para cada período (ANTES de converter para date)
            vacations_df['num_days'] = (vacations_df['end_date_dt'] - vacations_df['start_date_dt']).dt.days + 1

            # Agora converter para objetos date do Python
            vacations_df['start_date_obj'] = vacations_df['start_date_dt'].dt.date
            vacations_df['end_date_obj'] = vacations_df['end_date_dt'].dt.date

            # Contar férias ativas
            active = vacations_df[
                (vacations_df['start_date_obj'] <= today) &
                (vacations_df['end_date_obj'] >= today)
            ]
            active_vacations = len(active)

            # Extrair ano e mês da data de início
            vacations_df['year'] = vacations_df['start_date_obj'].apply(lambda x: x.year)
            vacations_df['month'] = vacations_df['start_date_obj'].apply(lambda x: x.month)

            # Formatar datas no formato brasileiro curto (dd/mm/aa)
            vacations_df['start_date_short'] = vacations_df['start_date_obj'].apply(lambda x: x.strftime('%d/%m/%y'))
            vacations_df['end_date_short'] = vacations_df['end_date_obj'].apply(lambda x: x.strftime('%d/%m/%y'))

            # Ordenar por ano, mês e data de início
            vacations_df = vacations_df.sort_values(by=['year', 'month', 'start_date_obj'])

            # Nomes dos meses em português
            month_names = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }

            # Agrupar férias por ano e mês
            for _, row in vacations_df.iterrows():
                year = int(row['year'])  # Converter para int nativo do Python
                month = int(row['month'])  # Converter para int nativo do Python
                month_name = month_names[month]

                if year not in vacations_by_year_month:
                    vacations_by_year_month[year] = {}

                if month_name not in vacations_by_year_month[year]:
                    vacations_by_year_month[year][month_name] = []

                vacations_by_year_month[year][month_name].append({
                    'name': str(row['name']),
                    'start_date': str(row['start_date_short']),
                    'end_date': str(row['end_date_short']),
                    'num_days': int(row['num_days'])  # Converter para int nativo do Python
                })

        return render_template('dashboard.html',
                             total_employees=total_employees,
                             total_vacations=total_vacations,
                             active_vacations=active_vacations,
                             vacations_by_year_month=vacations_by_year_month)
    except Exception as e:
        # Logar o erro e exibir mensagem amigável
        import traceback
        print(f"Erro no dashboard: {e}")
        traceback.print_exc()
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html',
                             total_employees=0,
                             total_vacations=0,
                             active_vacations=0,
                             vacations_by_year_month={})


# Rotas de Funcionários
@app.route('/funcionarios', methods=['GET', 'POST'])
@login_required
def funcionarios():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()

        # Validações
        if not name:
            flash('Digite um nome válido', 'danger')
        elif len(name) < 2:
            flash('O nome deve ter pelo menos 2 caracteres', 'danger')
        elif len(name) > 100:
            flash('O nome não pode ter mais de 100 caracteres', 'danger')
        elif models.add_employee(name):
            flash(f'Funcionário {name} adicionado com sucesso!', 'success')
        else:
            flash('Erro ao adicionar funcionário', 'danger')

        return redirect(url_for('funcionarios'))

    employees_df = models.get_employees()
    employees = employees_df.to_dict('records') if not employees_df.empty else []

    return render_template('funcionarios.html', employees=employees)


@app.route('/funcionarios/delete/<int:employee_id>', methods=['POST'])
@login_required
def delete_funcionario(employee_id):
    if employee_id <= 0:
        flash('ID inválido', 'danger')
    else:
        models.delete_employee(employee_id)
        flash('Funcionário removido com sucesso!', 'success')
    return redirect(url_for('funcionarios'))


# Rotas de Férias
@app.route('/ferias', methods=['GET', 'POST'])
@login_required
def ferias():
    employees_df = models.get_employees()

    if employees_df.empty:
        flash('Cadastre funcionários primeiro na aba Funcionários', 'warning')
        return render_template('ferias.html', employees=[], vacations=[])

    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        start_date = request.form.get('start_date')
        days = request.form.get('days')

        # Validações
        if not employee_id or not start_date or not days:
            flash('Todos os campos são obrigatórios', 'danger')
            return redirect(url_for('ferias'))

        # Converter data e calcular data final
        try:
            start_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            days_int = int(days)

            # Validações
            if days_int < 1:
                flash('Quantidade de dias deve ser pelo menos 1', 'danger')
            elif days_int > 365:
                flash('Período de férias não pode ser maior que 365 dias', 'danger')
            else:
                # Calcular data final (se são 5 dias, vai do dia 1 ao dia 5)
                end_obj = start_obj + timedelta(days=days_int - 1)

                if models.add_vacation(employee_id, start_obj, end_obj):
                    flash('Férias adicionadas com sucesso!', 'success')
                else:
                    flash('Erro ao adicionar férias', 'danger')
        except ValueError:
            flash('Formato de data ou quantidade de dias inválido', 'danger')

        return redirect(url_for('ferias'))

    employees = employees_df.to_dict('records')
    vacations_df = models.get_vacations()

    # Calcular número de dias para cada período de férias
    if not vacations_df.empty:
        import pandas as pd
        vacations_df['start_date_obj'] = pd.to_datetime(vacations_df['start_date'], format='%d/%m/%Y')
        vacations_df['end_date_obj'] = pd.to_datetime(vacations_df['end_date'], format='%d/%m/%Y')
        vacations_df['num_days'] = (vacations_df['end_date_obj'] - vacations_df['start_date_obj']).dt.days + 1

        # Ordenar por nome alfabético
        vacations_df = vacations_df.sort_values(by='name')

        vacations = vacations_df.to_dict('records')
    else:
        vacations = []

    return render_template('ferias.html', employees=employees, vacations=vacations)


@app.route('/ferias/delete/<int:vacation_id>', methods=['POST'])
@login_required
def delete_ferias(vacation_id):
    if vacation_id <= 0:
        flash('ID inválido', 'danger')
    else:
        models.delete_vacation(vacation_id)
        flash('Período de férias removido com sucesso!', 'success')
    return redirect(url_for('ferias'))


# Rota de Ranking
@app.route('/ranking')
@login_required
def ranking():
    ranking_data = models.get_employee_ranking()
    month_points = models.get_month_points()

    month_names = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    # Adicionar detalhes formatados aos dados do ranking
    import sqlite3
    import pandas as pd

    # Buscar todas as férias
    conn = sqlite3.connect('vacation_manager.db')
    all_vacations_query = '''
        SELECT v.employee_id, e.name as employee_name, v.start_date, v.end_date
        FROM vacations v
        JOIN employees e ON v.employee_id = e.id
        ORDER BY v.start_date ASC
    '''
    all_vacations_df = pd.read_sql_query(all_vacations_query, conn)
    conn.close()

    for emp in ranking_data:
        emp['month_breakdown'] = []
        emp['periods_breakdown'] = []

        if emp['month_details']:
            # Agregado por mês (para compatibilidade)
            for month, days in sorted(emp['month_details'].items()):
                points_for_month = days * month_points[month]
                emp['month_breakdown'].append({
                    'month_name': month_names[month],
                    'days': days,
                    'points_per_day': month_points[month],
                    'total_points': points_for_month
                })

        # Buscar períodos individuais deste funcionário
        emp_vacations = all_vacations_df[all_vacations_df['employee_name'] == emp['name']]

        if not emp_vacations.empty:
            for idx, (_, vacation) in enumerate(emp_vacations.iterrows(), 1):
                start_date = datetime.strptime(vacation['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(vacation['end_date'], '%Y-%m-%d').date()

                # Calcular pontos e breakdown por mês deste período
                period_points, days_by_month = models.calculate_vacation_points(start_date, end_date)
                period_days = (end_date - start_date).days + 1

                # Formatar datas no formato brasileiro
                start_date_br = start_date.strftime('%d/%m/%y')
                end_date_br = end_date.strftime('%d/%m/%y')

                # Breakdown por mês do período
                month_details = []
                for month, days in sorted(days_by_month.items()):
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

                    month_details.append({
                        'month_name': month_names[month],
                        'day_range': f"{first_day_in_month:02d} - {last_day_in_month:02d}",
                        'days': days,
                        'points_per_day': points_per_day,
                        'total_points': month_total_points
                    })

                emp['periods_breakdown'].append({
                    'period_number': idx,
                    'start_date': start_date_br,
                    'end_date': end_date_br,
                    'total_days': period_days,
                    'total_points': period_points,
                    'month_details': month_details
                })

    # Criar lista de pontos por mês para exibição
    month_points_list = [
        {'name': month_names[m], 'points': p}
        for m, p in month_points.items()
    ]

    return render_template('ranking.html',
                         ranking_data=ranking_data,
                         month_points_list=month_points_list)


@app.route('/ranking/pdf')
@login_required
def ranking_pdf():
    """Gera e baixa PDF do ranking"""
    try:
        pdf_buffer = models.generate_ranking_pdf()
        filename = f'ranking_ferias_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('ranking'))


# Rota de Configurações
@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validações
        if not current_password or not new_password or not confirm_password:
            flash('Todos os campos são obrigatórios', 'danger')
        elif new_password != confirm_password:
            flash('As senhas não coincidem', 'danger')
        elif len(new_password) < 6:
            flash('A nova senha deve ter pelo menos 6 caracteres', 'danger')
        elif len(new_password) > 100:
            flash('A nova senha não pode ter mais de 100 caracteres', 'danger')
        elif not models.verify_login(session['username'], current_password):
            flash('Senha atual incorreta', 'danger')
        elif models.change_password(session['username'], new_password):
            flash('Senha alterada com sucesso!', 'success')
        else:
            flash('Erro ao alterar senha', 'danger')

        return redirect(url_for('configuracoes'))

    return render_template('configuracoes.html')


# Handler de erros
@app.errorhandler(404)
def page_not_found(e):
    flash('Página não encontrada', 'warning')
    return redirect(url_for('index'))


@app.errorhandler(500)
def internal_server_error(e):
    flash('Erro interno do servidor', 'danger')
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Configurações de desenvolvimento
    debug_mode = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    port = int(os.environ.get('PORT', 5000))

    app.run(debug=debug_mode, host='0.0.0.0', port=port)
