# modules/dashboard.py
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
from datetime import datetime, timedelta
from .config import (
    DASHBOARD_ICON,
    FORM_ICON,
    EXPECTED_UPLOAD_COLUMNS,
    TRANSACTION_TEMPLATE_PATH,
    UPLOAD_DATE_FORMAT,
    UPLOAD_DATETIME_FORMAT,
    TRANSACTION_TYPES,
    DEFAULT_CATEGORIES,
    SANKEY_GROUP_OPTIONS,
    SANKEY_GROUP_LABELS,
)
from . import db_utils
from .form import format_currency_br
from io import StringIO


# ---------------------------------------------------------------------------
# Sankey
# ---------------------------------------------------------------------------

def _resolve_group(df_sub: pd.DataFrame, group_col: str) -> pd.Series:
    """Returns the grouping series, falling back to descricao when categoria is empty."""
    if group_col == "categoria":
        cat = df_sub["categoria"].replace("", pd.NA)
        return cat.fillna(df_sub["descricao"]).fillna("Sem categoria")
    return df_sub[group_col].fillna("Sem categoria").replace("", "Sem categoria")


def build_sankey(df: pd.DataFrame, group_col: str) -> go.Figure | None:
    df_receitas = df[df["tipo"].str.lower() == "receita"].copy()
    df_gastos = df[df["tipo"].str.lower() == "gasto"].copy()
    df_invest = df[df["tipo"].str.lower() == "investimento"].copy()

    if df_receitas.empty:
        return None

    df_receitas["_group"] = _resolve_group(df_receitas, group_col)
    income_groups = df_receitas.groupby("_group")["valor"].sum().sort_values(ascending=False)
    total_receitas = income_groups.sum()

    if not df_gastos.empty:
        df_gastos["_group"] = _resolve_group(df_gastos, group_col)
        expense_groups = df_gastos.groupby("_group")["valor"].sum().sort_values(ascending=False)
    else:
        expense_groups = pd.Series(dtype=float)

    if not df_invest.empty:
        df_invest["_group"] = _resolve_group(df_invest, group_col)
        invest_groups = df_invest.groupby("_group")["valor"].sum().sort_values(ascending=False)
    else:
        invest_groups = pd.Series(dtype=float)

    total_gastos = expense_groups.sum()
    total_invest = invest_groups.sum()
    saldo_final = total_receitas - total_gastos - total_invest

    # --- Nodes ---
    labels, colors = [], []

    # Level 1 — income sources
    income_idx = {}
    for name in income_groups.index:
        income_idx[name] = len(labels)
        labels.append(str(name))
        colors.append("#2ecc71")

    # Level 2 — budget aggregate
    budget_idx = len(labels)
    labels.append("Orçamento Total")
    colors.append("#3498db")

    # Level 2 → 3 — gastos aggregate (only if there are expenses)
    gastos_agg_idx = None
    if total_gastos > 0:
        gastos_agg_idx = len(labels)
        labels.append("Gastos")
        colors.append("#c0392b")

    # Level 3 — expense breakdown
    expense_idx = {}
    for name in expense_groups.index:
        expense_idx[name] = len(labels)
        labels.append(str(name))
        colors.append("#e74c3c")

    # Level 2 → 3 — investimentos aggregate (only if there are investments)
    invest_agg_idx = None
    if total_invest > 0:
        invest_agg_idx = len(labels)
        labels.append("Investimentos")
        colors.append("#6c3483")

    # Level 3 — investment breakdown
    invest_idx = {}
    for name in invest_groups.index:
        invest_idx[name] = len(labels)
        labels.append(str(name))
        colors.append("#9b59b6")

    # Level 2 — saldo final
    saldo_idx = len(labels)
    labels.append("Saldo Final")
    colors.append("#27ae60" if saldo_final >= 0 else "#c0392b")

    # --- Links ---
    src, tgt, vals, link_colors, hover_vals = [], [], [], [], []

    # Income sources → Orçamento Total
    for name, val in income_groups.items():
        src.append(income_idx[name])
        tgt.append(budget_idx)
        vals.append(val)
        link_colors.append("rgba(46,204,113,0.35)")
        hover_vals.append(format_currency_br(val))

    # Orçamento Total → Gastos (aggregate)
    if gastos_agg_idx is not None:
        src.append(budget_idx)
        tgt.append(gastos_agg_idx)
        vals.append(total_gastos)
        link_colors.append("rgba(192,57,43,0.35)")
        hover_vals.append(format_currency_br(total_gastos))

    # Gastos (aggregate) → each expense group
    for name, val in expense_groups.items():
        src.append(gastos_agg_idx)
        tgt.append(expense_idx[name])
        vals.append(val)
        link_colors.append("rgba(231,76,60,0.35)")
        hover_vals.append(format_currency_br(val))

    # Orçamento Total → Investimentos (aggregate)
    if invest_agg_idx is not None:
        src.append(budget_idx)
        tgt.append(invest_agg_idx)
        vals.append(total_invest)
        link_colors.append("rgba(108,52,131,0.35)")
        hover_vals.append(format_currency_br(total_invest))

    # Investimentos (aggregate) → each investment group
    for name, val in invest_groups.items():
        src.append(invest_agg_idx)
        tgt.append(invest_idx[name])
        vals.append(val)
        link_colors.append("rgba(155,89,182,0.35)")
        hover_vals.append(format_currency_br(val))

    # Orçamento Total → Saldo Final
    if saldo_final > 0:
        src.append(budget_idx)
        tgt.append(saldo_idx)
        vals.append(saldo_final)
        link_colors.append("rgba(39,174,96,0.35)")
        hover_vals.append(format_currency_br(saldo_final))

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        textfont=dict(size=14, color="black", family="Arial Black, Arial, sans-serif"),
        node=dict(
            pad=20,
            thickness=24,
            line=dict(color="black", width=0.5),
            label=labels,
            color=colors,
        ),
        link=dict(
            source=src,
            target=tgt,
            value=vals,
            color=link_colors,
            customdata=hover_vals,
            hovertemplate="%{source.label} → %{target.label}<br>Valor: %{customdata}<extra></extra>",
        ),
    ))
    fig.update_layout(
        title_text="Fluxo Financeiro",
        height=520,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


# ---------------------------------------------------------------------------
# Edit / Delete helper
# ---------------------------------------------------------------------------

def _edit_delete_section(username: str, df: pd.DataFrame):
    """Expander with edit and delete controls for an existing transaction."""
    with st.expander("✏️ Editar ou Excluir Transação"):
        if df.empty:
            st.info("Nenhuma transação disponível.")
            return

        def fmt_tx(tx_id):
            row = df[df["id"] == tx_id].iloc[0]
            tipo_str = str(row["tipo"]).upper()
            desc = str(row["descricao"])[:35]
            val = format_currency_br(row["valor"])
            return f"#{tx_id} | {tipo_str} | {val} | {desc}"

        selected_id = st.selectbox(
            "Selecione a transação",
            df["id"].tolist(),
            format_func=fmt_tx,
            key="manage_tx_id",
        )

        if selected_id is None:
            return

        row = df[df["id"] == selected_id].iloc[0]

        tab_edit, tab_del = st.tabs(["✏️ Editar", "🗑️ Excluir"])

        # ---- Delete ----
        with tab_del:
            st.warning(
                f"Tem certeza que deseja excluir a transação **#{selected_id}** — "
                f"*{row['descricao']}* ({format_currency_br(row['valor'])})?",
                icon="⚠️",
            )
            if st.button("🗑️ Confirmar Exclusão", type="primary", key="btn_confirm_delete"):
                if db_utils.delete_transaction(username, int(selected_id)):
                    st.success("Transação excluída com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao excluir a transação.")

        # ---- Edit ----
        with tab_edit:
            current_tipo = str(row["tipo"]).capitalize()
            tipo_index = TRANSACTION_TYPES.index(current_tipo) if current_tipo in TRANSACTION_TYPES else 0

            # Tipo fora do sub-form para categorias reativas
            edit_tipo = st.selectbox(
                "Tipo",
                TRANSACTION_TYPES,
                index=tipo_index,
                key=f"edit_tipo_{selected_id}",
            )

            cat_options = DEFAULT_CATEGORIES.get(edit_tipo, ["Outros"])
            current_cat = str(row.get("categoria", "")) if pd.notna(row.get("categoria")) else ""
            safe_cat_idx = cat_options.index(current_cat) if current_cat in cat_options else 0

            with st.form(key=f"edit_form_{selected_id}"):
                edit_cat = st.selectbox("Categoria", cat_options, index=safe_cat_idx)
                edit_valor = st.number_input(
                    "Valor (R$)", min_value=0.01, value=float(row["valor"]), format="%.2f"
                )

                card_options = ["Débito", "Crédito", "Outro/Dinheiro/Pix"]
                card_idx = 2
                for i, opt in enumerate(card_options):
                    if opt.lower().replace(" ", "_").replace("/", "_") == str(row["tipo_cartao"]).lower():
                        card_idx = i
                        break
                edit_card = st.selectbox("Tipo de Pagamento", card_options, index=card_idx)
                edit_banco = st.text_input("Banco/Instituição", value=str(row["banco"]))
                edit_desc = st.text_area("Descrição", value=str(row["descricao"]))

                current_dt = row["data_hora_dt"] if "data_hora_dt" in df.columns else datetime.now()
                if not isinstance(current_dt, datetime):
                    current_dt = datetime.now()
                edit_date = st.date_input("Data", current_dt.date(), key=f"edit_date_{selected_id}")
                edit_time = st.time_input("Hora", current_dt.time(), key=f"edit_time_{selected_id}")

                if st.form_submit_button("💾 Salvar Alterações"):
                    full_dt = datetime.combine(edit_date, edit_time)
                    updated = {
                        "tipo": edit_tipo,
                        "valor": edit_valor,
                        "tipo_cartao": edit_card,
                        "banco": edit_banco,
                        "descricao": edit_desc,
                        "categoria": edit_cat,
                        "data_hora": full_dt,
                    }
                    if db_utils.update_transaction(username, int(selected_id), updated):
                        st.success("Transação atualizada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar a transação.")


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------

def _period_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Renders the period selector in the sidebar and returns the filtered DataFrame."""
    today = datetime.now().date()

    PERIOD_OPTIONS = {
        "Este mês": "month",
        "Últimos 3 meses": "quarter",
        "Este ano": "year",
        "Todo o período": "all",
        "Personalizado": "custom",
    }

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Período")
    selected_label = st.sidebar.selectbox(
        "Filtrar por período",
        list(PERIOD_OPTIONS.keys()),
        index=0,
        key="period_select",
        label_visibility="collapsed",
    )
    period = PERIOD_OPTIONS[selected_label]

    if period == "month":
        start = today.replace(day=1)
        end = today
    elif period == "quarter":
        start = today - timedelta(days=89)
        end = today
    elif period == "year":
        start = today.replace(month=1, day=1)
        end = today
    elif period == "all":
        return df
    else:  # custom
        col_a, col_b = st.sidebar.columns(2)
        with col_a:
            start = st.sidebar.date_input("De", today.replace(day=1), key="period_start")
        with col_b:
            end = st.sidebar.date_input("Até", today, key="period_end")

    if "data_hora_dt" not in df.columns:
        return df

    mask = (df["data_hora_dt"].dt.date >= start) & (df["data_hora_dt"].dt.date <= end)
    filtered = df[mask]
    total = len(df)
    shown = len(filtered)
    st.sidebar.caption(f"{shown} de {total} transações no período.")
    return filtered


def dashboard_page(username):
    st.title(f"{DASHBOARD_ICON} Planilha Financeira de {username}")

    df_transacoes = db_utils.get_transactions_for_user(username)

    if not df_transacoes.empty:
        df_transacoes["valor"] = pd.to_numeric(df_transacoes["valor"], errors="coerce")
        df_transacoes.dropna(subset=["valor"], inplace=True)

        if "data_hora_dt" not in df_transacoes.columns and "data_hora" in df_transacoes.columns:
            df_transacoes["data_hora_dt"] = pd.to_datetime(df_transacoes["data_hora"])

        df_transacoes = _period_filter(df_transacoes)

        if "data_hora_dt" in df_transacoes.columns:
            df_transacoes = df_transacoes.sort_values(
                by=["data_hora_dt", "id"], ascending=[False, False]
            )
            df_transacoes["data_hora_display"] = df_transacoes["data_hora_dt"].dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
        else:
            df_transacoes["data_hora_display"] = pd.Series(dtype="str")

        # --- Transaction table ---
        st.subheader("Visão Geral das Suas Transações")
        df_display = df_transacoes[
            ["id", "tipo", "valor", "tipo_cartao", "banco", "descricao", "categoria", "data_hora_display"]
        ].copy()
        df_display.rename(columns={"data_hora_display": "Data/Hora"}, inplace=True)
        df_display["tipo"] = df_display["tipo"].str.upper()
        df_display["valor_formatado"] = df_display["valor"].apply(format_currency_br)

        st.dataframe(
            df_display[["id", "tipo", "valor_formatado", "tipo_cartao", "banco", "descricao", "categoria", "Data/Hora"]],
            use_container_width=True,
            hide_index=True,
        )

        # CSV export
        if "data_hora_dt" in df_transacoes.columns:
            csv_data = df_transacoes[EXPECTED_UPLOAD_COLUMNS[:-1] + ["data_hora_dt"]].copy()
            csv_data["data_hora"] = csv_data["data_hora_dt"].dt.strftime(UPLOAD_DATETIME_FORMAT)
            csv_data_final = csv_data[EXPECTED_UPLOAD_COLUMNS]
        else:
            available = [c for c in EXPECTED_UPLOAD_COLUMNS if c in df_transacoes.columns]
            csv_data_final = df_transacoes[available].copy()
            for col in EXPECTED_UPLOAD_COLUMNS:
                if col not in csv_data_final.columns:
                    csv_data_final[col] = pd.NA

        csv_buffer = StringIO()
        csv_data_final.to_csv(csv_buffer, index=False, sep=",", encoding="utf-8")
        st.download_button(
            label="📥 Baixar Transações (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"transacoes_{username}.csv",
            mime="text/csv",
        )

        # --- Edit / Delete ---
        _edit_delete_section(username, df_transacoes)

        st.markdown("---")

        # --- Metrics ---
        total_gastos = df_transacoes[df_transacoes["tipo"].str.lower() == "gasto"]["valor"].sum()
        total_receitas = df_transacoes[df_transacoes["tipo"].str.lower() == "receita"]["valor"].sum()
        total_invest = df_transacoes[df_transacoes["tipo"].str.lower() == "investimento"]["valor"].sum()
        saldo_atual = total_receitas - total_gastos - total_invest

        st.subheader("Resumo Financeiro")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Receitas 📈", format_currency_br(total_receitas))
        with col2:
            st.metric("Total de Gastos 📉", format_currency_br(total_gastos), delta_color="inverse")
        with col3:
            st.metric("Investimentos 📊", format_currency_br(total_invest))
        with col4:
            st.metric("Saldo Disponível 💲", format_currency_br(saldo_atual))

        st.markdown("---")

        # --- Bar chart: expenses by bank ---
        st.subheader("Gastos por Banco")
        gastos_por_banco = (
            df_transacoes[df_transacoes["tipo"].str.lower() == "gasto"]
            .groupby("banco")["valor"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        if not gastos_por_banco.empty:
            fig_bank = px.bar(
                gastos_por_banco,
                x="banco",
                y="valor",
                color="banco",
                title="Gastos Totais por Banco",
                labels={"banco": "Banco", "valor": "Valor (R$)"},
                text="valor",
            )
            fig_bank.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
            fig_bank.update_layout(uniformtext_minsize=8, uniformtext_mode="hide")
            st.plotly_chart(fig_bank, use_container_width=True)
        else:
            st.info("Nenhum gasto registrado para exibir por banco.")

        st.markdown("---")

        # --- Pie chart: income sources ---
        st.subheader("Fontes de Receita por Descrição")
        df_receitas_pie = df_transacoes[df_transacoes["tipo"].str.lower() == "receita"].copy()
        if not df_receitas_pie.empty:
            receitas_por_desc = (
                df_receitas_pie.groupby("descricao")["valor"].sum().sort_values(ascending=False).reset_index()
            )
            if receitas_por_desc["valor"].sum() > 0:
                fig_pie = px.pie(
                    receitas_por_desc,
                    names="descricao",
                    values="valor",
                    title="Distribuição Percentual das Fontes de Receita",
                    hole=0.3,
                )
                fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                fig_pie.update_layout(legend_title_text="Fontes", uniformtext_minsize=10, uniformtext_mode="hide")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Nenhuma receita com valor positivo para exibir.")
        else:
            st.info("Nenhuma receita registrada.")

        st.markdown("---")

        # --- Sankey ---
        st.subheader("Fluxo Financeiro (Sankey)")

        group_col = st.radio(
            "Agrupar por:",
            options=SANKEY_GROUP_OPTIONS,
            format_func=lambda k: SANKEY_GROUP_LABELS[k],
            horizontal=True,
            key="sankey_group",
        )

        fig_sankey = build_sankey(df_transacoes, group_col)
        if fig_sankey is not None:
            if saldo_atual < 0:
                st.warning(
                    f"Atenção: saldo negativo ({format_currency_br(saldo_atual)}). "
                    "O nó 'Saldo Final' não aparece no Sankey quando o saldo é negativo.",
                    icon="⚠️",
                )
            st.plotly_chart(fig_sankey, use_container_width=True)
        else:
            st.info("Adicione receitas para visualizar o fluxo financeiro.")

    else:
        st.info("Nenhuma transação registrada ainda. Adicione no formulário ou faça upload!")

    st.markdown("---")

    # --- Bulk CSV upload ---
    st.subheader("📤 Upload de Transações em Lote (CSV)")

    try:
        with open(TRANSACTION_TEMPLATE_PATH, "rb") as fp:
            st.download_button(
                label="Baixar Modelo CSV de Transações",
                data=fp,
                file_name="transaction_template.csv",
                mime="text/csv",
            )
    except FileNotFoundError:
        st.error(f"Arquivo de modelo '{TRANSACTION_TEMPLATE_PATH}' não encontrado.")

    st.write(
        f"Use o modelo para formatar seus dados. Colunas esperadas: `{', '.join(EXPECTED_UPLOAD_COLUMNS)}`."
    )
    st.write(
        f"Formatos de data aceitos: `{UPLOAD_DATE_FORMAT}` (ex: 31/12/2023) "
        f"ou `{UPLOAD_DATETIME_FORMAT}` (ex: 31/12/2023 15:30:00)."
    )

    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv", key="transaction_uploader")
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            missing_cols = [c for c in EXPECTED_UPLOAD_COLUMNS if c not in df_upload.columns]
            if missing_cols:
                st.error(f"Colunas ausentes no CSV: {', '.join(missing_cols)}. Use o modelo.")
            else:
                df_to_process = df_upload[EXPECTED_UPLOAD_COLUMNS].copy()
                st.write("Pré-visualização (primeiras 5 linhas):")
                st.dataframe(df_to_process.head())

                if st.button("Confirmar e Inserir Transações do CSV"):
                    with st.spinner("Processando transações..."):
                        success_count, fail_count = db_utils.bulk_insert_transactions(username, df_to_process)
                    if success_count > 0:
                        st.success(f"{success_count} transações inseridas com sucesso!")
                    if fail_count > 0:
                        st.warning(f"{fail_count} transações falharam. Verifique os avisos acima.")
                    if success_count > 0:
                        st.rerun()
        except pd.errors.EmptyDataError:
            st.error("O arquivo CSV está vazio.")
        except Exception as e:
            st.error(f"Erro ao processar o CSV: {e}")

    if st.sidebar.button("Formulário de Transação " + FORM_ICON, use_container_width=True, key="dash_to_form_button"):
        st.session_state["page"] = "form"
        st.rerun()
