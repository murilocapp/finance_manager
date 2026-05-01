# 💰 Finance Manager — Gerenciador Financeiro Pessoal

> **Status:** MVP + Agente IA integrado | Stack: Python · Streamlit · SQLite · Plotly · Claude API  
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
├── .env.example              # Template de variáveis de ambiente (ANTHROPIC_API_KEY)
├── .devcontainer/
│   └── devcontainer.json     # Configuração GitHub Codespaces (Python 3.11)
└── modules/
    ├── __init__.py
    ├── config.py             # Constantes globais (tipos, categorias, opções Sankey, paths)
    ├── auth.py               # Páginas de login e cadastro
    ├── db_utils.py           # Camada de acesso a dados (SQLite) — CRUD completo
    ├── form.py               # Formulário de registro de transação
    ├── dashboard.py          # Dashboard analítico — gráficos, filtros, edição
    ├── agent.py              # Agente Claude — tool use, loop agentic, execução de tools
    └── chat.py               # Página de chat — UI Streamlit para o agente
```

### Modelo de Dados (SQLite)

| Tabela | Descrição |
|--------|-----------|
| `users_auth` | Autenticação: `username (PK)`, `password_hash` (SHA-256) |
| `usuarios_financas` | Mapeamento usuário → tabela financeira pessoal |
| `financas_<username>` | Transações: `id`, `tipo`, `valor`, `tipo_cartao`, `banco`, `descricao`, `categoria`, `data_hora` |

> Migração automática: tabelas antigas sem a coluna `categoria` recebem `ALTER TABLE` no primeiro acesso.

---

## ⚙️ Configuração

### Variáveis de ambiente

```bash
cp .env.example .env
# Edite .env e adicione sua chave:
# ANTHROPIC_API_KEY=sk-ant-...
```

A API key é necessária apenas para o Assistente IA. O restante da aplicação funciona sem ela.

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

### Assistente IA — Linguagem Natural → Transação

**Agente conversacional integrado ao Streamlit** (`modules/agent.py` + `modules/chat.py`)

- Registro por texto livre: *"Gastei 45 reais no almoço hoje no Nubank, débito"*
- Agente infere todos os campos (tipo, valor, categoria, banco, forma de pagamento, data)
- Confirmação obrigatória antes de salvar — usuário revisa o card antes de confirmar
- Consultas em linguagem natural: *"Quanto gastei este mês?"*, *"Mostre meus investimentos"*
- Contexto dinâmico enviado ao modelo: categorias do usuário, bancos já cadastrados, data atual, últimas 5 transações
- Dashboard atualiza automaticamente após salvar via agente

**Tools disponíveis para o agente:**

| Tool | Descrição |
|------|-----------|
| `create_transaction` | Cria transação com todos os campos validados |
| `query_transactions` | Consulta por período, tipo ou categoria |
| `get_summary` | Métricas consolidadas (receitas, gastos, investimentos, saldo) |

**Modelo:** `claude-sonnet-4-6` via Anthropic API (`tool_use`)

### Infraestrutura
- Configurado para rodar direto no **GitHub Codespaces** via `devcontainer.json`
- Script `testes/run_examples.sh` para popular o banco com dados de teste

---

## 🚀 Como Executar Localmente

### Pré-requisitos

```bash
Python >= 3.11
make
```

### Setup com Makefile (recomendado)

```bash
git clone <repo-url>
cd finance_manager
make setup   # cria venv, instala deps e solicita ANTHROPIC_API_KEY via CLI
make run     # inicia o Streamlit em http://localhost:8501
```

Comandos disponíveis:

| Comando | Ação |
|---------|------|
| `make setup` | Cria venv + instala deps + gera `.env` |
| `make install` | Instala/atualiza dependências |
| `make env` | Cria `.env` a partir do `.env.example` |
| `make run` | Inicia o Streamlit |
| `make test` | Popula banco com dados de teste |
| `make clean` | Remove venv e cache |

### Setup manual

```bash
git clone <repo-url>
cd finance_manager
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make env               # solicita ANTHROPIC_API_KEY via CLI e salva no .env
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
anthropic
python-dotenv
```

---

## 🔮 Roadmap — Transformação em Sistema com Agente Integrado

> Roteiro de evolução do MVP atual para um produto de dados com agente financeiro conversacional, análise inteligente de períodos e integração omnichannel via WhatsApp.

```
MVP Atual → Fase 1 (Fundação) → Fase 2 (Investimentos Acumulados)
         → Fase 3 (Agente: NL → Transação) → Fase 4 (Agente Analista)
         → Fase 5 (Infra & Qualidade) → Fase 6 (WhatsApp)
