#!/usr/bin/env bash
# Build do Render. No plano gratuito não há shell nem "pre-deploy command",
# então tudo o que precisa do banco roda aqui.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Remove o esquema antigo de contas, se ainda existir (exige RESETAR_CONTAS_LEGADO=sim).
python manage.py preparar_banco
python manage.py migrate --no-input

# Superusuário a partir de DJANGO_SUPERUSER_EMAIL e DJANGO_SUPERUSER_PASSWORD.
python manage.py garantir_superusuario

# Dados de demonstração só quando pedido explicitamente.
if [ "${CARREGAR_DEMO:-}" = "sim" ]; then
    python manage.py popular_demo --permitir-fora-de-desenvolvimento
fi
