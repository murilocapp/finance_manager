# modules/form.py
import streamlit as st  # type: ignore
from datetime import datetime
from .config import FORM_ICON, DASHBOARD_ICON, TRANSACTION_TYPES, DEFAULT_CATEGORIES
from . import db_utils


def format_currency_br(value):
    try:
        value = float(value)
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"


def transaction_form_page(username):
    st.title(f"{FORM_ICON} Olá, {username}! Registre suas Finanças")
    st.subheader("Insira os detalhes de sua transação abaixo.")

    col_form, col_info = st.columns([2, 1])

    with col_form:
        # Tipo fora do form para atualizar categorias de forma reativa
        transaction_type = st.selectbox(
            "Tipo de Transação",
            TRANSACTION_TYPES,
            key="new_tx_tipo",
            help="Selecione se é um gasto, receita ou investimento.",
        )

        with st.form(key='transaction_form', clear_on_submit=True):
            st.markdown("---")

            tipo_atual = st.session_state.get("new_tx_tipo", "Gasto")
            cat_options = DEFAULT_CATEGORIES.get(tipo_atual, ["Outros"])
            categoria = st.selectbox(
                "Categoria",
                cat_options,
                help="Categoria da transação. Usada para agrupar no gráfico Sankey.",
            )

            value = st.number_input(
                "Valor (R$)",
                min_value=0.01,
                value=None,
                format="%.2f",
                help="Digite o valor da transação (ex: 45.00).",
                key="value_input",
            )

            card_type = st.selectbox(
                "Tipo de Pagamento",
                ("Débito", "Crédito", "Outro/Dinheiro/Pix"),
                index=2,
                help="Selecione o tipo de pagamento.",
            )

            bank = st.text_input(
                "Banco/Instituição",
                placeholder="Ex: Nubank, Itaú, XP Investimentos",
                help="Nome do banco ou fonte/destino do dinheiro.",
                key="bank_input",
            )

            description = st.text_area(
                "Descrição",
                placeholder="Ex: Supermercado, Aluguel, Tesouro Direto",
                help="Uma breve descrição da transação.",
                key="description_input",
            )

            transaction_date = st.date_input(
                "Data da Transação",
                datetime.now().date(),
                help="Data em que a transação ocorreu.",
            )

            transaction_time = st.time_input(
                "Hora da Transação (opcional)",
                datetime.now().time(),
                help="Hora em que a transação ocorreu.",
            )

            st.markdown("---")
            submit_button = st.form_submit_button(label=f"{FORM_ICON} Registrar Transação")

            if submit_button:
                if value is None or value <= 0:
                    st.error("Por favor, digite um valor válido para a transação.")
                elif not description.strip():
                    st.error("Por favor, forneça uma descrição para a transação.")
                elif not bank.strip():
                    st.error("Por favor, forneça o nome do banco ou instituição.")
                else:
                    full_dt = datetime.combine(transaction_date, transaction_time)
                    transaction_details = {
                        "tipo": tipo_atual,
                        "valor": value,
                        "tipo_cartao": card_type,
                        "banco": bank,
                        "descricao": description,
                        "categoria": categoria,
                        "data_hora": full_dt,
                    }
                    if db_utils.insert_transaction(username, transaction_details):
                        st.success("Transação registrada com sucesso! ✅")
                    else:
                        st.error("Houve um erro ao registrar a transação. ❌")

    with col_info:
        tipo_info = st.session_state.get("new_tx_tipo", "Gasto")
        if tipo_info == "Investimento":
            st.info("💡 **Dicas para Investimentos:**\n\n- Use a categoria para distinguir Renda Fixa de Renda Variável.\n- O valor será deduzido do saldo no gráfico Sankey.")
        elif tipo_info == "Receita":
            st.info("💡 **Dicas para Receitas:**\n\n- Seja claro na descrição para identificar a fonte no Sankey.\n- Cada receita forma um nó de origem no fluxo.")
        else:
            st.info("💡 **Dicas para Gastos:**\n\n- A categoria agrupa seus gastos no Sankey.\n- Use categorias consistentes para análise mais clara.")
        st.markdown("---")
        st.write("📈 **Acompanhe seus Gastos!**")
        st.write("Clique no botão 'DASHBOARD' na barra lateral para ver o resumo e o gráfico Sankey.")

    if st.sidebar.button("DASHBOARD " + DASHBOARD_ICON, use_container_width=True, key="form_to_dash_button"):
        st.session_state['page'] = "dashboard"
        st.rerun()
