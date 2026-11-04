from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOuUsuarioBackend(ModelBackend):
    """Autentica pelo nome de usuário ou pelo e-mail (sem diferenciar maiúsculas)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username and "@" in username:
            User = get_user_model()
            usuarios = User.objects.filter(email__iexact=username)
            if usuarios.count() != 1:
                # E-mail inexistente ou ambíguo: roda o hasher para não
                # revelar pelo tempo de resposta se o e-mail existe.
                User().set_password(password)
                return None
            username = usuarios.get().get_username()
        return super().authenticate(request, username=username, password=password, **kwargs)
