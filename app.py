import streamlit as st
import subprocess
import json
import re
import pandas as pd
import sqlite3
from datetime import datetime
import os
from pandas.errors import DatabaseError

# --- Configurações Gerais ---
# Caminho para o script db_update.py
# Assume que db_update.py está no mesmo diretório que app.py
DB_UPDATE_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'local','db_update.py')
DB_MASTER_NAME = 'gerenciador_financas.db' 

# --- Configuração de Usuário Automático ---
DEFAULT_USERNAME = "usuario_padrao" # Você pode mudar este nome se preferir

# --- Funções Auxiliares de Formatação ---
def format_currency_br(value):
    """Formata um valor numérico para o padrão monetário brasileiro (R$ X.XXX,XX)."""
    try:
        value = float(value)
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00" # Retorna um valor padrão em caso de erro

# --- Funções do Banco de Dados (para visualização no Streamlit) ---
def get_db_connection():
    """Retorna uma conexão com o banco de dados principal."""
    conn = sqlite3.connect(DB_MASTER_NAME)
    return conn

def get_user_finance_table_name(username):
    """
    Obtém o nome da tabela financeira de um usuário a partir da tabela mestra.
    Cria o usuário e a tabela se não existirem.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios_financas (usuario TEXT PRIMARY KEY, tabela_financeira TEXT)")
    conn.commit()

    cursor.execute("SELECT tabela_financeira FROM usuarios_financas WHERE usuario = ?", (username,))
    result = cursor.fetchone()

    if not result:
        table_name = f"financas_{username}"
        cursor.execute("INSERT INTO usuarios_financas (usuario, tabela_financeira) VALUES (?, ?)", (username, table_name))
        conn.commit()
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo_cartao TEXT,
            banco TEXT,
            descricao TEXT,
            data_hora TEXT NOT NULL
        );
        """
        cursor.execute(create_table_sql)
        conn.commit()
        st.info(f"Usuário '{username}' e sua tabela financeira '{table_name}' criados.")
        conn.close() 
        return table_name
    
    conn.close()
    return result[0]

def get_transactions_for_user(username):
    """Obtém as transações de um usuário específico."""
    table_name = get_user_finance_table_name(username) 
    
    conn = get_db_connection()
    df = pd.DataFrame()
    try:
        query = f"SELECT id, tipo, valor, tipo_cartao, banco, descricao, data_hora FROM {table_name} ORDER BY data_hora DESC, id DESC"
        df = pd.read_sql_query(query, conn)
    except DatabaseError as e:
        st.error(f"Erro ao carregar dados da tabela '{table_name}': {e}. Certifique-se de que a tabela possui as colunas esperadas ou que o usuário tem transações.")
    finally:
        conn.close()
    return df

def run_db_update_script(username, json_data, transaction_date=None):
    """
    Executa o script db_update.py como um subprocesso.
    """
    # Garante que o valor é uma string formatada com vírgula para o db_update, se ele espera assim
    json_data_for_db = json_data.copy()
    if 'valor' in json_data_for_db and isinstance(json_data_for_db['valor'], (float, int)):
        json_data_for_db['valor'] = f"{json_data_for_db['valor']:.2f}".replace('.', ',')

    command = [
        "python3", # Use python3 para garantir a versão correta
        DB_UPDATE_SCRIPT_PATH,
        "--usuario", username,
        "--pacote", json.dumps(json_data_for_db)
    ]
    if transaction_date:
        command.extend(["--data", transaction_date])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.returncode == 0:
            st.success(f"Transação registrada com sucesso! {result.stdout}")
            return True
        else:
            st.error(f"Erro ao atualizar o banco de dados (código {result.returncode}): {result.stderr}")
            st.error(f"Comando executado: {' '.join(command)}")
            return False
    except FileNotFoundError:
        st.error(f"Erro: Script '{DB_UPDATE_SCRIPT_PATH}' não encontrado. Verifique o caminho.")
        st.error(f"Caminho procurado: {DB_UPDATE_SCRIPT_PATH}")
        return False
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao executar o script: {e}")
        return False

