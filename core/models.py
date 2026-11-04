from django.core.exceptions import ValidationError
from django.db import models


class Morador(models.Model):
    class Status(models.TextChoices):
        ATIVO = "ativo", "Ativo"
        INATIVO = "inativo", "Inativo"

    nome = models.CharField("nome", max_length=150)
    cpf = models.CharField("CPF", max_length=14, unique=True)
    telefone = models.CharField("telefone", max_length=20, blank=True)
    email = models.EmailField("e-mail", blank=True)
    apartamento = models.CharField("apartamento", max_length=10)
    bloco = models.CharField("bloco", max_length=10)
    status = models.CharField(
        "status", max_length=10, choices=Status.choices, default=Status.ATIVO
    )

    class Meta:
        verbose_name = "morador"
        verbose_name_plural = "moradores"
        ordering = ["bloco", "apartamento", "nome"]

    def __str__(self):
        return f"{self.nome} (Bloco {self.bloco} - Ap. {self.apartamento})"


class Visitante(models.Model):
    nome = models.CharField("nome", max_length=150)
    documento = models.CharField("documento (RG/CPF)", max_length=30)
    telefone = models.CharField("telefone", max_length=20, blank=True)
    data_entrada = models.DateTimeField("entrada", auto_now_add=True)
    data_saida = models.DateTimeField("saída", null=True, blank=True)
    motivo = models.CharField("motivo", max_length=200, blank=True)
    morador = models.ForeignKey(
        Morador,
        on_delete=models.PROTECT,
        related_name="visitantes",
        verbose_name="morador visitado",
    )

    class Meta:
        verbose_name = "visitante"
        verbose_name_plural = "visitantes"
        ordering = ["-data_entrada"]

    def __str__(self):
        return f"{self.nome} → {self.morador.bloco}/{self.morador.apartamento}"

    @property
    def presente(self):
        """True enquanto o visitante não tiver saída registrada."""
        return self.data_saida is None

    def clean(self):
        if self.data_saida and self.data_entrada and self.data_saida < self.data_entrada:
            raise ValidationError(
                {"data_saida": "A saída não pode ser anterior à entrada."}
            )


class Encomenda(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        RETIRADA = "retirada", "Retirada"

    descricao = models.CharField("descrição", max_length=200)
    transportadora = models.CharField("transportadora", max_length=100, blank=True)
    codigo_rastreio = models.CharField("código de rastreio", max_length=50, blank=True)
    data_recebimento = models.DateTimeField("recebida em", auto_now_add=True)
    data_retirada = models.DateTimeField("retirada em", null=True, blank=True)
    status = models.CharField(
        "status", max_length=10, choices=Status.choices, default=Status.PENDENTE
    )
    morador = models.ForeignKey(
        Morador,
        on_delete=models.PROTECT,
        related_name="encomendas",
        verbose_name="morador destinatário",
    )
    nome_retirou = models.CharField("retirada por (nome)", max_length=150, blank=True)
    documento_retirou = models.CharField(
        "retirada por (RG/CPF)", max_length=30, blank=True
    )

    class Meta:
        verbose_name = "encomenda"
        verbose_name_plural = "encomendas"
        ordering = ["-data_recebimento"]

    def __str__(self):
        return (
            f"{self.descricao} → {self.morador.bloco}/{self.morador.apartamento} "
            f"({self.get_status_display()})"
        )

    def clean(self):
        if self.status == self.Status.RETIRADA:
            erros = {}
            if not self.nome_retirou:
                erros["nome_retirou"] = "Informe quem retirou a encomenda."
            if not self.documento_retirou:
                erros["documento_retirou"] = "Informe o documento de quem retirou."
            if not self.data_retirada:
                erros["data_retirada"] = "Informe a data e hora da retirada."
            if erros:
                raise ValidationError(erros)
        if (
            self.data_retirada
            and self.data_recebimento
            and self.data_retirada < self.data_recebimento
        ):
            raise ValidationError(
                {"data_retirada": "A retirada não pode ser anterior ao recebimento."}
            )
