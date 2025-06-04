# modules/config.py
import os

DB_MASTER_NAME = 'gerenciador_financas.db'
FORM_ICON = "📝"
DASHBOARD_ICON = "📊"
LOGIN_ICON = "🔑"
SIGNUP_ICON = "👤➕"
APP_ICON = "💰"

# For transaction uploads
EXPECTED_UPLOAD_COLUMNS = ['tipo', 'valor', 'tipo_cartao', 'banco', 'descricao', 'data_hora']
# Expected date format in CSV, e.g., 'DD/MM/YYYY' or 'YYYY-MM-DD HH:MM:SS'
# SQLite prefers 'YYYY-MM-DD HH:MM:SS'
UPLOAD_DATE_FORMAT = '%d/%m/%Y' # Example: 31/12/2023
UPLOAD_DATETIME_FORMAT = '%d/%m/%Y %H:%M:%S' # Example: 31/12/2023 15:30:00
# If only date is provided, time will be set to 00:00:00

# Path for the transaction template file
TRANSACTION_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'transaction_template.csv')