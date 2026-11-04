from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Moradores
    path("moradores/", views.MoradorListView.as_view(), name="morador_list"),
    path("moradores/novo/", views.MoradorCreateView.as_view(), name="morador_create"),
    path("moradores/<int:pk>/editar/", views.MoradorUpdateView.as_view(), name="morador_update"),
    path("moradores/<int:pk>/excluir/", views.MoradorDeleteView.as_view(), name="morador_delete"),
    # Visitantes
    path("visitantes/", views.VisitanteListView.as_view(), name="visitante_list"),
    path("visitantes/entrada/", views.VisitanteCreateView.as_view(), name="visitante_create"),
    path("visitantes/<int:pk>/saida/", views.VisitanteSaidaView.as_view(), name="visitante_saida"),
    # Encomendas
    path("encomendas/", views.EncomendaListView.as_view(), name="encomenda_list"),
    path("encomendas/chegada/", views.EncomendaCreateView.as_view(), name="encomenda_create"),
    path("encomendas/<int:pk>/baixa/", views.EncomendaBaixaView.as_view(), name="encomenda_baixa"),
]
