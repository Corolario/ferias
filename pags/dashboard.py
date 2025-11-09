import streamlit as st
import pandas as pd
from datetime import date
from database import get_employees, get_vacations


def render():
    """Renderiza a aba Dashboard com métricas e visão geral"""
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
