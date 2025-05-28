import streamlit as st  # type: ignore
import os
from datetime import datetime
import subprocess
import json
import pandas as pd # Necessário para funções de banco de dados, se elas fossem aqui
import sqlite3 # Necessário para funções de banco de dados, se elas fossem aqui
from pandas.errors import DatabaseError # Necessário para funções de banco de dados, se elas fossem aqui


# --- Configurações Comuns (repitidas ou passadas, mas aqui para o contexto da página) ---
# Você pode ter um arquivo 'config.py' no futuro para centralizar isso
DB_UPDATE_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local','db_update.py')
DB_MASTER_NAME = 'gerenciador_financas.db' 

# --- Configurações de Ícones ---
FORM_ICON = "📝"
DASHBOARD_ICON = "📊"


# --- Funções do Banco de Dados (necessárias aqui para a submissão do formulário) ---
# Essas funções foram movidas para cá para manter o módulo self-contained para a sua funcionalidade
# O ideal seria ter um arquivo 'db_utils.py' e importar de lá.
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

def run_db_update_script(username, json_data, transaction_date=None):
    """
    Executa o script db_update.py como um subprocesso.
    """
    json_data_for_db = json_data.copy()
    if 'valor' in json_data_for_db and isinstance(json_data_for_db['valor'], (float, int)):
        json_data_for_db['valor'] = f"{json_data_for_db['valor']:.2f}".replace('.', ',')

    command = [
        "python3",
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


# --- Função da Página de Formulário ---
def transaction_form_page(username):
    st.title(f"{FORM_ICON} Olá, {username}! Registre suas Finanças")
    st.subheader("Insira os detalhes de sua transação abaixo.")

    col_form, col_info = st.columns([2, 1])

    with col_form:
        with st.form(key='transaction_form', clear_on_submit=True):
            st.markdown("---")
            
            transaction_type = st.selectbox(
                "Tipo de Transação",
                ("Gasto", "Receita"),
                index=0,
                help="Selecione se é um gasto ou uma receita."
            )

            value = st.number_input(
                "Valor (R$)",
                min_value=0.01,
                value=None, 
                format="%.2f",
                help="Digite o valor da transação (ex: 45.00).",
                key="value_input"
            )

            card_type = st.selectbox(
                "Tipo de Cartão",
                ("Débito", "Crédito", "Outro/Dinheiro/Pix"),
                index=2,
                help="Selecione o tipo de cartão usado, ou 'Outro' para dinheiro/pix etc."
            )

            bank = st.text_input(
                "Banco/Instituição",
                placeholder="Ex: Nubank, Itaú, Salário",
                help="Nome do banco ou fonte/destino do dinheiro.",
                key="bank_input"
            )

            description = st.text_area(
                "Descrição",
                placeholder="Ex: Supermercado, Aluguel, Salário mensal",
                help="Uma breve descrição da transação.",
                key="description_input"
            )

            transaction_date = st.date_input(
                "Data da Transação",
                datetime.now().date(),
                help="Data em que a transação ocorreu."
            )

            st.markdown("---")
            submit_button = st.form_submit_button(label=f"{FORM_ICON} Registrar Transação")

            if submit_button:
                if value is None or value <= 0:
                    st.error("Por favor, digite um valor válido para a transação.")
                elif not description.strip():
                    st.error("Por favor, forneça uma descrição para a transação.")
                elif not bank.strip():
                     st.error("Por favor, forneça o nome do banco ou instituição.")
                else:
                    parsed_data = {
                        "tipo": transaction_type.lower(),
                        "valor": value,
                        "tipo_de_cartao": card_type.lower().replace(' ', '_').replace('/', '_'),
                        "banco": bank.strip(),
                        "descricao": description.strip()
                    }
                    
                    if run_db_update_script(username, parsed_data, transaction_date.strftime('%Y-%m-%d')):
                        st.success("Transação registrada com sucesso! ✅")
                    else:
                        st.error("Houve um erro ao registrar a transação. Verifique os detalhes e tente novamente. ❌")

    with col_info:
        st.info("💡 **Dicas para registrar:**\n\n- Seja claro na descrição para facilitar a busca depois.\n- 'Outro/Dinheiro/Pix' é ideal para transações que não usam cartão específico.\n- A data padrão é a de hoje, mas você pode mudar!")
        st.markdown("---")
        st.write("📈 **Acompanhe seus Gastos!**")
        st.write("Clique no botão 'DASHBOARD' na barra lateral para ver um resumo e todas as suas transações.")

    st.sidebar.button("DASHBOARD " + DASHBOARD_ICON, on_click=lambda: st.session_state.update(page="dashboard"), use_container_width=True)
    
    