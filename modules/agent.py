# modules/agent.py
import os
import json
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

from .config import DEFAULT_CATEGORIES, TRANSACTION_TYPES
from . import db_utils

load_dotenv()

_client = None

def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


TOOLS = [
    {
        "name": "create_transaction",
        "description": "Cria uma transação financeira com todos os campos preenchidos. Chame esta tool apenas após confirmar com o usuário.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["Gasto", "Receita", "Investimento"],
                    "description": "Tipo da transação"
                },
                "valor": {
                    "type": "number",
                    "description": "Valor em reais (ex: 45.00)"
                },
                "categoria": {
                    "type": "string",
                    "description": "Categoria da transação conforme o tipo"
                },
                "banco": {
                    "type": "string",
                    "description": "Banco ou instituição financeira"
                },
                "tipo_cartao": {
                    "type": "string",
                    "enum": ["Débito", "Crédito", "Outro/Dinheiro/Pix"],
                    "description": "Forma de pagamento"
                },
                "descricao": {
                    "type": "string",
                    "description": "Descrição breve da transação"
                },
                "data_hora": {
                    "type": "string",
                    "description": "Data e hora no formato YYYY-MM-DD HH:MM:SS"
                }
            },
            "required": ["tipo", "valor", "categoria", "banco", "tipo_cartao", "descricao", "data_hora"]
        }
    },
    {
        "name": "query_transactions",
        "description": "Consulta transações do usuário por período, tipo ou categoria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Data inicial YYYY-MM-DD (opcional)"
                },
                "end_date": {
                    "type": "string",
                    "description": "Data final YYYY-MM-DD (opcional)"
                },
                "tipo": {
                    "type": "string",
                    "enum": ["Gasto", "Receita", "Investimento"],
                    "description": "Filtrar por tipo (opcional)"
                },
                "categoria": {
                    "type": "string",
                    "description": "Filtrar por categoria (opcional)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_summary",
        "description": "Retorna métricas consolidadas: total de receitas, gastos, investimentos e saldo para um período.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Data inicial YYYY-MM-DD (opcional, padrão: início do mês atual)"
                },
                "end_date": {
                    "type": "string",
                    "description": "Data final YYYY-MM-DD (opcional, padrão: hoje)"
                }
            },
            "required": []
        }
    }
]


def _build_system_prompt(username: str, df) -> str:
    cats_json = json.dumps(DEFAULT_CATEGORIES, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    known_banks = []
    if not df.empty and 'banco' in df.columns:
        known_banks = df['banco'].dropna().unique().tolist()[:20]

    recent_rows = ""
    if not df.empty:
        sample = df.head(5)[['tipo', 'valor', 'categoria', 'banco', 'descricao', 'data_hora']].to_dict('records')
        recent_rows = json.dumps(sample, ensure_ascii=False, default=str)

    return f"""Você é um assistente financeiro pessoal para {username}.
Data e hora atual: {now}

Categorias disponíveis por tipo:
{cats_json}

Bancos/instituições já cadastrados pelo usuário:
{json.dumps(known_banks, ensure_ascii=False)}

Últimas 5 transações do usuário (para inferir padrões):
{recent_rows}

Seu trabalho:
1. Quando o usuário descrever uma transação em linguagem natural, extraia os campos e chame create_transaction.
2. Antes de chamar create_transaction, SEMPRE apresente um card resumo com os campos inferidos e peça confirmação.
3. Somente chame create_transaction após o usuário confirmar (ex: "sim", "pode salvar", "confirma").
4. Para consultas e resumos, use query_transactions e get_summary.
5. Use português brasileiro. Seja direto e objetivo.
6. Se algum campo essencial for ambíguo (ex: banco não mencionado), pergunte antes de inferir."""


def _execute_tool(tool_name: str, tool_input: dict, username: str, df) -> str:
    if tool_name == "create_transaction":
        try:
            dt = datetime.strptime(tool_input["data_hora"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.now()

        data = {
            "tipo": tool_input["tipo"],
            "valor": float(tool_input["valor"]),
            "tipo_cartao": tool_input["tipo_cartao"],
            "banco": tool_input["banco"],
            "descricao": tool_input["descricao"],
            "categoria": tool_input["categoria"],
            "data_hora": dt,
        }
        success = db_utils.insert_transaction(username, data)
        if success:
            return json.dumps({"status": "ok", "message": "Transação salva com sucesso."})
        return json.dumps({"status": "error", "message": "Erro ao salvar no banco."})

    elif tool_name == "query_transactions":
        if df.empty:
            return json.dumps({"transactions": []})
        filtered = df.copy()
        if tool_input.get("start_date"):
            filtered = filtered[filtered['data_hora'] >= tool_input["start_date"]]
        if tool_input.get("end_date"):
            filtered = filtered[filtered['data_hora'] <= tool_input["end_date"] + " 23:59:59"]
        if tool_input.get("tipo"):
            filtered = filtered[filtered['tipo'].str.lower() == tool_input["tipo"].lower()]
        if tool_input.get("categoria"):
            filtered = filtered[filtered['categoria'].str.lower() == tool_input["categoria"].lower()]
        records = filtered.head(50).to_dict('records')
        return json.dumps({"transactions": records}, ensure_ascii=False, default=str)

    elif tool_name == "get_summary":
        if df.empty:
            return json.dumps({"receitas": 0, "gastos": 0, "investimentos": 0, "saldo": 0})
        filtered = df.copy()
        if tool_input.get("start_date"):
            filtered = filtered[filtered['data_hora'] >= tool_input["start_date"]]
        if tool_input.get("end_date"):
            filtered = filtered[filtered['data_hora'] <= tool_input["end_date"] + " 23:59:59"]
        receitas = float(filtered[filtered['tipo'] == 'receita']['valor'].sum())
        gastos = float(filtered[filtered['tipo'] == 'gasto']['valor'].sum())
        investimentos = float(filtered[filtered['tipo'] == 'investimento']['valor'].sum())
        return json.dumps({
            "receitas": receitas,
            "gastos": gastos,
            "investimentos": investimentos,
            "saldo": receitas - gastos - investimentos
        })

    return json.dumps({"error": f"Tool desconhecida: {tool_name}"})


def chat(messages: list, username: str, df) -> tuple[str, bool]:
    """
    Processa uma rodada do chat com o agente.
    Retorna (resposta_texto, transaction_saved).
    messages: lista de dicts {role, content} no formato Anthropic.
    """
    client = _get_client()
    system = _build_system_prompt(username, df)
    transaction_saved = False

    working_messages = list(messages)

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system,
            tools=TOOLS,
            messages=working_messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            assistant_content = response.content

            for block in response.content:
                if block.type == "tool_use":
                    result_str = _execute_tool(block.name, block.input, username, df)
                    if block.name == "create_transaction":
                        result_data = json.loads(result_str)
                        if result_data.get("status") == "ok":
                            transaction_saved = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str
                    })

            working_messages = working_messages + [
                {"role": "assistant", "content": assistant_content},
                {"role": "user", "content": tool_results}
            ]
            continue

        text_parts = [b.text for b in response.content if hasattr(b, "text")]
        return "\n".join(text_parts), transaction_saved
