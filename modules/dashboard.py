# modules/dashboard.py
import streamlit as st # type: ignore
import pandas as pd # type: ignore
import plotly.express as px # type: ignore
import plotly.graph_objects as go # type: ignore
from .config import (
    DASHBOARD_ICON,
    FORM_ICON,
    EXPECTED_UPLOAD_COLUMNS,
    TRANSACTION_TEMPLATE_PATH,
    UPLOAD_DATE_FORMAT,
    UPLOAD_DATETIME_FORMAT
)
from . import db_utils # Relative import
from .form import format_currency_br # Import from form.py or move to a common utils
from io import StringIO # For file download/upload

# --- Função da Página de Dashboard ---
def dashboard_page(username):
    st.title(f"{DASHBOARD_ICON} Planilha Financeira de {username}")
    
    df_transacoes = db_utils.get_transactions_for_user(username)

    if not df_transacoes.empty:
        df_transacoes['valor'] = pd.to_numeric(df_transacoes['valor'], errors='coerce')
        df_transacoes.dropna(subset=['valor'], inplace=True)

        if 'data_hora_dt' not in df_transacoes.columns and 'data_hora' in df_transacoes.columns:
             df_transacoes['data_hora_dt'] = pd.to_datetime(df_transacoes['data_hora'])

        if 'data_hora_dt' in df_transacoes.columns:
            df_transacoes = df_transacoes.sort_values(by=['data_hora_dt', 'id'], ascending=[False, False])
            df_transacoes['data_hora_display'] = df_transacoes['data_hora_dt'].dt.strftime('%d/%m/%Y %H:%M:%S')
        else:
            df_transacoes['data_hora_display'] = pd.Series(dtype='str')


        df_display = df_transacoes[['id', 'tipo', 'valor', 'tipo_cartao', 'banco', 'descricao', 'data_hora_display']].copy()
        df_display.rename(columns={'data_hora_display': 'Data/Hora'}, inplace=True)
        df_display['tipo'] = df_display['tipo'].str.upper()
        
        df_display['valor_formatado'] = df_display['valor'].apply(format_currency_br)
        
        st.subheader("Visão Geral das Suas Transações")
        st.dataframe(df_display[['id', 'tipo', 'valor_formatado', 'tipo_cartao', 'banco', 'descricao', 'Data/Hora']], use_container_width=True, hide_index=True)
        
        if 'data_hora_dt' in df_transacoes.columns:
            csv_data = df_transacoes[EXPECTED_UPLOAD_COLUMNS[:-1] + ['data_hora_dt']].copy()
            csv_data['data_hora'] = csv_data['data_hora_dt'].dt.strftime(UPLOAD_DATETIME_FORMAT) 
            csv_data_final = csv_data[EXPECTED_UPLOAD_COLUMNS] 
        else: 
            st.warning("Não foi possível preparar todas as colunas para o download devido à falta de 'data_hora_dt'. O arquivo pode estar incompleto.")
            available_cols_for_export = [col for col in EXPECTED_UPLOAD_COLUMNS if col in df_transacoes.columns]
            if 'data_hora' not in df_transacoes.columns and 'data_hora' in EXPECTED_UPLOAD_COLUMNS: 
                 csv_data_final = pd.DataFrame(columns=EXPECTED_UPLOAD_COLUMNS) 
            else:
                csv_data_final = df_transacoes[available_cols_for_export].copy()
                for col in EXPECTED_UPLOAD_COLUMNS: 
                    if col not in csv_data_final.columns:
                        csv_data_final[col] = pd.NA


        csv_buffer = StringIO()
        csv_data_final.to_csv(csv_buffer, index=False, sep=',', encoding='utf-8')
        st.download_button(
            label="📥 Baixar Transações (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"transacoes_{username}.csv",
            mime="text/csv",
        )
        st.markdown("---")

        st.subheader("Resumo Financeiro")
        col1, col2, col3 = st.columns(3)
        
        total_gastos = df_transacoes[df_transacoes['tipo'].str.lower() == 'gasto']['valor'].sum()
        total_receitas = df_transacoes[df_transacoes['tipo'].str.lower() == 'receita']['valor'].sum() 
        saldo_atual = total_receitas - total_gastos

        with col1:
            st.metric(label="Total de Gastos 📉", value=format_currency_br(total_gastos), delta_color="inverse")
        with col2:
            st.metric(label="Total de Receitas 📈", value=format_currency_br(total_receitas))
        with col3:
            st.metric(label="Saldo Atual 💲", value=format_currency_br(saldo_atual))

        st.markdown("---")
        
        st.subheader("Gastos por Banco")
        gastos_por_banco = df_transacoes[df_transacoes['tipo'].str.lower() == 'gasto'].groupby('banco')['valor'].sum().sort_values(ascending=False).reset_index()
        
        if not gastos_por_banco.empty:
            fig_bank = px.bar(
                gastos_por_banco, 
                x='banco', 
                y='valor', 
                color='banco',
                title='Gastos Totais por Banco',
                labels={'banco': 'Banco', 'valor': 'Valor (R$)'},
                text='valor'
            )
            fig_bank.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
            fig_bank.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig_bank, use_container_width=True)
        else:
            st.info("Nenhum gasto registrado para exibir a distribuição por banco.")

        st.markdown("---") # Separador para o novo gráfico

        # --- GRÁFICO DE PIZZA: FONTES DE RECEITA ---
        st.subheader("🍕 Fontes de Receita por Descrição")
        df_receitas = df_transacoes[df_transacoes['tipo'].str.lower() == 'receita'].copy() # Usar .copy() para evitar SettingWithCopyWarning
        
        if not df_receitas.empty:
            # Certificar que 'valor' é numérico para o groupby
            df_receitas['valor'] = pd.to_numeric(df_receitas['valor'], errors='coerce')
            df_receitas.dropna(subset=['valor'], inplace=True)

            receitas_por_descricao = df_receitas.groupby('descricao')['valor'].sum().sort_values(ascending=False).reset_index()
            
            if not receitas_por_descricao.empty and receitas_por_descricao['valor'].sum() > 0:
                fig_receitas_pie = px.pie(
                    receitas_por_descricao,
                    names='descricao',
                    values='valor',
                    title='Distribuição Percentual das Fontes de Receita',
                    hole=.3 # Cria um gráfico de "donut"
                )
                fig_receitas_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label', # Mostrar percentual e a descrição (label)
                    # Para mostrar o valor também: textinfo='percent+label+value'
                    # Para formatar o valor, pode ser necessário adicionar uma coluna formatada ao DataFrame
                )
                fig_receitas_pie.update_layout(
                    legend_title_text='Categorias de Receita',
                    uniformtext_minsize=10, # Garante que o texto não seja muito pequeno
                    uniformtext_mode='hide' # Esconde o texto se for muito pequeno para caber
                )
                st.plotly_chart(fig_receitas_pie, use_container_width=True)
            else:
                st.info("Nenhuma receita com valor positivo registrada com descrição para exibir o gráfico de pizza.")
        else:
            st.info("Nenhuma receita registrada para exibir o gráfico de fontes de receita.")
        # --- FIM GRÁFICO DE PIZZA ---

        st.markdown("---")

        st.subheader("Fluxo de Caixa: Receitas vs. Gastos por Descrição")
        
        receitas_total_sum = df_transacoes[df_transacoes['tipo'].str.lower() == 'receita']['valor'].sum()
        gastos_por_descricao_waterfall = df_transacoes[df_transacoes['tipo'].str.lower() == 'gasto'].groupby('descricao')['valor'].sum().sort_values(ascending=False)

        if not gastos_por_descricao_waterfall.empty or receitas_total_sum > 0:
            names_wf = ['Receitas Totais']
            measures_wf = ['absolute']
            values_wf = [receitas_total_sum]
            texts_wf = [format_currency_br(receitas_total_sum)]

            for desc, val in gastos_por_descricao_waterfall.items():
                names_wf.append(desc)
                measures_wf.append('relative')
                values_wf.append(-val) 
                texts_wf.append(format_currency_br(val))

            names_wf.append('Saldo Final')
            measures_wf.append('total')
            values_wf.append(saldo_atual) 
            texts_wf.append(format_currency_br(saldo_atual))

            fig_waterfall = go.Figure(go.Waterfall(
                name = "Fluxo de Caixa", orientation = "v", measure = measures_wf,
                x = names_wf, textposition = "outside", text = texts_wf, y = values_wf,
                connector = {"line":{"color":"rgb(63, 63, 63)"}},
            ))
            fig_waterfall.update_layout(title_text = "Como suas receitas se transformam em saldo", showlegend = False, height=600)
            st.plotly_chart(fig_waterfall, use_container_width=True)
        else:
            st.info("Nenhuma receita ou gasto significativo registrado para exibir o fluxo de caixa.")

    else:
        st.info("Nenhuma transação registrada para este usuário ainda. Adicione algumas no formulário ou faça um upload!")

    st.markdown("---")
    st.subheader("📤 Upload de Transações em Lote (CSV)")
    
    try:
        with open(TRANSACTION_TEMPLATE_PATH, "rb") as fp:
            st.download_button(
                label="Baixar Modelo CSV de Transações",
                data=fp,
                file_name="transaction_template.csv",
                mime="text/csv"
            )
    except FileNotFoundError:
        st.error(f"Arquivo de modelo '{TRANSACTION_TEMPLATE_PATH}' não encontrado.")

    st.write(f"Use o modelo para formatar seus dados. As colunas esperadas são: `{', '.join(EXPECTED_UPLOAD_COLUMNS)}`.")
    st.write(f"Formatos de data aceitos na coluna 'data_hora': `{UPLOAD_DATE_FORMAT}` (ex: 31/12/2023) ou `{UPLOAD_DATETIME_FORMAT}` (ex: 31/12/2023 15:30:00).")


    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv", key="transaction_uploader")
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            
            missing_cols = [col for col in EXPECTED_UPLOAD_COLUMNS if col not in df_upload.columns]
            if missing_cols:
                st.error(f"O arquivo CSV enviado não contém as colunas esperadas: {', '.join(missing_cols)}. Por favor, use o modelo.")
            else:
                df_to_process = df_upload[EXPECTED_UPLOAD_COLUMNS].copy() 
                st.write("Pré-visualização dos dados carregados (primeiras 5 linhas):")
                st.dataframe(df_to_process.head())

                if st.button("Confirmar e Inserir Transações do CSV"):
                    with st.spinner("Processando transações..."):
                        success_count, fail_count = db_utils.bulk_insert_transactions(username, df_to_process)
                    if success_count > 0:
                        st.success(f"{success_count} transações inseridas com sucesso!")
                    if fail_count > 0:
                        st.warning(f"{fail_count} transações falharam ao serem inseridas. Verifique os avisos acima.")
                    if success_count > 0:
                         st.rerun() 
        except pd.errors.EmptyDataError:
            st.error("O arquivo CSV enviado está vazio.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo CSV: {e}")

    if st.sidebar.button("Formulário de Transação " + FORM_ICON, use_container_width=True, key="dash_to_form_button"):
        st.session_state['page'] = "form"
        st.rerun()