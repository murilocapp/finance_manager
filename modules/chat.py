# modules/chat.py
import streamlit as st
from . import db_utils, agent

CHAT_ICON = "🤖"


def _init_chat_state():
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []
    if "chat_api_messages" not in st.session_state:
        st.session_state["chat_api_messages"] = []


def chat_page(username: str):
    st.title(f"{CHAT_ICON} Assistente Financeiro")
    st.caption("Descreva uma transação em linguagem natural ou faça perguntas sobre suas finanças.")

    _init_chat_state()

    api_key_ok = bool(__import__("os").environ.get("ANTHROPIC_API_KEY"))
    if not api_key_ok:
        st.error("ANTHROPIC_API_KEY não configurada. Adicione ao arquivo .env na raiz do projeto.")
        st.code("ANTHROPIC_API_KEY=sk-ant-...")
        return

    df = db_utils.get_transactions_for_user(username)

    # Render histórico
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ex: Gastei 45 reais no almoço hoje no Nubank, débito")

    if user_input:
        st.session_state["chat_messages"].append({"role": "user", "content": user_input})
        st.session_state["chat_api_messages"].append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    reply, saved = agent.chat(
                        st.session_state["chat_api_messages"],
                        username,
                        df,
                    )
                except Exception as e:
                    reply = f"Erro ao contatar a API: {e}"
                    saved = False

            st.markdown(reply)

            if saved:
                st.success("Transação salva! Dashboard atualizado.")

        st.session_state["chat_messages"].append({"role": "assistant", "content": reply})
        st.session_state["chat_api_messages"].append({"role": "assistant", "content": reply})

        if saved:
            st.rerun()

    if st.session_state["chat_messages"]:
        if st.button("Limpar conversa", key="clear_chat"):
            st.session_state["chat_messages"] = []
            st.session_state["chat_api_messages"] = []
            st.rerun()