```

---

### Fase 1 — Fundação Robusta

Pré-requisito técnico para as fases de agente. Nenhuma feature nova visível ao usuário, mas garante que o sistema aguente os casos de uso seguintes.

**Substituir SQLite por PostgreSQL (Docker)**  
Consolidar o modelo multi-tabela por usuário em schema único: tabela `transactions` com `user_id` como FK. O padrão atual não escala e dificulta queries analíticas necessárias para o agente.

**bcrypt para hashing de senhas**  
SHA-256 sem salt não é adequado para senhas. Trocar por `bcrypt` ou `argon2-cffi` alinha ao padrão de produção antes de expor o sistema a mais canais (ex: WhatsApp).

**Cobertura de testes e CI**  
`pytest` + `pytest-cov` cobrindo `db_utils.py` e as transformações analíticas. GitHub Actions executando a suíte a cada push — base para refatorar com segurança nas fases seguintes.

**API REST com FastAPI**  
Separar backend da camada de apresentação. Endpoints: `POST /transactions`, `GET /transactions`, `GET /summary/{period}`, `POST /agent/parse`. O Streamlit e futuramente o WhatsApp consomem a mesma API.

---

### Fase 2 — Área de Investimentos Acumulados

Antes de construir o agente analista, o sistema precisa de uma visão correta do patrimônio investido — incluindo a lógica de resgate.

**Tabela de posição acumulada (`investment_positions`)**  
Cada aporte do tipo `Investimento` incrementa a posição do ativo correspondente (agrupado por `categoria` + `banco`). A posição é calculada como uma running sum, não como saldo de caixa.

```
Posição atual = Σ aportes − Σ resgates (por ativo)
```

**Lógica de resgate via categoria `"Resgate de Investimentos"`**  
Quando uma transação do tipo `Receita` chegar com `categoria = "Resgate de Investimentos"`, o sistema deduz automaticamente o valor da posição do ativo correspondente (identificado pelo campo `banco`). O saldo de caixa aumenta normalmente; o patrimônio investido diminui.

Fluxo de dados:
```
Receita + categoria="Resgate de Investimentos" + banco="XP / Tesouro / ..."
  → db_utils: registra como receita normal (fluxo de caixa)
  → investment_positions: deduz do ativo correspondente (patrimônio)
```

**Painel de Investimentos no Dashboard**  
Nova aba/seção com:
- Tabela de posição atual por ativo (aporte acumulado − resgates)
- Linha do tempo de evolução do patrimônio investido
- Distribuição por categoria (Renda Fixa / Variável / Fundos / etc.) em gráfico de área empilhada
- Rentabilidade implícita: `(posição atual − total aportado) / total aportado × 100%` *(requer input manual de valor de mercado ou integração futura com API de cotações)*

---

### ~~Fase 3 — Agente: Linguagem Natural → Transação~~ ✅ Implementado

Ver seção **Assistente IA** em *O que está implementado* acima.

---

### Fase 4 — Agente Analista Financeiro

O agente deixa de ser apenas um parser e passa a atuar proativamente como consultor financeiro do usuário.

**Análise de período sob demanda**  
Usuário solicita: *"Analise meu último mês"* ou *"Compare meu trimestre atual com o anterior"*. O agente recebe o DataFrame serializado do período e retorna um relatório estruturado:

```
📊 Análise — Abril 2025

GASTOS
• Alimentação representa 38% dos gastos totais (+12% vs março)
• Assinaturas cresceram R$ 85 sem contrapartida identificada
• 3 gastos acima de R$ 200 em Lazer na mesma semana (dias 18-20)

INVESTIMENTOS  
• Taxa de investimento: 8% da receita (meta recomendada: ≥ 20%)
• Concentração em Renda Fixa: 100% — considere diversificar

