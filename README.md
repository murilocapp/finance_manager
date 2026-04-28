# 💰 Finance Manager — Gerenciador Financeiro Pessoal

> **Status:** Em retomada ativa | Stack original: Python · Streamlit · SQLite · Plotly  
> **Autor:** Murilo Appugliese — Data Science/Engineering @ Hospital Albert Einstein | Mestrando Eng. Biomédica @ UFABC

---

## 📋 Visão Geral

O **Finance Manager** é uma aplicação web de gestão financeira pessoal construída com **Streamlit**, voltada para o registro, visualização e análise de transações financeiras por usuário. O projeto implementa um ciclo completo de produto de dados: ingestão (manual + upload em lote), persistência (SQLite), transformação (Pandas) e visualização interativa (Plotly).

---

## 🏗️ Arquitetura Atual

```
finance_manager/
├── app.py                    # Entry point — roteamento de páginas e gestão de sessão
├── requirements.txt          # Dependências Python
├── transaction_template.csv  # Template para upload em lote
├── .devcontainer/
│   └── devcontainer.json     # Configuração GitHub Codespaces (Python 3.11)
└── modules/
    ├── __init__.py
    ├── config.py             # Constantes globais (paths, ícones, formatos de data)
    ├── auth.py               # Páginas de login e cadastro
    ├── db_utils.py           # Camada de acesso a dados (SQLite)
    ├── form.py               # Formulário de registro de transação
    └── dashboard.py          # Dashboard analítico com gráficos e export
```

### Modelo de Dados (SQLite)

| Tabela | Descrição |
|--------|-----------|
| `users_auth` | Autenticação: `username (PK)`, `password_hash` (SHA-256) |
| `usuarios_financas` | Mapeamento usuário → tabela financeira pessoal |
| `financas_<username>` | Transações do usuário: `id`, `tipo`, `valor`, `tipo_cartao`, `banco`, `descricao`, `data_hora` |

> Cada usuário possui sua própria tabela de transações, isolando os dados por conta.

---

## ✅ O que está implementado

### Autenticação
- Cadastro de novos usuários com validação de senha (mínimo 6 caracteres)
- Login com verificação de hash SHA-256
- Controle de sessão via `st.session_state`
- Provisionamento automático da tabela financeira no primeiro acesso

### Registro de Transações
- Formulário interativo: tipo (Gasto/Receita), valor, tipo de cartão, banco, descrição, data e hora
- Validação de campos obrigatórios antes da persistência
- Upload em lote via CSV com template disponível para download
- Suporte a dois formatos de data: `DD/MM/YYYY` e `DD/MM/YYYY HH:MM:SS`

### Dashboard Analítico
- Tabela de transações com ordenação por data (mais recentes primeiro)
- Métricas consolidadas: Total de Gastos, Total de Receitas, Saldo Atual
- **Gráfico de barras:** Gastos por banco/instituição
- **Gráfico de pizza (donut):** Distribuição percentual de fontes de receita por descrição
- **Waterfall chart:** Fluxo de caixa — como as receitas se transformam em saldo após cada gasto
- Export das transações em CSV

### Infraestrutura
- Configurado para rodar direto no **GitHub Codespaces** via `devcontainer.json`
- Script `run_examples.sh` para popular o banco com dados de teste

---

## 🚀 Como Executar Localmente

### Pré-requisitos

```bash
Python >= 3.11
pip
```

### Instalação

```bash
git clone <repo-url>
cd finance_manager
pip install -r requirements.txt
```

### Execução

```bash
streamlit run app.py
```

Acesse em: `http://localhost:8501`

### Via GitHub Codespaces

O projeto está configurado para iniciar automaticamente no Codespaces. O Streamlit sobe na porta `8501` com CORS e XSRF desabilitados para o ambiente de preview.

---

## 📦 Dependências Atuais

```
pandas
streamlit
plotly
```

---

## 🔮 Roadmap — Evolução para Portfolio de Dados & IA

> As seções abaixo descrevem como transformar este projeto em um portfólio de alto nível, demonstrando capacidade de construção de produtos de dados end-to-end com IA integrada.

---

### Fase 1 — Fundação Robusta (sem quebrar o que existe)

**Substituir SQLite por PostgreSQL (local via Docker)**  
O modelo multi-tabela por usuário não escala. Consolidar em schema único com `user_id` como FK em uma tabela `transactions` resolve isso e prepara o terreno para conectores externos.

