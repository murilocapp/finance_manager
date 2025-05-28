import streamlit as st # type: ignore
import pandas as pd
import sqlite3
import plotly.express as px # type: ignore
import plotly.graph_objects as go # type: ignore
import os # Necessário para DB_MASTER_NAME e path para o db

# --- Configurações Comuns (repitadas ou passadas, mas aqui para o contexto da página) ---
# Você pode ter um arquivo 'config.py' no futuro para centralizar isso
DB_MASTER_NAME = 'gerenciador_financas.db' 

# --- Configurações de Ícones ---
FORM_ICON = "📝"
DASHBOARD_ICON = "📊"


# --- Funções Auxiliares de Formatação ---
def format_currency_br(value):
    """Formata um valor numérico para o padrão monetário brasileiro (R$ X.XXX,XX)."""
    try:
        value = float(value)
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

# --- Funções do Banco de Dados (necessárias aqui para carregar as transações) ---
# O ideal seria ter um arquivo 'db_utils.py' e importar de lá.
def get_db_connection():
    """Retorna uma conexão com o banco de dados principal."""
    conn = sqlite3.connect(DB_MASTER_NAME)
    return conn

def get_user_finance_table_name(username):
    """
    Obtém o nome da tabela financeira de um usuário a partir da tabela mestra.
    Retorna None se o usuário não for encontrado.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Criar a tabela usuarios_financas se não existir (para garantir)
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios_financas (usuario TEXT PRIMARY KEY, tabela_financeira TEXT)")
    conn.commit()

    cursor.execute("SELECT tabela_financeira FROM usuarios_financas WHERE usuario = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_transactions_for_user(username):
    """Obtém as transações de um usuário específico."""
    table_name = get_user_finance_table_name(username) 
    
    if not table_name:
        st.warning(f"Nenhuma tabela financeira encontrada para o usuário '{username}'.")
        return pd.DataFrame() # Retorna DataFrame vazio se a tabela não existir

    conn = get_db_connection()
    df = pd.DataFrame()
    try:
        query = f"SELECT id, tipo, valor, tipo_cartao, banco, descricao, data_hora FROM {table_name} ORDER BY data_hora DESC, id DESC"
        df = pd.read_sql_query(query, conn)
    except Exception as e: # Captura exceção mais genérica para erro de tabela não encontrada
        st.error(f"Erro ao carregar dados da tabela '{table_name}': {e}. Certifique-se de que a tabela existe ou que o usuário tem transações.")
        df = pd.DataFrame() # Retorna DataFrame vazio em caso de erro
    finally:
        conn.close()
    return df


# --- Função da Página de Dashboard ---
def dashboard_page(username):
    st.title(f"{DASHBOARD_ICON} Planilha Financeira de {username}")
    st.subheader("Visão Geral das Suas Transações")

    df_transacoes = get_transactions_for_user(username)

    if not df_transacoes.empty:
        df_transacoes['valor'] = pd.to_numeric(df_transacoes['valor'], errors='coerce')
        df_transacoes.dropna(subset=['valor'], inplace=True) 

        # Convertendo para datetime para ordenação
        df_transacoes['_data_para_ordenar'] = pd.to_datetime(df_transacoes['data_hora'])
        df_transacoes = df_transacoes.sort_values(by=['_data_para_ordenar', 'id'], ascending=[False, False])
        
        # Formata a coluna 'data_hora' para o formato desejado (string)
        df_transacoes['data_hora'] = df_transacoes['_data_para_ordenar'].dt.strftime('%d/%m/%Y')
        
        # Remove a coluna auxiliar
        df_transacoes = df_transacoes.drop(columns=['_data_para_ordenar'])
        
        st.dataframe(df_transacoes, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Resumo Financeiro")
        col1, col2, col3 = st.columns(3)
        
        total_gastos = df_transacoes[df_transacoes['tipo'] == 'gasto']['valor'].sum()
        total_receitas = df_transacoes[df_transacoes['tipo'] == 'receita']['valor'].sum() 
        saldo_atual = total_receitas - total_gastos

        with col1:
            st.metric(label="Total de Gastos 📉", value=format_currency_br(total_gastos), delta_color="inverse")
        with col2:
            st.metric(label="Total de Receitas 📈", value=format_currency_br(total_receitas))
        with col3:
            st.metric(label="Saldo Atual 💲", value=format_currency_br(saldo_atual))

        st.markdown("---")
        
        # --- Gráfico de Barras com Cores por Banco ---
        st.subheader("Gastos por Banco")
        gastos_por_banco = df_transacoes[df_transacoes['tipo'] == 'gasto'].groupby('banco')['valor'].sum().sort_values(ascending=False).reset_index()
        
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

        st.markdown("---")

        # --- Gráfico de Cascata (Waterfall Chart) ---
        st.subheader("Fluxo de Caixa: Receitas vs. Gastos por Categoria")
        
        # Receitas totais (como o ponto de partida)
        receitas_total = df_transacoes[df_transacoes['tipo'] == 'receita']['valor'].sum()
        
        # Gastos por descrição (para as quedas na cascata)
        gastos_por_descricao = df_transacoes[df_transacoes['tipo'] == 'gasto'].groupby('descricao')['valor'].sum().sort_values(ascending=False)

        # Labels, medidas e valores para o gráfico de cascata
        names = []
        measures = []
        values = []
        texts = []

        # Ponto de partida: Receitas
        names.append('Receitas Totais')
        measures.append('absolute')
        values.append(receitas_total)
        texts.append(format_currency_br(receitas_total))

        # Adiciona cada gasto como uma "queda"
        for desc, val in gastos_por_descricao.items():
            names.append(desc)
            measures.append('relative')
            values.append(-val) # Valor negativo para indicar diminuição
            texts.append(format_currency_br(val)) # Texto deve mostrar o valor positivo do gasto

        # Ponto final: Saldo Atual
        names.append('Saldo Final')
        measures.append('total')
        values.append(saldo_atual)
        texts.append(format_currency_br(saldo_atual))

        fig_waterfall = go.Figure(go.Waterfall(
            name = "Fluxo de Caixa",
            orientation = "v",
            measure = measures,
            x = names,
            textposition = "outside",
            text = texts,
            y = values,
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))

        fig_waterfall.update_layout(
            title_text = "Como suas receitas se transformam em saldo",
            showlegend = False,
            height=500
        )
        
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
        if gastos_por_descricao.empty and receitas_total == 0:
            st.info("Nenhuma receita ou gasto registrado para exibir o fluxo de caixa.")

    else:
        st.info("Nenhuma transação registrada para este usuário ainda.")
    
    st.sidebar.button("Formulário de Transação " + FORM_ICON, on_click=lambda: st.session_state.update(page="form"), use_container_width=True)
    
   