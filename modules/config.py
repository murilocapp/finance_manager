# modules/config.py
import os

DB_MASTER_NAME = 'gerenciador_financas.db'
FORM_ICON = "📝"
DASHBOARD_ICON = "📊"
LOGIN_ICON = "🔑"
SIGNUP_ICON = "👤➕"
APP_ICON = "💰"

# Tipos de transação disponíveis
TRANSACTION_TYPES = ["Gasto", "Receita", "Investimento"]

# Categorias padrão por tipo de transação
DEFAULT_CATEGORIES = {
    "Gasto": [
        "Alimentação",
        "Moradia",
        "Transporte",
        "Saúde",
        "Educação",
        "Lazer",
        "Vestuário",
        "Serviços & Assinaturas",
        "Outros",
    ],
    "Receita": [
        "Salário",
        "Freelance",
        "Reembolso",
        "Aluguel recebido",
        "Outros",
    ],
    "Investimento": [
        "Renda Fixa",
        "Renda Variável",
        "Fundos",
        "Criptoativos",
        "Previdência",
        "Outros",
    ],
}

# Opções de agrupamento para o Sankey
SANKEY_GROUP_OPTIONS = ["categoria", "banco", "descricao"]
SANKEY_GROUP_LABELS = {
    "categoria": "Categoria",
    "banco":     "Banco / Instituição",
    "descricao": "Descrição",
}

# Colunas esperadas no upload CSV
EXPECTED_UPLOAD_COLUMNS = [
    'tipo', 'valor', 'tipo_cartao', 'banco', 'descricao', 'categoria', 'data_hora'
]

UPLOAD_DATE_FORMAT     = '%d/%m/%Y'
UPLOAD_DATETIME_FORMAT = '%d/%m/%Y %H:%M:%S'

TRANSACTION_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'transaction_template.csv'
)