import streamlit as st
import pandas as pd
from database import get_employee_ranking, get_month_points


def render():
    """Renderiza a aba de ranking com sistema de pontuação"""
    st.subheader("🏆 Ranking de Pontos")

    st.info("📋 **Sistema de Pontuação**: Cada dia de férias vale pontos diferentes dependendo do mês. "
            "Meses de alta temporada (Janeiro, Fevereiro, Julho, Dezembro) valem 11 pontos por dia.")

    ranking_data = get_employee_ranking()

    if ranking_data:
        # Tabela de pontos por mês (referência)
        with st.expander("📅 Ver Tabela de Pontos por Mês"):
            month_points = get_month_points()
            month_names = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }

            col1, col2, col3, col4 = st.columns(4)
            for i, (month, points) in enumerate(month_points.items()):
                with [col1, col2, col3, col4][i % 4]:
                    st.metric(month_names[month], f"{points} pts")

        st.markdown("---")
        st.markdown("### 🥇 Classificação")

        # Converter ranking para DataFrame
        ranking_list = []
        for idx, emp_data in enumerate(ranking_data, 1):
            position = f"{idx}º"
            ranking_list.append({
                'Posição': position,
                'Funcionário': emp_data['name'],
                'Total de Pontos': emp_data['total_points']
            })

        ranking_df = pd.DataFrame(ranking_list)

        # Exibir tabela
        st.dataframe(
            ranking_df,
            hide_index=True,
            column_config={
                "Posição": st.column_config.TextColumn("Posição", width="small"),
                "Funcionário": st.column_config.TextColumn("Funcionário", width="medium"),
                "Total de Dias": st.column_config.NumberColumn("Total de Dias", width="small"),
                "Total de Pontos": st.column_config.NumberColumn("Total de Pontos", width="medium", format="%d pts")
            }
        )

        # Detalhes por funcionário
        st.markdown("---")
        st.markdown("### 📊 Detalhes por Funcionário")

        for emp_data in ranking_data:
            if emp_data['month_details']:
                with st.expander(f"📅 {emp_data['name']} - Detalhamento Mensal"):
                    month_names = {
                        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
                    }
                    month_points = get_month_points()

                    details_list = []
                    for month, days in sorted(emp_data['month_details'].items()):
                        points_for_month = days * month_points[month]
                        details_list.append({
                            'Mês': month_names[month],
                            'Dias': days,
                            'Pontos/Dia': month_points[month],
                            'Total': points_for_month
                        })

                    details_df = pd.DataFrame(details_list)
                    st.dataframe(
                        details_df,
                        use_container_width=True,
                        hide_index=True
                    )
    else:
        st.info("Nenhum funcionário cadastrado ainda. Adicione funcionários e registre férias para ver o ranking!")
    st.write(ranking_data)