# --- Páginas da Aplicação ---
def transaction_form_page(username):
    st.title(f"Olá, {username}! 👋")
    st.subheader("Registre uma Nova Transação")

    # Usar st.form para agrupar os widgets e submeter de uma vez
    with st.form(key='transaction_form'):
        st.markdown("---")
        st.write("Preencha os campos abaixo para registrar sua transação:")

        # Tipo de Transação (Gasto/Receita)
        transaction_type = st.selectbox(
            "Tipo de Transação",
            ("Gasto", "Receita"),
            index=0, # Gasto é o padrão
            help="Selecione se é um gasto ou uma receita."
        )

        # Valor da Transação
        value = st.number_input(
            "Valor (R$)",
            min_value=0.01,
            value=None, # Começa vazio
            format="%.2f",
            help="Digite o valor da transação (ex: 45.00)."
        )

        # Tipo de Cartão (opcional, só para gastos)
        card_type = st.selectbox(
            "Tipo de Cartão",
            ("Débito", "Crédito", "Outro/Dinheiro/Pix"), # Incluindo opções mais flexíveis
            index=2, # Padrão para "Outro"
            help="Selecione o tipo de cartão usado, ou 'Outro' para dinheiro/pix etc."
        )

        # Banco
        bank = st.text_input(
            "Banco/Instituição",
            placeholder="Ex: Nubank, Itaú, Salário",
            help="Nome do banco ou fonte/destino do dinheiro."
        )

        # Descrição
        description = st.text_area(
            "Descrição",
            placeholder="Ex: Supermercado, Aluguel, Salário mensal",
            help="Uma breve descrição da transação."
        )

        # Data da Transação (opcional, padrão hoje)
        transaction_date = st.date_input(
            "Data da Transação",
            datetime.now().date(), # Padrão para a data de hoje
            help="Data em que a transação ocorreu."
        )

        st.markdown("---")
        # Botão de Submissão do Formulário
        submit_button = st.form_submit_button(label='Registrar Transação')

        # Lógica após submissão do formulário
        if submit_button:
            # Validação básica dos campos
            if value is None or value <= 0:
                st.error("Por favor, digite um valor válido para a transação.")
            elif not description.strip():
                st.error("Por favor, forneça uma descrição para a transação.")
            elif not bank.strip():
                 st.error("Por favor, forneça o nome do banco ou instituição.")
            else:
                # Prepara os dados no formato JSON esperado pelo db_update.py
                parsed_data = {
                    "tipo": transaction_type.lower(), # 'gasto' ou 'receita'
                    "valor": value, # Já é float
                    "tipo_de_cartao": card_type.lower().replace(' ', '_').replace('/', '_'), # 'debito', 'credito', 'outro_dinheiro_pix'
                    "banco": bank.strip(),
                    "descricao": description.strip()
                }
                
                # Chama o script db_update.py
                # O datetime.strftime('%Y-%m-%d') formata a data para 'AAAA-MM-DD'
                if run_db_update_script(username, parsed_data, transaction_date.strftime('%Y-%m-%d')):
                    st.success("Transação registrada com sucesso!")
                    # Opcional: limpar o formulário após sucesso (requer truques ou reruns controlados)
                    # Para um MVP, a mensagem de sucesso já indica que funcionou.
                else:
                    st.error("Houve um erro ao registrar a transação. Verifique os detalhes e tente novamente.")

    # Botão para ir para a visualização da planilha
    if st.sidebar.button("Ver Planilha Financeira"):
        st.session_state.page = "dashboard"
        st.rerun()

# A página de dashboard permanece a mesma, só mudamos a forma de chegar nela
def dashboard_page(username):
    st.title(f"Planilha Financeira de {username}")

    df_transacoes = get_transactions_for_user(username)

    if not df_transacoes.empty:
        df_transacoes['valor'] = pd.to_numeric(df_transacoes['valor'], errors='coerce')
        df_transacoes.dropna(subset=['valor'], inplace=True) 

        st.dataframe(df_transacoes)
        
        total_gastos = df_transacoes[df_transacoes['tipo'] == 'gasto']['valor'].sum()
        total_receitas = df_transacoes[df_transacoes['tipo'] == 'receita']['valor'].sum() 
        saldo_atual = total_receitas - total_gastos

        st.subheader("Resumo Financeiro")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total de Gastos", value=format_currency_br(total_gastos))
        with col2:
            st.metric(label="Total de Receitas", value=format_currency_br(total_receitas))
        with col3:
            st.metric(label="Saldo Atual", value=format_currency_br(saldo_atual))

    else:
        st.info("Nenhuma transação registrada para este usuário ainda.")
    
    # Botão para voltar para a página de formulário
    if st.sidebar.button("Voltar ao Formulário de Transação"):
        st.session_state.page = "form" # Agora a página é 'form'
        st.rerun()

# --- Controle de Navegação Principal ---
if 'page' not in st.session_state:
    st.session_state['page'] = "form" # Começa diretamente na página de formulário

st.session_state['username'] = DEFAULT_USERNAME

# Renderiza a página baseada no estado atual
if st.session_state['page'] == "form":
    transaction_form_page(st.session_state['username'])
elif st.session_state['page'] == "dashboard":
    dashboard_page(st.session_state['username'])