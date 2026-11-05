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

### Dados e usuário de demonstração

```bash
python manage.py popular_dados_teste      # dados FICTÍCIOS (--limpar para recriar)
python manage.py criar_porteiro_demo      # senha via PORTEIRO_DEMO_PASSWORD ou terminal
python manage.py test                     # testes
```

## Deploy no Render

O arquivo `render.yaml` cria o web service (gunicorn + WhiteNoise) e o PostgreSQL.
O `build.sh` instala as dependências, roda `collectstatic` e `migrate` e, se configurado,
cria o porteiro de demonstração e os dados fictícios.

1. No Render: **New → Blueprint**, escolha este repositório e confirme.
2. Preencha `PORTEIRO_DEMO_PASSWORD` quando o Render pedir.
3. Aguarde o deploy e acesse `https://<nome-do-serviço>.onrender.com`.

| Variável | Origem | Descrição |
|---|---|---|
| `SECRET_KEY` | gerada pelo Render | chave do Django |
| `DATABASE_URL` | banco `condoport-db` | conexão com o PostgreSQL |
| `DEBUG` | `False` | ativa as configurações de segurança |
| `PYTHON_VERSION` | `3.12.4` | versão do Python |
| `WEB_CONCURRENCY` | `2` | workers do gunicorn |
| `PORTEIRO_DEMO_PASSWORD` | você define | senha do usuário `porteiro.demo` |
| `SEED_DADOS_DEMO` | `True` | popula dados fictícios no build |
| `RENDER_EXTERNAL_HOSTNAME` | automático | adicionado a `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` |

### Simular produção localmente

No PowerShell (as variáveis valem só para esta janela):

```powershell
$env:DEBUG="False"; $env:FORCAR_HTTPS="False"
python manage.py collectstatic --no-input
python manage.py runserver
```

Para voltar ao modo de desenvolvimento, feche o terminal ou rode
`Remove-Item Env:DEBUG, Env:FORCAR_HTTPS`. A pasta `staticfiles/` é ignorada pelo git.
