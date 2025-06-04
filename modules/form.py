# modules/form.py
import streamlit as st  # type: ignore
from datetime import datetime
from .config import FORM_ICON, DASHBOARD_ICON # Relative import
from . import db_utils # Relative import

# --- Funções Auxiliares de Formatação (pode ser movida para um utils.py geral se houver mais) ---
def format_currency_br(value):
    """Formata um valor numérico para o padrão monetário brasileiro (R$ X.XXX,XX)."""
    try:
        value = float(value)
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

# --- Função da Página de Formulário ---
def transaction_form_page(username):
    st.title(f"{FORM_ICON} Olá, {username}! Registre suas Finanças")
    st.subheader("Insira os detalhes de sua transação abaixo.")

    col_form, col_info = st.columns([2, 1])

    with col_form:
        with st.form(key='transaction_form', clear_on_submit=True):
            st.markdown("---")
            
            transaction_type = st.selectbox(
                "Tipo de Transação",
                ("Gasto", "Receita"),
                index=0,
                help="Selecione se é um gasto ou uma receita."
            )

            value = st.number_input(
                "Valor (R$)",
                min_value=0.01,
                value=None, 
                format="%.2f",
                help="Digite o valor da transação (ex: 45.00).",
                key="value_input"
            )

            card_type = st.selectbox(
                "Tipo de Cartão",
                ("Débito", "Crédito", "Outro/Dinheiro/Pix"),
                index=2,
                help="Selecione o tipo de cartão usado, ou 'Outro' para dinheiro/pix etc."
            )

            bank = st.text_input(
                "Banco/Instituição",
                placeholder="Ex: Nubank, Itaú, Salário",
                help="Nome do banco ou fonte/destino do dinheiro.",
                key="bank_input"
            )

            description = st.text_area(
                "Descrição",
                placeholder="Ex: Supermercado, Aluguel, Salário mensal",
                help="Uma breve descrição da transação.",
                key="description_input"
            )

            transaction_date = st.date_input(
                "Data da Transação",
                datetime.now().date(), # Defaults to date part
                help="Data em que a transação ocorreu."
            )
            
            transaction_time = st.time_input(
                "Hora da Transação (opcional)",
                datetime.now().time(), # Defaults to current time
                help="Hora em que a transação ocorreu. Se não especificado, será 00:00."
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
                    # Combine date and time
                    full_transaction_datetime = datetime.combine(transaction_date, transaction_time)

                    transaction_details = {
                        "tipo": transaction_type, # Keep original casing for now, db_utils will handle lower()
                        "valor": value,
                        "tipo_cartao": card_type,
                        "banco": bank,
                        "descricao": description,
                        "data_hora": full_transaction_datetime # Pass datetime object
                    }
                    
                    if db_utils.insert_transaction(username, transaction_details):
                        st.success("Transação registrada com sucesso! ✅")
                    else:
                        st.error("Houve um erro ao registrar a transação. Verifique os detalhes e tente novamente. ❌")

    with col_info:
        st.info("💡 **Dicas para registrar:**\n\n- Seja claro na descrição para facilitar a busca depois.\n- 'Outro/Dinheiro/Pix' é ideal para transações que não usam cartão específico.\n- A data e hora padrão são as atuais, mas você pode mudar!")
        st.markdown("---")
        st.write("📈 **Acompanhe seus Gastos!**")
        st.write("Clique no botão 'DASHBOARD' na barra lateral para ver um resumo e todas as suas transações.")

    if st.sidebar.button("DASHBOARD " + DASHBOARD_ICON, use_container_width=True, key="form_to_dash_button"):
        st.session_state['page'] = "dashboard"
        st.rerun()