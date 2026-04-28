# 💰 Finance Manager — Gerenciador Financeiro Pessoal

> **Status:** MVP funcional com analytics avançado | Stack: Python · Streamlit · SQLite · Plotly  
> **Autor:** Murilo Appugliese — Data Science/Engineering @ Hospital Albert Einstein | Mestrando Eng. Biomédica @ UFABC

---

## 📋 Visão Geral

O **Finance Manager** é uma aplicação web de gestão financeira pessoal construída com **Streamlit**, voltada para o registro, visualização e análise de transações financeiras por usuário. O projeto implementa um ciclo completo de produto de dados: ingestão (manual + upload em lote), persistência (SQLite), transformação (Pandas) e visualização interativa (Plotly), incluindo um **Sankey hierárquico** de fluxo financeiro.

---

## 🏗️ Arquitetura Atual

```
finance_manager/
├── app.py                    # Entry point — roteamento de páginas e gestão de sessão
├── requirements.txt          # Dependências Python
├── transaction_template.csv  # Template para upload em lote (inclui coluna categoria)
├── .devcontainer/
│   └── devcontainer.json     # Configuração GitHub Codespaces (Python 3.11)
└── modules/
    ├── __init__.py
    ├── config.py             # Constantes globais (tipos, categorias, opções Sankey, paths)
    ├── auth.py               # Páginas de login e cadastro
    ├── db_utils.py           # Camada de acesso a dados (SQLite) — CRUD completo
    ├── form.py               # Formulário de registro de transação
    └── dashboard.py          # Dashboard analítico — gráficos, filtros, edição
```

### Modelo de Dados (SQLite)

| Tabela | Descrição |
|--------|-----------|
| `users_auth` | Autenticação: `username (PK)`, `password_hash` (SHA-256) |
| `usuarios_financas` | Mapeamento usuário → tabela financeira pessoal |
| `financas_<username>` | Transações: `id`, `tipo`, `valor`, `tipo_cartao`, `banco`, `descricao`, `categoria`, `data_hora` |

> Migração automática: tabelas antigas sem a coluna `categoria` recebem `ALTER TABLE` no primeiro acesso.

---

## ✅ O que está implementado

### Autenticação
- Cadastro com validação de senha (mínimo 6 caracteres)
- Login com verificação de hash SHA-256
- Controle de sessão via `st.session_state`
- Provisionamento automático da tabela financeira no primeiro acesso

### Registro de Transações
- **3 tipos de transação:** Gasto, Receita, Investimento
- **Categoria dinâmica:** selectbox muda as opções conforme o tipo selecionado
  - Gasto → Alimentação, Moradia, Transporte, Saúde, Educação, Lazer, Vestuário, Serviços & Assinaturas, Outros
  - Receita → Salário, Freelance, Reembolso, Aluguel recebido, Outros
  - Investimento → Renda Fixa, Renda Variável, Fundos, Criptoativos, Previdência, Outros
- Campos completos: valor, tipo de pagamento, banco/instituição, descrição, data e hora
- Validação de campos obrigatórios antes da persistência
- Upload em lote via CSV com template disponível para download
- Suporte a dois formatos de data no upload: `DD/MM/YYYY` e `DD/MM/YYYY HH:MM:SS`

### Dashboard Analítico

**Filtro de período (sidebar)**
- Opções: Este mês · Últimos 3 meses · Este ano · Todo o período · Personalizado
- Filtra todas as métricas, gráficos e a tabela simultaneamente
- Contador de transações visíveis no período selecionado

**Tabela de transações**
- Colunas: id, tipo, valor, tipo de pagamento, banco, descrição, categoria, data/hora
- Ordenação por data decrescente
- Export das transações filtradas em CSV

**Editar / Excluir transação**
- Expander com selectbox de ID (exibe tipo + valor + descrição para fácil identificação)
- Tab **Editar:** formulário pré-preenchido com todos os campos, categoria reativa ao tipo
- Tab **Excluir:** confirmação explícita com nome e valor da transação

**Métricas consolidadas (4 colunas)**
- Total de Receitas · Total de Gastos · Investimentos · Saldo Disponível  
  *(Saldo = Receitas − Gastos − Investimentos)*