**Adicionar bcrypt para hashing de senhas**  
SHA-256 direto não é adequado para senhas. `bcrypt` ou `argon2-cffi` aplicam salt e stretching, alinhando ao padrão de produção.

**Cobertura mínima de testes**  
`pytest` + `pytest-cov` nas funções de `db_utils.py` e nas transformações do dashboard. CI via GitHub Actions executando os testes a cada push.

---

### Fase 2 — Stack Moderna de Dados

**Apache Airflow para orquestração de pipelines**  
Implementar DAGs para: sincronização de extratos bancários simulados, geração de relatórios periódicos, e triggers de alertas financeiros. Alinha diretamente com a stack do GRIOh.

**MinIO como object storage**  
Armazenar os CSVs exportados, backups do banco e futuramente PDFs de relatórios no MinIO local, em vez do filesystem. Demonstra conhecimento de storage distribuído on-premises.

**dbt para transformações analíticas**  
Criar modelos dbt sobre o PostgreSQL: `stg_transactions`, `fct_monthly_summary`, `dim_categories`. Documenta a linhagem dos dados e gera um catálogo automático via `dbt docs generate`.

**Evidently AI para monitoramento de dados**  
Detectar drift nos padrões de gastos do usuário ao longo do tempo, com relatórios automáticos.

---

### Fase 3 — IA Integrada ao Produto

**Assistente Financeiro via LLM (Claude API)**  
Módulo de chat integrado ao dashboard onde o usuário faz perguntas em linguagem natural sobre suas finanças: "Quanto gastei com alimentação em março?", "Qual banco concentra mais meus gastos?". O contexto enviado ao modelo é o DataFrame de transações do usuário serializado.

**Categorização Automática de Transações**  
Few-shot prompting para classificar automaticamente transações por categoria (alimentação, transporte, lazer, saúde) a partir da descrição livre. Demonstra NLP aplicado a dados financeiros.

**Detecção de Anomalias**  
Modelo de isolation forest ou DBSCAN para identificar transações fora do padrão histórico do usuário. Alertas no dashboard quando um gasto anômalo é detectado.

**Previsão de Saldo (Time Series)**  
Prophet ou ARIMA sobre o histórico de transações para projetar o saldo dos próximos 30 dias. Visualização no dashboard com intervalo de confiança.

---

### Fase 4 — Qualidade de Produto

**API REST com FastAPI**  
Separar o backend da camada de apresentação. FastAPI expõe endpoints `/transactions`, `/summary`, `/predict`. O Streamlit consome a API. Permite futuramente um frontend React ou mobile.

**Containerização completa**  
`docker-compose.yml` com serviços: `app` (Streamlit), `api` (FastAPI), `db` (PostgreSQL), `minio`, `airflow`. Um único `docker compose up` sobe todo o ambiente.

**AWS CDK para infraestrutura cloud (opcional)**  
Stack CDK para deploy na AWS: RDS PostgreSQL, ECS Fargate para os serviços, S3 em vez de MinIO, CloudWatch para observabilidade.

---

## 🛠️ Stack Alvo (Portfolio Completo)

| Camada | Tecnologia |
|--------|------------|
| Frontend | Streamlit (atual) → React (futuro) |
| API | FastAPI |
| Orquestração | Apache Airflow |
| Banco de dados | PostgreSQL |
| Object Storage | MinIO |
| Transformações | dbt |
| IA / LLM | Claude API (Anthropic) |
| ML | scikit-learn, Prophet |
| Monitoramento | Evidently AI |
| IaC | AWS CDK |
| CI/CD | GitHub Actions |
| Containerização | Docker + docker-compose |

---

## 📊 Demonstração de Competências (para Recrutadores)

| Domínio | Como é evidenciado neste projeto |
|---------|----------------------------------|
| Engenharia de Dados | Pipeline de ingestão (manual + bulk CSV), modelagem relacional, ETL com Pandas |
| Data Warehouse | dbt models com linhagem documentada sobre PostgreSQL |
| Orquestração | DAGs Airflow para pipelines recorrentes |
| Produto de Dados | Aplicação end-to-end com auth, UI, analytics e export |
| IA Aplicada | LLM para Q&A financeiro, NLP para categorização, anomaly detection |
| MLOps | Monitoramento de drift com Evidently, versionamento de modelos |
| Infraestrutura | MinIO, Docker, AWS CDK |
| Boas Práticas | Tipagem, docstrings, modularização, testes, CI/CD |

---

*Desenvolvido por Murilo Appugliese — Engenharia de Dados & IA Aplicada*