OPORTUNIDADES
1. Reduzir Alimentação em R$ 150/mês → R$ 1.800/ano
2. Cancelar assinaturas não recorrentes → R$ 85/mês livre
3. Redirecionar 10% do saldo final para Renda Variável
```

**Ferramenta `analyze_period`**  
Recebe `start_date`, `end_date` e `comparison_period` (opcional). Calcula variações, identifica anomalias de gastos, aponta concentrações e gera recomendações priorizadas por impacto financeiro.

**Ferramenta `forecast_balance`**  
Projeção de saldo para os próximos 30/60/90 dias baseada na média histórica por categoria, com alertas para meses com gastos sazonais conhecidos (ex: IPTU, férias).

**Detecção de padrões e alertas proativos**  
- Gasto recorrente novo detectado (ex: nova assinatura)
- Mês sem aporte em investimentos
- Saldo disponível caiu abaixo de X% da receita média
- Categoria de gasto cresceu >30% vs média dos 3 meses anteriores

**Memória de conversa por sessão**  
O agente mantém o contexto da conversa dentro da sessão Streamlit, permitindo perguntas encadeadas: *"E se eu cortar os gastos com lazer pela metade?"* após uma análise prévia.

---

### Fase 5 — Stack de Dados & Qualidade de Produto

**dbt para transformações analíticas**  
Modelos sobre o PostgreSQL: `stg_transactions`, `fct_monthly_summary`, `fct_investment_positions`, `dim_categories`. Linhagem documentada e catálogo via `dbt docs generate`. O agente analista consome as views dbt em vez de calcular no Python.

**Apache Airflow para orquestração**  
DAGs para: geração de relatório mensal automático (PDF via Evidently + Claude), detecção de anomalias agendada, backup do banco para MinIO.

**MinIO como object storage**  
Armazenar relatórios gerados, CSVs exportados e snapshots do banco. Substituível por S3 na nuvem sem mudança de interface.

**Containerização completa**
```yaml
# docker-compose.yml
services:
  app:        # Streamlit
  api:        # FastAPI
  db:         # PostgreSQL
  minio:      # Object storage
  airflow:    # Orquestração
  worker:     # Celery worker para tasks assíncronas (parsing NL, análise)
```

**AWS CDK (deploy opcional)**  
Stack CDK: RDS PostgreSQL, ECS Fargate para app e api, S3 em vez de MinIO, CloudWatch para observabilidade, API Gateway na frente do FastAPI.

---

### Fase 6 — Integração WhatsApp

O mesmo agente da Fase 3 passa a operar via WhatsApp, permitindo registrar transações sem abrir o dashboard.

**Arquitetura**

```
WhatsApp (usuário)
    ↓ mensagem
Twilio / Meta Cloud API (webhook)
    ↓ POST /webhook/whatsapp
FastAPI (worker assíncrono)
    ↓ autenticação por número de telefone
Agente Claude (Fase 3 reutilizado)
    ↓ tool call → create_transaction / query / analyze
PostgreSQL
    ↓ confirmação formatada
WhatsApp (resposta ao usuário)
```

**Autenticação por número de telefone**  
Cada usuário vincula seu número ao account no dashboard (`settings` → *Conectar WhatsApp*). O webhook valida o `from` da mensagem contra a tabela `user_phone_bindings` antes de processar.

**Fluxo de registro de transação via WhatsApp**

```
Usuário: "Paguei 120 de luz hoje, Débito no Neon"

Bot: ✅ Transação identificada:
     • Tipo: Gasto
     • Valor: R$ 120,00
     • Categoria: Moradia
     • Banco: Neon
     • Pagamento: Débito
     • Data: 28/04/2025

     Confirmar? Responda *sim* para salvar ou corrija o que precisar.

Usuário: "sim"
Bot: 💾 Salvo! Saldo do mês: R$ 1.340,00
```

**Comandos especiais via WhatsApp**

| Comando | Resposta do agente |
|---------|--------------------|
| `resumo` | Métricas do mês atual (receitas, gastos, saldo) |
| `analise` | Análise do período atual com recomendações |
| `investimentos` | Posição atual dos investimentos acumulados |
| `ajuda` | Lista de comandos disponíveis |

**Considerações de implementação**
- **Twilio** é a rota mais rápida para prototipagem (sandbox gratuito, SDK Python)
- **Meta Cloud API** é necessária para produção (número de telefone oficial da empresa, aprovação de templates)
- Mensagens de análise longas são quebradas em múltiplas mensagens ou enviadas como documento PDF gerado on-the-fly
- Rate limiting por usuário para evitar abuso da API Claude

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
| IA / LLM | Claude API (Anthropic) — claude-sonnet-4-6, tool use |
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
| IA Aplicada | Agente conversacional com Claude API + tool use: NL → transação, consultas e resumos financeiros |
| MLOps | Monitoramento de drift com Evidently, versionamento de modelos *(roadmap)* |
| Infraestrutura | MinIO, Docker, AWS CDK *(roadmap)* |
| Boas Práticas | Tipagem, modularização, migração de schema, separação de responsabilidades |

---

*Desenvolvido por Murilo Appugliese — Engenharia de Dados & IA Aplicada*
