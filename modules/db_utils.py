# modules/db_utils.py
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
import hashlib

from .config import DB_MASTER_NAME, UPLOAD_DATE_FORMAT, UPLOAD_DATETIME_FORMAT


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def get_db_connection() -> sqlite3.Connection:
    """Retorna uma conexão com o banco de dados principal."""
    conn = sqlite3.connect(DB_MASTER_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Inicialização de tabelas
# ---------------------------------------------------------------------------

def create_initial_tables() -> None:
    """Cria as tabelas mestras se não existirem."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_auth (
            username      TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_financas (
            usuario           TEXT PRIMARY KEY,
            tabela_financeira TEXT NOT NULL,
            FOREIGN KEY (usuario) REFERENCES users_auth(username)
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def add_user(username: str, password: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users_auth (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(username: str, password: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users_auth WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return bool(result and result['password_hash'] == hash_password(password))


# ---------------------------------------------------------------------------
# Tabela financeira por usuário
# ---------------------------------------------------------------------------

def get_or_create_user_finance_table_name(username: str) -> str | None:
    """
    Retorna o nome da tabela financeira do usuário, criando-a se necessário.
    Também executa a migração para adicionar a coluna 'categoria' caso ela
    ainda não exista (compatibilidade com dados anteriores).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT tabela_financeira FROM usuarios_financas WHERE usuario = ?",
        (username,)
    )
    result = cursor.fetchone()

    if result:
        table_name = result['tabela_financeira']
    else:
        table_name = f"financas_{username.lower().replace(' ', '_')}"
        try:
            cursor.execute(
                "INSERT INTO usuarios_financas (usuario, tabela_financeira) VALUES (?, ?)",
                (username, table_name)
            )
        except Exception as e:
            st.error(f"Erro ao registrar tabela para {username}: {e}")
            conn.close()
            return None

    # Cria tabela principal (inclui 'categoria' desde o início)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo        TEXT    NOT NULL,
            valor       REAL    NOT NULL,
            tipo_cartao TEXT,
            banco       TEXT,
            descricao   TEXT,
            categoria   TEXT,
            data_hora   TEXT    NOT NULL
        )
    """)

    # Migração: adiciona 'categoria' em tabelas antigas que não possuem a coluna
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row['name'] for row in cursor.fetchall()}
    if 'categoria' not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN categoria TEXT")

    conn.commit()
    conn.close()
    return table_name


# ---------------------------------------------------------------------------
# CRUD de transações
# ---------------------------------------------------------------------------

def insert_transaction(username: str, transaction_data: dict) -> bool:
    """Insere uma única transação."""
    table_name = get_or_create_user_finance_table_name(username)
    if not table_name:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        dt_obj: datetime = transaction_data['data_hora']
        cursor.execute(f"""
            INSERT INTO {table_name}
                (tipo, valor, tipo_cartao, banco, descricao, categoria, data_hora)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_data['tipo'].lower(),
            float(transaction_data['valor']),
            transaction_data['tipo_cartao'].lower().replace(' ', '_').replace('/', '_'),
            transaction_data['banco'].strip(),
            transaction_data['descricao'].strip(),
            transaction_data.get('categoria', '').strip(),
            dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
        ))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao inserir transação: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def update_transaction(username: str, transaction_id: int, updated_data: dict) -> bool:
    """Atualiza uma transação existente pelo id."""
    table_name = get_or_create_user_finance_table_name(username)
    if not table_name:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        dt_obj: datetime = updated_data['data_hora']
        cursor.execute(f"""
            UPDATE {table_name}
            SET tipo        = ?,
                valor       = ?,
                tipo_cartao = ?,
                banco       = ?,
                descricao   = ?,
                categoria   = ?,
                data_hora   = ?
            WHERE id = ?
        """, (
            updated_data['tipo'].lower(),
            float(updated_data['valor']),
            updated_data['tipo_cartao'].lower().replace(' ', '_').replace('/', '_'),
            updated_data['banco'].strip(),
            updated_data['descricao'].strip(),
            updated_data.get('categoria', '').strip(),
            dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
            transaction_id,
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"Erro ao atualizar transação id={transaction_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_transaction(username: str, transaction_id: int) -> bool:
    """Remove uma transação pelo id."""
    table_name = get_or_create_user_finance_table_name(username)
    if not table_name:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (transaction_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"Erro ao deletar transação id={transaction_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_transactions_for_user(username: str) -> pd.DataFrame:
    """Retorna todas as transações do usuário ordenadas por data."""
    table_name = get_or_create_user_finance_table_name(username)
    if not table_name:
        return pd.DataFrame()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        if cursor.fetchone() is None:
            return pd.DataFrame()

        df = pd.read_sql_query(
            f"""
            SELECT id, tipo, valor, tipo_cartao, banco, descricao, categoria, data_hora
            FROM {table_name}
            ORDER BY data_hora DESC, id DESC
            """,
            conn
        )
        if not df.empty:
            df['data_hora_dt'] = pd.to_datetime(df['data_hora'])
        return df
    except Exception as e:
        st.error(f"Erro ao carregar transações: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def bulk_insert_transactions(username: str, df_transactions: pd.DataFrame) -> tuple[int, int]:
    """Insere múltiplas transações a partir de um DataFrame."""
    table_name = get_or_create_user_finance_table_name(username)
    if not table_name:
        return 0, len(df_transactions)

    conn = get_db_connection()
    cursor = conn.cursor()
    ok, fail = 0, 0

    for index, row in df_transactions.iterrows():
        try:
            raw_date = str(row['data_hora']).strip()
            dt_obj = None
            for fmt in (UPLOAD_DATETIME_FORMAT, UPLOAD_DATE_FORMAT):
                try:
                    dt_obj = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue
            if dt_obj is None:
                st.warning(f"Formato de data inválido na linha {index + 2}: '{raw_date}'. Pulando.")
                fail += 1
                continue

            cursor.execute(f"""
                INSERT INTO {table_name}
                    (tipo, valor, tipo_cartao, banco, descricao, categoria, data_hora)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row['tipo']).lower(),
                float(row['valor']),
                str(row.get('tipo_cartao', '')).lower().replace(' ', '_').replace('/', '_'),
                str(row.get('banco', '')).strip(),
                str(row.get('descricao', '')).strip(),
                str(row.get('categoria', '')).strip(),
                dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
            ))
            ok += 1
        except Exception as e:
            st.error(f"Erro na linha {index + 2}: {e}")
            fail += 1
            conn.rollback()

    if ok > 0:
        conn.commit()
    conn.close()
    return ok, fail