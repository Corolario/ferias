import streamlit as st
from database import add_employee, get_employees, delete_employee, update_employee

def render():
    """Renderiza a aba de gerenciamento de funcionários"""
    st.subheader("Gerenciar Funcionários")

    employees_df = get_employees()

    if not employees_df.empty:
        # Criar DataFrame com ID como coluna oculta
        display_df = employees_df[['id', 'name']].copy()

        edited_df = st.data_editor(
            display_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,  # Oculta completamente a coluna ID
                "name": st.column_config.TextColumn("Nome", width="large", required=True)
            }
        )

        # Detectar linhas excluídas
        deleted_ids = set(employees_df['id']) - set(edited_df['id'])
        if deleted_ids:
            for emp_id in deleted_ids:
                delete_employee(emp_id)
            st.success(f"✅ {len(deleted_ids)} funcionário(s) excluído(s)")
            st.rerun()

        # Detectar novas linhas adicionadas (linhas sem ID ou com ID inválido)
        for idx, row in edited_df.iterrows():
            if idx >= len(employees_df) or (row['id'] not in employees_df['id'].values):
                new_name = row['name']
                if new_name and str(new_name).strip():
                    add_employee(str(new_name).strip())
                    st.success(f"✅ Funcionário adicionado: {new_name}")
                    st.rerun()

        # Detectar edições nos nomes
        for idx, row in edited_df.iterrows():
            if row['id'] in employees_df['id'].values:
                original_name = employees_df[employees_df['id'] == row['id']]['name'].values[0]
                edited_name = row['name']

                if str(edited_name).strip() and str(edited_name) != str(original_name):
                    update_employee(row['id'], str(edited_name).strip())
                    st.success(f"✅ Nome atualizado: {original_name} → {edited_name}")
                    st.rerun()
    else:
        st.info("Nenhum funcionário cadastrado. Clique no + abaixo para adicionar.")

        # Criar DataFrame vazio para permitir adicionar o primeiro funcionário
        empty_df = st.data_editor(
            {"name": []},
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("Nome", width="large", required=True)
            }
        )

        # Verificar se foi adicionado algum funcionário
        if not empty_df.empty and len(empty_df) > 0:
            for _, row in empty_df.iterrows():
                if row['name'] and str(row['name']).strip():
                    add_employee(str(row['name']).strip())
            st.success(f"✅ {len(empty_df)} funcionário(s) adicionado(s)")
            st.rerun()
