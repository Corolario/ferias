"""
Aplicação Flask para Gerenciamento de Férias
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, datetime
from functools import wraps
import models

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-aqui-mude-em-producao'  # Mude em produção!

# Inicializar banco de dados
models.init_db()


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
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if models.verify_login(username, password):
            session['username'] = username
            flash(f'Bem-vindo, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha incorretos', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Você saiu com sucesso', 'info')
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

        # Próximas férias
        upcoming = vacations_df[vacations_df['start_date_obj'] >= today].head(5)
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
        if name:
            models.add_employee(name)
            flash(f'Funcionário {name} adicionado com sucesso!', 'success')
        else:
            flash('Digite um nome válido', 'danger')
        return redirect(url_for('funcionarios'))

    employees_df = models.get_employees()
    employees = employees_df.to_dict('records') if not employees_df.empty else []

    return render_template('funcionarios.html', employees=employees)


@app.route('/funcionarios/delete/<int:employee_id>', methods=['POST'])
@login_required
def delete_funcionario(employee_id):
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
        end_date = request.form.get('end_date')

        # Converter datas do formato dd/mm/aaaa ou aaaa-mm-dd
        try:
            if '/' in start_date:
                start_obj = datetime.strptime(start_date, '%d/%m/%Y').date()
                end_obj = datetime.strptime(end_date, '%d/%m/%Y').date()
            else:
                start_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

            if start_obj <= end_obj:
                models.add_vacation(employee_id, start_obj, end_obj)
                flash('Férias adicionadas com sucesso!', 'success')
            else:
                flash('Data inicial deve ser anterior à data final', 'danger')
        except ValueError:
            flash('Formato de data inválido', 'danger')

        return redirect(url_for('ferias'))

    employees = employees_df.to_dict('records')
    vacations_df = models.get_vacations()
    vacations = vacations_df.to_dict('records') if not vacations_df.empty else []

    return render_template('ferias.html', employees=employees, vacations=vacations)


@app.route('/ferias/delete/<int:vacation_id>', methods=['POST'])
@login_required
def delete_ferias(vacation_id):
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
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if models.verify_login(session['username'], current_password):
            if new_password == confirm_password:
                if len(new_password) >= 6:
                    models.change_password(session['username'], new_password)
                    flash('Senha alterada com sucesso!', 'success')
                else:
                    flash('A nova senha deve ter pelo menos 6 caracteres', 'danger')
            else:
                flash('As senhas não coincidem', 'danger')
        else:
            flash('Senha atual incorreta', 'danger')

        return redirect(url_for('configuracoes'))

    return render_template('configuracoes.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
