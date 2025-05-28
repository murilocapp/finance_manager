import sqlite3
import argparse
import json
from datetime import datetime
import re

DB_MASTER_NAME = 'gerenciador_financas.db'

def get_db_connection():
    """Retorna uma conexão com o banco de dados principal."""
    conn = sqlite3.connect(DB_MASTER_NAME)
    conn.execute("PRAGMA foreign_keys = ON;") # Garante integridade referencial
    return conn

def setup_master_table():
    """Cria a tabela mestra de usuarios_financas se ela não existir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios_financas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            tabela_financeira TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("Tabela mestra 'usuarios_financas' verificada/criada.")

def get_or_create_user_table(usuario):
    """
    Obtém o nome da tabela financeira do usuário ou cria uma nova se o usuário for novo.
    Retorna o nome da tabela financeira.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tenta encontrar o usuário na tabela mestra
    cursor.execute("SELECT tabela_financeira FROM usuarios_financas WHERE usuario = ?", (usuario,))
    resultado = cursor.fetchone()

    if resultado:
        tabela_financeira = resultado[0]
        print(f"Usuário '{usuario}' encontrado. Tabela: '{tabela_financeira}'.")
    else:
        # Se o usuário é novo, gera um nome de tabela e o insere na tabela mestra
        tabela_financeira = f"financas_{usuario.replace(' ', '_').lower()}"
        cursor.execute("INSERT INTO usuarios_financas (usuario, tabela_financeira) VALUES (?, ?)",
                       (usuario, tabela_financeira))
        conn.commit()
        print(f"Novo usuário '{usuario}' registrado. Criando tabela: '{tabela_financeira}'.")

    # Cria a tabela financeira específica do usuário se ela não existir
    # A estrutura da tabela financeira do usuário
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {tabela_financeira} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo_cartao TEXT,
            banco TEXT,
            descricao TEXT,
            data_hora TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    return tabela_financeira

def insert_transaction_into_user_table(tabela_financeira, data):
    """
    Insere os dados da transação na tabela financeira específica do usuário.
    Espera um dicionário com os campos: tipo, valor, tipo_de_cartao, banco, descricao.
    """
    conn = sqlite3.connect(DB_MASTER_NAME) # Conecta ao mesmo DB file para todas as tabelas
    cursor = conn.cursor()
    # MODIFICAÇÃO AQUI: Apenas a data (YYYY-MM-DD)
    data_hora = datetime.now().strftime('%Y-%m-%d')

    try:
        tipo = data.get('tipo', 'gasto').lower()
        
        valor_str = str(data.get('valor', '0.00')).replace(',', '.')
        valor = float(valor_str)

        tipo_cartao = data.get('tipo_de_cartao', '').capitalize()
        banco = data.get('banco', '')
        descricao = data.get('descricao', '')

        cursor.execute(f'''
            INSERT INTO {tabela_financeira} (tipo, valor, tipo_cartao, banco, descricao, data_hora)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tipo, valor, tipo_cartao, banco, descricao, data_hora))
        conn.commit()
        print(f"Transação inserida com sucesso na tabela '{tabela_financeira}'.")
        print(f"Detalhes: Tipo: {tipo}, Valor: R${valor:.2f}, Cartão: {tipo_cartao}, Banco: {banco}, Descrição: {descricao}")
    except KeyError as e:
        print(f"Erro: Chave ausente no pacote JSON: {e}")
    except ValueError as e:
        print(f"Erro de valor ao processar o pacote JSON: {e}")
    except Exception as e:
        print(f"Ocorreu um erro ao inserir a transação: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Atualiza o banco de dados financeiro para um usuário específico.")
    parser.add_argument('--usuario', required=True, help="Nome do usuário para quem a transação será registrada.")
    parser.add_argument('--pacote', required=True,
                        help='Dados da transação em formato JSON. Ex: \'{"valor": "45,00", "tipo_de_cartao": "debito", "banco": "Nubank", "descricao": "Supermercado", "tipo": "gasto"}\'')

    args = parser.parse_args()

    setup_master_table()

    tabela_financeira_do_usuario = get_or_create_user_table(args.usuario)

    try:
        pacote_data = json.loads(args.pacote)
    except json.JSONDecodeError:
        print("Erro: O pacote JSON está mal formatado. Por favor, verifique a sintaxe.")

    insert_transaction_into_user_table(tabela_financeira_do_usuario, pacote_data)
