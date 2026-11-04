from django.contrib import admin

from .models import Encomenda, Morador, Visitante


@admin.register(Morador)
class MoradorAdmin(admin.ModelAdmin):
    list_display = ("nome", "bloco", "apartamento", "telefone", "email", "status")
    list_filter = ("status", "bloco")
    search_fields = ("nome", "cpf", "apartamento", "bloco", "email")


@admin.register(Visitante)
class VisitanteAdmin(admin.ModelAdmin):
    list_display = ("nome", "documento", "morador", "data_entrada", "data_saida", "presente")
    list_filter = ("data_entrada", "morador__bloco")
    search_fields = ("nome", "documento", "morador__nome", "morador__apartamento")
    autocomplete_fields = ("morador",)
    date_hierarchy = "data_entrada"

    @admin.display(boolean=True, description="no condomínio")
    def presente(self, obj):
        return obj.presente


@admin.register(Encomenda)
class EncomendaAdmin(admin.ModelAdmin):
    list_display = (
        "descricao",
        "morador",
        "transportadora",
        "status",
        "data_recebimento",
        "data_retirada",
        "nome_retirou",
    )
    list_filter = ("status", "transportadora", "data_recebimento")
    search_fields = (
        "descricao",
        "codigo_rastreio",
        "morador__nome",
        "morador__apartamento",
        "nome_retirou",
    )
    autocomplete_fields = ("morador",)
    date_hierarchy = "data_recebimento"
