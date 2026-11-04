import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Morador, Visitante


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


class BootstrapFormMixin:
    """Aplica as classes do Bootstrap 5 aos widgets do formulário."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                css = "form-select"
            elif isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        # Destaca em vermelho os campos com erro.
        for nome in self.errors:
            if nome in self.fields:
                attrs = self.fields[nome].widget.attrs
                attrs["class"] = f"{attrs.get('class', '')} is-invalid".strip()


class MoradorForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Morador
        fields = ["nome", "cpf", "telefone", "email", "bloco", "apartamento", "status"]
        widgets = {
            "cpf": forms.TextInput(attrs={"placeholder": "000.000.000-00", "inputmode": "numeric"}),
            "telefone": forms.TextInput(attrs={"placeholder": "(00) 00000-0000", "inputmode": "tel"}),
        }
        help_texts = {"cpf": "Somente números ou com pontuação."}

    def clean_cpf(self):
        digitos = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if len(digitos) != 11:
            raise forms.ValidationError("O CPF deve ter 11 dígitos.")
        cpf = f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
        duplicado = Morador.objects.filter(cpf=cpf).exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise forms.ValidationError("Já existe um morador com este CPF.")
        return cpf


class VisitanteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Visitante
        fields = ["morador", "nome", "documento", "telefone", "motivo"]
        widgets = {
            "telefone": forms.TextInput(attrs={"placeholder": "(00) 00000-0000", "inputmode": "tel"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só moradores ativos recebem visitas.
        self.fields["morador"].queryset = Morador.objects.filter(status=Morador.Status.ATIVO)
        self.fields["morador"].empty_label = "Selecione o morador / apartamento"
