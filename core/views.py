from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from .forms import LoginForm


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class DashboardView(TemplateView):
    # Protegida pelo LoginRequiredMiddleware. Conteúdo real vem nas próximas etapas.
    template_name = "core/dashboard.html"
