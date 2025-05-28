#!/bin/bash

# Define o arquivo do script python3
python3_SCRIPT="local/db_update.py"

# Limpa o banco de dados existente para um teste limpo (opcional)
# CUIDADO: Isso APAGARÁ todos os dados anteriores!
echo "Removendo o banco de dados existente para um teste limpo..."
rm -f gerenciador_financas.db
echo "Banco de dados limpo."
echo "---"

echo "Executando exemplos para o usuário 'alice':"
python3 "$python3_SCRIPT" --usuario alice --pacote '{"valor": "75,50", "tipo_de_cartao": "debito", "banco": "NuBank", "descricao": "Compras do mês", "tipo": "gasto"}'
sleep 1 # Pequena pausa para melhor visualização
python3 "$python3_SCRIPT" --usuario alice --pacote '{"valor": "25,00", "tipo_de_cartao": "credito", "banco": "Itau", "descricao": "Lanche na padaria", "tipo": "gasto"}'
sleep 1
python3 "$python3_SCRIPT" --usuario alice --pacote '{"valor": "1200.00", "banco": "NuBank", "descricao": "Salário", "tipo": "receita"}' --data "2025-05-21" # Exemplo de receita
echo "---"

echo "Executando exemplos para o usuário 'bob':"
python3 "$python3_SCRIPT" --usuario bob --pacote '{"valor": "15,99", "tipo_de_cartao": "credito", "banco": "Santander", "descricao": "Aplicativo de música", "tipo": "gasto"}'
sleep 1
python3 "$python3_SCRIPT" --usuario bob --pacote '{"valor": "50.00", "banco": "PicPay", "descricao": "Venda de item", "tipo": "receita"}'
echo "---"

echo "Adicionando mais um gasto para 'alice':"
python3 "$python3_SCRIPT" --usuario alice --pacote '{"valor": "300,00", "tipo_de_cartao": "credito", "banco": "Itau", "descricao": "Conta de luz", "tipo": "gasto"}'
echo "---"

echo "Exemplos concluídos. Verifique o arquivo 'gerenciador_financas.db' para ver os dados."
echo "Você pode usar 'sqlite3 gerenciador_financas.db' para inspecionar as tabelas."