**Gráfico de barras — Gastos por Banco**
- Ranking de gastos por instituição financeira com valores formatados

**Gráfico de pizza (donut) — Fontes de Receita**
- Distribuição percentual das receitas por descrição

**Sankey — Fluxo Financeiro (3 níveis)**
```
Fontes de receita ──→ Orçamento Total ──→ Gastos (agregado) ──→ categorias de gasto
                                      ──→ Investimentos (agregado) ──→ ativos individuais
                                      ──→ Saldo Final
```
- Seletor de agrupamento: **Categoria · Banco / Instituição · Descrição**
- Fallback automático: se `categoria` estiver vazia, usa `descricao`
- Nós e links com cores distintas por nível (verde → azul → vermelho/roxo → verde)
- Hover exibe valor formatado em R$
- Labels em preto destacado (Arial Black)
- Nós agregados "Gastos" e "Investimentos" aparecem apenas quando há transações do tipo

### Infraestrutura
- Configurado para rodar direto no **GitHub Codespaces** via `devcontainer.json`
- Script `testes/run_examples.sh` para popular o banco com dados de teste

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
Implementar DAGs para: sincronização de extratos bancários simulados, geração de relatórios periódicos, e triggers de alertas financeiros.

**MinIO como object storage**  
Armazenar os CSVs exportados, backups do banco e futuramente PDFs de relatórios no MinIO local, em vez do filesystem.

**dbt para transformações analíticas**  
Criar modelos dbt sobre o PostgreSQL: `stg_transactions`, `fct_monthly_summary`, `dim_categories`. Documenta a linhagem dos dados e gera um catálogo automático via `dbt docs generate`.

**Evidently AI para monitoramento de dados**  
Detectar drift nos padrões de gastos do usuário ao longo do tempo, com relatórios automáticos.

---

### Fase 3 — IA Integrada ao Produto

**Assistente Financeiro via LLM (Claude API)**  
Módulo de chat integrado ao dashboard onde o usuário faz perguntas em linguagem natural sobre suas finanças: "Quanto gastei com alimentação em março?", "Qual banco concentra mais meus gastos?". O contexto enviado ao modelo é o DataFrame de transações do usuário serializado.

**Categorização Automática de Transações**  
Few-shot prompting para classificar automaticamente transações por categoria a partir da descrição livre.

**Detecção de Anomalias**  
Modelo de isolation forest ou DBSCAN para identificar transações fora do padrão histórico do usuário.

**Previsão de Saldo (Time Series)**  
Prophet ou ARIMA sobre o histórico de transações para projetar o saldo dos próximos 30 dias com intervalo de confiança.

---

### Fase 4 — Qualidade de Produto

**API REST com FastAPI**  
Separar o backend da camada de apresentação. FastAPI expõe endpoints `/transactions`, `/summary`, `/predict`. O Streamlit consome a API.

**Containerização completa**  
`docker-compose.yml` com serviços: `app` (Streamlit), `api` (FastAPI), `db` (PostgreSQL), `minio`, `airflow`.

**AWS CDK para infraestrutura cloud (opcional)**  
Stack CDK para deploy na AWS: RDS PostgreSQL, ECS Fargate, S3 em vez de MinIO, CloudWatch para observabilidade.

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
| Visualização | Sankey hierárquico 3 níveis, gráficos interativos Plotly, filtro temporal dinâmico |
| Produto de Dados | Aplicação end-to-end com auth, UI, analytics, CRUD completo e export |
| Data Warehouse | dbt models com linhagem documentada sobre PostgreSQL *(roadmap)* |
| Orquestração | DAGs Airflow para pipelines recorrentes *(roadmap)* |
| IA Aplicada | LLM para Q&A financeiro, NLP para categorização, anomaly detection *(roadmap)* |
| MLOps | Monitoramento de drift com Evidently, versionamento de modelos *(roadmap)* |
| Infraestrutura | MinIO, Docker, AWS CDK *(roadmap)* |
| Boas Práticas | Tipagem, modularização, migração de schema, separação de responsabilidades |

---

*Desenvolvido por Murilo Appugliese — Engenharia de Dados & IA Aplicada*
