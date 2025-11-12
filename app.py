"""
Aplicação Flask para Gerenciamento de Férias
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash
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
    employees_df = models.get_employees()
    vacations_df = models.get_vacations()

    total_employees = len(employees_df)
    total_vacations = len(vacations_df)

    # Férias ativas (em andamento)
    today = date.today()
    active_vacations = 0
    upcoming_vacations = []

    if not vacations_df.empty:
        # Converter strings dd/mm/aaaa para objetos date
        import pandas as pd
        vacations_df['start_date_obj'] = pd.to_datetime(vacations_df['start_date'], format='%d/%m/%Y').dt.date
        vacations_df['end_date_obj'] = pd.to_datetime(vacations_df['end_date'], format='%d/%m/%Y').dt.date

        # Contar férias ativas
        active = vacations_df[
            (vacations_df['start_date_obj'] <= today) &
            (vacations_df['end_date_obj'] >= today)
        ]
        active_vacations = len(active)

        # Próximas férias - ordenar por data crescente e nome alfabético
        upcoming = vacations_df[vacations_df['start_date_obj'] >= today].sort_values(by=['start_date_obj', 'name']).head(5)
        for _, row in upcoming.iterrows():
            days_until = (row['start_date_obj'] - today).days
            upcoming_vacations.append({
                'name': row['name'],
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'days_until': days_until
            })

    return render_template('dashboard.html',
                         total_employees=total_employees,
                         total_vacations=total_vacations,
                         active_vacations=active_vacations,
                         upcoming_vacations=upcoming_vacations)


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
    for emp in ranking_data:
        emp['month_breakdown'] = []
        if emp['month_details']:
            for month, days in sorted(emp['month_details'].items()):
                points_for_month = days * month_points[month]
                emp['month_breakdown'].append({
                    'month_name': month_names[month],
                    'days': days,
                    'points_per_day': month_points[month],
                    'total_points': points_for_month
                })

    # Criar lista de pontos por mês para exibição
    month_points_list = [
        {'name': month_names[m], 'points': p}
        for m, p in month_points.items()
    ]

    return render_template('ranking.html',
                         ranking_data=ranking_data,
                         month_points_list=month_points_list)


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
