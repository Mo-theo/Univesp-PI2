#!/usr/bin/env bash
# Build do CondoPort no Render. Interrompe no primeiro erro.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# O plano gratuito do Render não tem Shell; por isso o porteiro de
# demonstração é criado/atualizado aqui, se a senha estiver definida no painel.
if [ -n "${PORTEIRO_DEMO_PASSWORD:-}" ]; then
  python manage.py criar_porteiro_demo
fi

# Dados FICTÍCIOS para demonstração (não duplica se já existirem).
if [ "${SEED_DADOS_DEMO:-False}" = "True" ]; then
  python manage.py popular_dados_teste
fi
