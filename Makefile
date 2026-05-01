.PHONY: setup install env run test clean help

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
STREAMLIT := $(VENV)/bin/streamlit

help:
	@echo "Comandos disponíveis:"
	@echo "  make setup   — cria venv, instala deps e configura .env"
	@echo "  make install — instala/atualiza dependências"
	@echo "  make env     — cria .env a partir do .env.example (se não existir)"
	@echo "  make run     — inicia o Streamlit"
	@echo "  make test    — popula banco com dados de teste"
	@echo "  make clean   — remove venv e cache"

setup: $(VENV) install env
	@echo ""
	@echo "✅ Setup completo. Rode: make run"

$(VENV):
	python3 -m venv $(VENV)

install: $(VENV)
	$(PIP) install --upgrade pip -q
	$(PIP) install -r requirements.txt -q
	@echo "✅ Dependências instaladas."

env:
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo ""
	@echo "🔑 Configuração de variáveis de ambiente"
	@echo "─────────────────────────────────────────"
	@current=$$(grep -E '^ANTHROPIC_API_KEY=' .env | cut -d= -f2); \
	if [ -n "$$current" ] && [ "$$current" != "sk-ant-your-key-here" ]; then \
		echo "   ANTHROPIC_API_KEY já configurada ($$current)."; \
		printf "   Deseja substituir? [s/N] "; read ans; \
		if [ "$$ans" = "s" ] || [ "$$ans" = "S" ]; then \
			printf "   Nova ANTHROPIC_API_KEY: "; read key; \
			if [ -n "$$key" ]; then \
				sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$$key|" .env; \
				echo "   ✅ Chave atualizada."; \
			else \
				echo "   ⚠️  Entrada vazia — chave não alterada."; \
			fi; \
		fi; \
	else \
		printf "   ANTHROPIC_API_KEY (necessária para o Assistente IA): "; read key; \
		if [ -n "$$key" ]; then \
			sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$$key|" .env; \
			echo "   ✅ Chave salva em .env"; \
		else \
			echo "   ⚠️  Entrada vazia — o Assistente IA não funcionará sem a chave."; \
		fi; \
	fi

run: $(VENV)
	$(STREAMLIT) run app.py

test: $(VENV)
	@bash testes/run_examples.sh

clean:
	rm -rf $(VENV) modules/__pycache__ __pycache__
	@echo "✅ Ambiente limpo."
