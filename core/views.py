from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    BaixaEncomendaForm,
    EncomendaForm,
    LoginForm,
    MoradorForm,
    VisitanteForm,
)
from .models import Encomenda, Morador, Visitante

# Todas as views (exceto login) são protegidas pelo LoginRequiredMiddleware.


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    ULTIMOS = 5

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoje = timezone.localdate()  # dia no fuso America/Sao_Paulo
        visitantes = Visitante.objects.select_related("morador")
        encomendas = Encomenda.objects.select_related("morador")
        ctx.update(
            visitantes_presentes=visitantes.filter(data_saida__isnull=True).count(),
            visitantes_hoje=visitantes.filter(data_entrada__date=hoje).count(),
            encomendas_pendentes=encomendas.filter(status=Encomenda.Status.PENDENTE).count(),
            ultimos_visitantes=visitantes.order_by("-data_entrada")[: self.ULTIMOS],
            ultimas_encomendas=encomendas.order_by("-data_recebimento")[: self.ULTIMOS],
        )
        return ctx


class BuscaMixin:
    """Filtra o queryset pelo parâmetro ?q= nos campos de `search_fields`."""

    search_fields = ()

    def get_busca(self):
        return self.request.GET.get("q", "").strip()

    def filtrar(self, queryset):
        termo = self.get_busca()
        if termo:
            filtro = Q()
            for campo in self.search_fields:
                filtro |= Q(**{f"{campo}__icontains": termo})
            queryset = queryset.filter(filtro)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.get_busca()
        return ctx


# ---------- Moradores ----------


class MoradorListView(BuscaMixin, ListView):
    model = Morador
    paginate_by = 20
    search_fields = ("nome", "apartamento", "bloco")

    def get_queryset(self):
        return self.filtrar(super().get_queryset())


class MoradorCreateView(SuccessMessageMixin, CreateView):
    model = Morador
    form_class = MoradorForm
    success_url = reverse_lazy("morador_list")
    success_message = "Morador %(nome)s cadastrado."


class MoradorUpdateView(SuccessMessageMixin, UpdateView):
    model = Morador
    form_class = MoradorForm
    success_url = reverse_lazy("morador_list")
    success_message = "Morador %(nome)s atualizado."


class MoradorDeleteView(DeleteView):
    model = Morador
    success_url = reverse_lazy("morador_list")

    def form_valid(self, form):
        nome = self.object.nome
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f"{nome} possui visitas ou encomendas registradas e não pode ser excluído. "
                "Altere o status para Inativo.",
            )
            return redirect("morador_update", pk=self.object.pk)
        messages.success(self.request, f"Morador {nome} excluído.")
        return response


# ---------- Visitantes ----------


class VisitanteListView(BuscaMixin, ListView):
    """Histórico paginado (com saída) + lista de quem está presente agora."""

    model = Visitante
    paginate_by = 20
    search_fields = ("nome", "documento", "morador__nome", "morador__apartamento", "morador__bloco")

    def get_queryset(self):
        qs = Visitante.objects.select_related("morador").filter(data_saida__isnull=False)
        return self.filtrar(qs).order_by("-data_saida")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        presentes = Visitante.objects.select_related("morador").filter(data_saida__isnull=True)
        ctx["presentes"] = self.filtrar(presentes)
        return ctx


class VisitanteCreateView(SuccessMessageMixin, CreateView):
    model = Visitante
    form_class = VisitanteForm
    success_url = reverse_lazy("visitante_list")
    success_message = "Entrada de %(nome)s registrada."

    def get_initial(self):
        initial = super().get_initial()
        morador = self.request.GET.get("morador")
        if morador and morador.isdigit():
            initial["morador"] = morador
        return initial


class VisitanteSaidaView(View):
    """Ação rápida: registra a saída do visitante (somente POST)."""

    http_method_names = ["post"]

    def post(self, request, pk):
        visitante = get_object_or_404(Visitante, pk=pk)
        if visitante.data_saida:
            messages.warning(request, f"A saída de {visitante.nome} já havia sido registrada.")
        else:
            visitante.data_saida = timezone.now()
            visitante.save(update_fields=["data_saida"])
            messages.success(request, f"Saída de {visitante.nome} registrada.")

        destino = request.POST.get("next")
        if not url_has_allowed_host_and_scheme(
            destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            destino = reverse("visitante_list")
        return redirect(destino)


# ---------- Encomendas ----------


class EncomendaListView(BuscaMixin, ListView):
    """Histórico paginado (retiradas) + lista de pendentes."""

    model = Encomenda
    paginate_by = 20
    search_fields = (
        "descricao",
        "transportadora",
        "codigo_rastreio",
        "nome_retirou",
        "morador__nome",
        "morador__apartamento",
        "morador__bloco",
    )

    def get_queryset(self):
        qs = Encomenda.objects.select_related("morador").filter(status=Encomenda.Status.RETIRADA)
        return self.filtrar(qs).order_by("-data_retirada")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pendentes = Encomenda.objects.select_related("morador").filter(
            status=Encomenda.Status.PENDENTE
        )
        ctx["pendentes"] = self.filtrar(pendentes)
        return ctx


class EncomendaCreateView(SuccessMessageMixin, CreateView):
    model = Encomenda
    form_class = EncomendaForm
    success_url = reverse_lazy("encomenda_list")
    success_message = "Chegada de encomenda (%(descricao)s) registrada."

    def get_initial(self):
        initial = super().get_initial()
        morador = self.request.GET.get("morador")
        if morador and morador.isdigit():
            initial["morador"] = morador
        return initial


class EncomendaBaixaView(UpdateView):
    """Baixa da encomenda: registra quem retirou, status e data/hora."""

    model = Encomenda
    form_class = BaixaEncomendaForm
    template_name = "core/encomenda_baixa.html"
    success_url = reverse_lazy("encomenda_list")

    def dispatch(self, request, *args, **kwargs):
        encomenda = get_object_or_404(Encomenda, pk=kwargs["pk"])
        if encomenda.status == Encomenda.Status.RETIRADA:
            messages.warning(request, "Esta encomenda já foi retirada.")
            return redirect("encomenda_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Baixa registrada: {self.object.descricao} retirada por {self.object.nome_retirou}.",
        )
        return response
