"""Cria (ou atualiza) o usuário porteiro de DEMONSTRAÇÃO.

A senha NUNCA fica no código. Ela vem, nesta ordem:
1. da variável de ambiente PORTEIRO_DEMO_PASSWORD (pode estar no .env);
2. ou é pedida no terminal (sem eco).
"""

import getpass
import sys

from decouple import config
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

ENV_SENHA = "PORTEIRO_DEMO_PASSWORD"


class Command(BaseCommand):
    help = "Cria o usuário porteiro de demonstração (senha via ambiente ou terminal)."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", default="porteiro.demo", help="Nome de usuário.")
        parser.add_argument(
            "--email", default="porteiro.demo@exemplo.com.br", help="E-mail fictício."
        )

    def handle(self, *args, usuario, email, **options):
        User = get_user_model()
        senha = config(ENV_SENHA, default="")
        if not senha:
            senha = self._pedir_senha()

        user = User.objects.filter(username=usuario).first() or User(username=usuario)
        user.email = email
        user.first_name = "Porteiro"
        user.last_name = "Demonstração"
        user.is_active = True
        # O porteiro usa o sistema, não o admin do Django.
        user.is_staff = False
        user.is_superuser = False

        try:
            validate_password(senha, user)
        except ValidationError as e:
            raise CommandError("Senha recusada: " + " ".join(e.messages))

        criado = user.pk is None
        user.set_password(senha)
        user.save()

        acao = "criado" if criado else "atualizado"
        self.stdout.write(
            self.style.SUCCESS(f"Porteiro de demonstração {acao}: {usuario} ({email}).")
        )

    def _pedir_senha(self):
        if not sys.stdin.isatty():
            raise CommandError(
                f"Defina {ENV_SENHA} no ambiente/.env ou rode o comando em um terminal interativo."
            )
        senha = getpass.getpass("Senha do porteiro de demonstração: ")
        if senha != getpass.getpass("Repita a senha: "):
            raise CommandError("As senhas não conferem.")
        if not senha:
            raise CommandError("A senha não pode ser vazia.")
        return senha
