# CondoPort

Sistema web para gestão de visitantes e encomendas em portaria condominial (UNIVESP – PJI240).

## Como rodar localmente

Requisitos: Python 3.12+.

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
copy .env.example .env        # Windows (ou: cp .env.example .env)
# Edite o .env e defina uma SECRET_KEY

# 4. Criar o banco e iniciar o servidor
python manage.py migrate
python manage.py runserver
```

Acesse http://127.0.0.1:8000/.

Sem `DATABASE_URL` no `.env`, o projeto usa SQLite local (`db.sqlite3`). Em produção, defina `DATABASE_URL` apontando para o PostgreSQL.
