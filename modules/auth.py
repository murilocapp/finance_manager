# modules/auth.py
import streamlit as st # type: ignore
from . import db_utils # Use . for relative import within package
from .config import LOGIN_ICON, SIGNUP_ICON

def login_page():
    st.header(f"{LOGIN_ICON} Login de Usuário")
    with st.form("login_form"):
        username = st.text_input("Usuário", key="login_username")
        password = st.text_input("Senha", type="password", key="login_password")
        submit_button = st.form_submit_button("Entrar")

        if submit_button:
            if not username or not password:
                st.error("Por favor, preencha usuário e senha.")
            elif db_utils.verify_user(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['page'] = "form" # Redirect to form page after login
                 # Ensure finance table is ready
                db_utils.get_or_create_user_finance_table_name(username)
                st.success(f"Bem-vindo, {username}!")
                st.rerun() # Rerun to reflect login state immediately
            else:
                st.error("Usuário ou senha inválidos.")

def signup_page():
    st.header(f"{SIGNUP_ICON} Criar Nova Conta")
    # Adicione clear_on_submit=True aqui
    with st.form("signup_form", clear_on_submit=True): 
        new_username = st.text_input("Escolha um nome de usuário", key="signup_username_field") # Alterando a key para evitar conflito
        new_password = st.text_input("Escolha uma senha", type="password", key="signup_password_field") # Alterando a key
        confirm_password = st.text_input("Confirme a senha", type="password", key="signup_confirm_password_field") # Alterando a key
        submit_button = st.form_submit_button("Registrar")

        if submit_button:
            if not new_username or not new_password or not confirm_password:
                st.error("Por favor, preencha todos os campos.")
            elif new_password != confirm_password:
                st.error("As senhas não coincidem.")
            elif len(new_password) < 6: # Basic password policy
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                if db_utils.add_user(new_username, new_password):
                    st.success(f"Usuário '{new_username}' criado com sucesso! Você já pode fazer o login.")
                    # Ensure finance table infrastructure is ready upon signup
                    db_utils.get_or_create_user_finance_table_name(new_username)
                    st.session_state['page'] = "login" # Redirect to login page
                    # Não é necessário st.rerun() aqui se clear_on_submit=True está funcionando
                    # e a navegação para login ocorrerá no próximo ciclo de execução do Streamlit.
                    # No entanto, se você quiser forçar a navegação imediatamente, mantenha o st.rerun().
                    # Se o st.rerun() for mantido, a limpeza ocorrerá antes do rerun.
                    st.rerun() 
                else:
                    st.error(f"O nome de usuário '{new_username}' já existe. Tente outro.")
