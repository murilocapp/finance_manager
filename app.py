# app.py
import streamlit as st  # type: ignore

# --- Importa as funções das páginas e utilitários ---
from modules.form import transaction_form_page
from modules.dashboard import dashboard_page
from modules.auth import login_page, signup_page
from modules.chat import chat_page
from modules import db_utils
from modules.config import APP_ICON, FORM_ICON, DASHBOARD_ICON, CHAT_ICON, LOGIN_ICON, SIGNUP_ICON

# --- Configurações Iniciais do Streamlit ---
st.set_page_config(
    page_title="Gerenciador Financeiro Pessoal",
    page_icon=APP_ICON,
    layout="wide"
)

# --- Inicialização do Banco de Dados ---
# Garante que as tabelas de autenticação e mestra de finanças existam.
db_utils.create_initial_tables()

# --- Controle de Navegação e Estado da Sessão ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'page' not in st.session_state:
    st.session_state['page'] = "login" # Default to login page
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- Renderização da Página ---
if not st.session_state['logged_in']:
    st.sidebar.title("Bem-vindo!")
    nav_choice = st.sidebar.radio("Navegação", ["Login", "Criar Conta"], key="auth_nav",
                                  captions=[f"{LOGIN_ICON} Acesse sua conta", f"{SIGNUP_ICON} Novo por aqui?"])
    
    if nav_choice == "Login":
        st.session_state['page'] = "login"
        login_page()
    elif nav_choice == "Criar Conta":
        st.session_state['page'] = "signup"
        signup_page()
else:
    # Usuário Logado
    st.sidebar.title(f"Olá, {st.session_state['username']}!")
    st.sidebar.markdown("---")
    
    if st.sidebar.button(f"{FORM_ICON} Registrar Transação", use_container_width=True, key="sidebar_to_form"):
        st.session_state['page'] = "form"
        st.rerun()

    if st.sidebar.button(f"{DASHBOARD_ICON} Meu Dashboard", use_container_width=True, key="sidebar_to_dashboard"):
        st.session_state['page'] = "dashboard"
        st.rerun()

    if st.sidebar.button(f"{CHAT_ICON} Assistente IA", use_container_width=True, key="sidebar_to_chat"):
        st.session_state['page'] = "chat"
        st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True, key="logout_button"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.session_state['page'] = "login"
        st.success("Você saiu com segurança.")
        st.rerun()

    # Renderiza a página principal baseada no estado
    if st.session_state['page'] == "form":
        transaction_form_page(st.session_state['username'])
    elif st.session_state['page'] == "dashboard":
        dashboard_page(st.session_state['username'])
    elif st.session_state['page'] == "chat":
        chat_page(st.session_state['username'])
    else:
        st.session_state['page'] = "form"
        transaction_form_page(st.session_state['username'])