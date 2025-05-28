import streamlit as st  # type: ignore

# --- Importa as funções das páginas ---
from modules.form import transaction_form_page # Importa a função da página de formulário
from modules.dashboard import dashboard_page # Importa a função da página de dashboard

# --- Configurações Globais ---
DEFAULT_USERNAME = "Murilo" 
PAGE_ICON = "💰" # Ícone geral do aplicativo (para set_page_config)

# --- Configurações Iniciais do Streamlit ---
# Deve ser chamado APENAS UMA VEZ e no topo do script.
st.set_page_config(
    page_title="Gerenciador Financeiro - Murilo",
    page_icon=PAGE_ICON,
    layout="wide" 
)

# --- Controle de Navegação Principal ---
# Inicializa o estado da página se não existir
if 'page' not in st.session_state:
    st.session_state['page'] = "form" # Começa na página de formulário

# Atribui o usuário padrão ao estado da sessão
st.session_state['username'] = DEFAULT_USERNAME

# Renderiza a página baseada no estado atual
if st.session_state['page'] == "form":
    transaction_form_page(st.session_state['username'])
elif st.session_state['page'] == "dashboard":
    dashboard_page(st.session_state['username'])