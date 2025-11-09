import streamlit as st
from database import get_employees, add_vacation, get_vacations, delete_vacation


def render():
    """Renderiza a aba de gerenciamento de férias"""
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
                # Criar DataFrame com ID oculto e colunas visíveis
                display_df = vacations_df[['id', 'name', 'start_date', 'end_date']].copy()

                edited_df = st.data_editor(
                    display_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "id": None,  # Oculta a coluna ID
                        "name": st.column_config.TextColumn("Funcionário", width="medium", disabled=True),
                        "start_date": st.column_config.TextColumn("Data Inicial", width="medium", disabled=True),
                        "end_date": st.column_config.TextColumn("Data Final", width="medium", disabled=True)
                    }
                )

                # Detectar linhas excluídas
                deleted_ids = set(vacations_df['id']) - set(edited_df['id'])
                if deleted_ids:
                    for vac_id in deleted_ids:
                        delete_vacation(vac_id)
                    st.success(f"✅ {len(deleted_ids)} período(s) de férias excluído(s)")
                    st.rerun()
            else:
                st.info("Nenhum período de férias cadastrado")
