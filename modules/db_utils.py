# modules/db_utils.py
import sqlite3
import pandas as pd # type: ignore
import streamlit as st # type: ignore
from datetime import datetime
import hashlib # For basic password hashing, consider bcrypt for production
from .config import DB_MASTER_NAME, UPLOAD_DATE_FORMAT, UPLOAD_DATETIME_FORMAT

def get_db_connection():
    """Retorna uma conexão com o banco de dados principal."""
    conn = sqlite3.connect(DB_MASTER_NAME)
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn

def create_initial_tables():
    """Cria as tabelas mestras (usuários_auth, usuários_financas) se não existirem."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tabela de autenticação de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_auth (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)
    # Tabela mestra que liga usuário à sua tabela financeira (como já existia)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_financas (
            usuario TEXT PRIMARY KEY,
            tabela_financeira TEXT NOT NULL,
            FOREIGN KEY (usuario) REFERENCES users_auth(username)
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    """Gera um hash simples para a senha (use bcrypt em produção)."""
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password):
    """Adiciona um novo usuário à tabela de autenticação."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users_auth (username, password_hash) VALUES (?, ?)",
                       (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError: # Username already exists
        return False
    finally:
        conn.close()

def verify_user(username, password):
    """Verifica as credenciais do usuário."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users_auth WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    if result and result['password_hash'] == hash_password(password):
        return True
    return False

def get_or_create_user_finance_table_name(username):
    """
    Obtém o nome da tabela financeira de um usuário.
    Cria a entrada em usuarios_financas e a tabela financeira se não existirem.
    Esta função deve ser chamada APÓS o usuário ser autenticado ou registrado.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT tabela_financeira FROM usuarios_financas WHERE usuario = ?", (username,))
    result = cursor.fetchone()

    if result:
        conn.close()
        return result['tabela_financeira']
    else:
        table_name = f"financas_{username.lower().replace(' ', '_')}" # Sanitize table name
        try:
            # Adiciona à tabela mestra de finanças
            cursor.execute("INSERT INTO usuarios_financas (usuario, tabela_financeira) VALUES (?, ?)",
                           (username, table_name))
            
            # Cria a tabela de finanças específica do usuário
            create_user_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                valor REAL NOT NULL,
                tipo_cartao TEXT,
                banco TEXT,
                descricao TEXT,
                data_hora TEXT NOT NULL -- Store as ISO8601 TEXT (YYYY-MM-DD HH:MM:SS)
            );
            """
            cursor.execute(create_user_table_sql)
            conn.commit()
            st.info(f"Tabela financeira '{table_name}' pronta para o usuário '{username}'.")
            return table_name
        except Exception as e:
            st.error(f"Erro ao configurar tabela para {username}: {e}")
            conn.rollback() # Rollback in case of error during this sensitive operation
            return None
        finally:
            conn.close()


def insert_transaction(username, transaction_data):
    """Insere uma única transação para o usuário."""
    table_name = get_or_create_user_finance_table_name(username)
    if not table_name:
        st.error(f"Não foi possível obter/criar a tabela financeira para o usuário {username}.")
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure data_hora is in 'YYYY-MM-DD HH:MM:SS' format
        dt_obj = transaction_data['data_hora'] # expects datetime object
        formatted_datetime = dt_obj.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute(f"""
            INSERT INTO {table_name} (tipo, valor, tipo_cartao, banco, descricao, data_hora)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            transaction_data['tipo'].lower(),
            float(transaction_data['valor']),
            transaction_data['tipo_cartao'].lower().replace(' ', '_').replace('/', '_'),
            transaction_data['banco'].strip(),
            transaction_data['descricao'].strip(),
            formatted_datetime
        ))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao inserir transação no banco de dados '{table_name}': {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_transactions_for_user(username):
    """Obtém as transações de um usuário específico."""
    table_name = get_or_create_user_finance_table_name(username)
    if not table_name:
        st.warning(f"Nenhuma tabela financeira encontrada ou configurada para o usuário '{username}'.")
        return pd.DataFrame()

    conn = get_db_connection()
    df = pd.DataFrame()
    try:
        # Verificar se a tabela existe antes de consultá-la
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone() is None:
            st.info(f"A tabela '{table_name}' ainda não existe. Nenhuma transação para carregar.")
            return pd.DataFrame()

        query = f"SELECT id, tipo, valor, tipo_cartao, banco, descricao, data_hora FROM {table_name} ORDER BY data_hora DESC, id DESC"
        df = pd.read_sql_query(query, conn)
        if not df.empty:
             # Convert data_hora from string to datetime for processing, then to desired string format for display
            df['data_hora_dt'] = pd.to_datetime(df['data_hora'])
            # df['data_hora'] = df['data_hora_dt'].dt.strftime('%d/%m/%Y %H:%M:%S') # Example display format
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            st.info(f"A tabela '{table_name}' parece não existir ainda ou foi removida. Nenhuma transação para mostrar.")
            # This case should ideally be caught by the check above, but as a fallback.
            # We ensure get_or_create_user_finance_table_name creates it.
            # If it's still not there, it implies another issue.
        else:
            st.error(f"Erro ao carregar dados da tabela '{table_name}': {e}.")
        df = pd.DataFrame()
    except Exception as e:
        st.error(f"Erro inesperado ao carregar transações da tabela '{table_name}': {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def bulk_insert_transactions(username, df_transactions):
    """Insere múltiplas transações de um DataFrame para o usuário."""
    table_name = get_or_create_user_finance_table_name(username)
    if not table_name:
        st.error(f"Não foi possível obter/criar a tabela financeira para o usuário {username}.")
        return 0, len(df_transactions)

    conn = get_db_connection()
    cursor = conn.cursor()
    successful_inserts = 0
    failed_inserts = 0

    for index, row in df_transactions.iterrows():
        try:
            # Data validation and parsing for 'data_hora'
            raw_date_str = str(row['data_hora']).strip()
            dt_obj = None
            try:
                dt_obj = datetime.strptime(raw_date_str, UPLOAD_DATETIME_FORMAT)
            except ValueError:
                try:
                    dt_obj = datetime.strptime(raw_date_str, UPLOAD_DATE_FORMAT)
                    # If only date is provided, time defaults to 00:00:00
                except ValueError:
                    st.warning(f"Formato de data inválido para '{raw_date_str}' na linha {index + 2}. Pulando. Use '{UPLOAD_DATE_FORMAT}' ou '{UPLOAD_DATETIME_FORMAT}'.")
                    failed_inserts += 1
                    continue
            
            formatted_datetime = dt_obj.strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute(f"""
                INSERT INTO {table_name} (tipo, valor, tipo_cartao, banco, descricao, data_hora)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(row['tipo']).lower(),
                float(row['valor']),
                str(row['tipo_cartao']).lower().replace(' ', '_').replace('/', '_'),
                str(row['banco']).strip(),
                str(row['descricao']).strip(),
                formatted_datetime
            ))
            successful_inserts += 1
        except Exception as e:
            st.error(f"Erro ao inserir linha {index + 2} ({row.get('descricao', 'N/A')}): {e}")
            failed_inserts += 1
            conn.rollback() # Rollback this specific transaction
    
    if successful_inserts > 0:
        conn.commit()
    conn.close()
    return successful_inserts, failed_inserts