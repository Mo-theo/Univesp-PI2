from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="E-mail ou usuário",
        max_length=254,
        widget=forms.TextInput(
            attrs={"class": "form-control", "autofocus": True, "autocomplete": "username"}
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "current-password"}
        ),
    )

    error_messages = {
        "invalid_login": "E-mail/usuário ou senha incorretos.",
        "inactive": "Esta conta está inativa.",
    }
