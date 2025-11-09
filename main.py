import streamlit as st
from pags import dashboard, funcionarios, ferias, ranking
from database import init_db, verify_login, change_password

# Inicializar banco de dados
init_db()

# Configuração da página
st.set_page_config(
    page_title="Gestão de Férias",
    page_icon="🏖️",
    layout="wide",
    menu_items={
        'About': '### Sistema de Gestão de Férias v1.0.'
    }
)

# Tela de Login
def login_page():
    st.title("🏖️ Gerenciador de Férias")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 1])

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

    # Criar as tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard",
        "👥 Funcionários",
        "📅 Férias",
        "🏆 Ranking",
        "⚙️ Configurações"
    ])

    # Renderizar cada tab com seu respectivo módulo
    with tab1:
        dashboard.render()

    with tab2:
        funcionarios.render()

    with tab3:
        ferias.render()

    with tab4:
        ranking.render()

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


# Inicializar estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Controle de fluxo
if st.session_state.logged_in:
    main_page()
else:
    login_page()
