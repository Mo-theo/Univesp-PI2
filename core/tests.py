from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Encomenda, Morador, Visitante


def criar_morador(**kwargs):
    dados = {
        "nome": "Morador Teste",
        "cpf": "000.000.000-99",
        "apartamento": "101",
        "bloco": "A",
    }
    dados.update(kwargs)
    return Morador.objects.create(**dados)


class MoradorModelTest(TestCase):
    def test_str_e_status_padrao(self):
        m = criar_morador()
        self.assertEqual(str(m), "Morador Teste (Bloco A - Ap. 101)")
        self.assertEqual(m.status, Morador.Status.ATIVO)

    def test_cpf_unico(self):
        criar_morador()
        with self.assertRaises(IntegrityError):
            criar_morador(nome="Outro")

    def test_ordenacao_por_bloco_e_apartamento(self):
        criar_morador(cpf="000.000.000-91", bloco="B", apartamento="101")
        criar_morador(cpf="000.000.000-92", bloco="A", apartamento="202")
        criar_morador(cpf="000.000.000-93", bloco="A", apartamento="101")
        ordem = [(m.bloco, m.apartamento) for m in Morador.objects.all()]
        self.assertEqual(ordem, [("A", "101"), ("A", "202"), ("B", "101")])

    def test_nao_apaga_morador_com_registros(self):
        m = criar_morador()
        Visitante.objects.create(nome="V", documento="TESTE-1", morador=m)
        with self.assertRaises(ProtectedError):
            m.delete()


class VisitanteModelTest(TestCase):
    def setUp(self):
        self.morador = criar_morador()

    def test_entrada_automatica_e_presente(self):
        v = Visitante.objects.create(nome="Visitante", documento="TESTE-1", morador=self.morador)
        self.assertIsNotNone(v.data_entrada)
        self.assertTrue(v.presente)
        self.assertEqual(str(v), "Visitante → A/101")

    def test_saida_registrada(self):
        v = Visitante.objects.create(nome="Visitante", documento="TESTE-1", morador=self.morador)
        v.data_saida = timezone.now()
        v.full_clean()
        self.assertFalse(v.presente)

    def test_saida_antes_da_entrada_invalida(self):
        v = Visitante.objects.create(nome="Visitante", documento="TESTE-1", morador=self.morador)
        v.data_saida = v.data_entrada - timedelta(hours=1)
        with self.assertRaises(ValidationError) as ctx:
            v.full_clean()
        self.assertIn("data_saida", ctx.exception.message_dict)


class EncomendaModelTest(TestCase):
    def setUp(self):
        self.morador = criar_morador()
        self.encomenda = Encomenda.objects.create(descricao="Caixa", morador=self.morador)

    def test_padroes_e_str(self):
        self.assertEqual(self.encomenda.status, Encomenda.Status.PENDENTE)
        self.assertIsNotNone(self.encomenda.data_recebimento)
        self.assertEqual(str(self.encomenda), "Caixa → A/101 (Pendente)")

    def test_retirada_exige_nome_documento_e_data(self):
        self.encomenda.status = Encomenda.Status.RETIRADA
        with self.assertRaises(ValidationError) as ctx:
            self.encomenda.full_clean()
        self.assertEqual(
            set(ctx.exception.message_dict),
            {"nome_retirou", "documento_retirou", "data_retirada"},
        )

    def test_retirada_valida(self):
        self.encomenda.status = Encomenda.Status.RETIRADA
        self.encomenda.nome_retirou = "Pessoa Fictícia"
        self.encomenda.documento_retirou = "TESTE-R1"
        self.encomenda.data_retirada = timezone.now()
        self.encomenda.full_clean()  # não deve levantar erro

    def test_retirada_antes_do_recebimento_invalida(self):
        self.encomenda.data_retirada = self.encomenda.data_recebimento - timedelta(hours=1)
        with self.assertRaises(ValidationError):
            self.encomenda.full_clean()


class PopularDadosTesteCommandTest(TestCase):
    def test_popula_somente_dados_ficticios(self):
        call_command("popular_dados_teste", stdout=StringIO())
        self.assertEqual(Morador.objects.count(), 8)
        self.assertEqual(Visitante.objects.count(), 5)
        self.assertEqual(Encomenda.objects.count(), 5)
        self.assertTrue(all(m.cpf.startswith("000.000.000-") for m in Morador.objects.all()))
        for e in Encomenda.objects.filter(status=Encomenda.Status.RETIRADA):
            e.full_clean()  # retiradas geradas são válidas

    def test_nao_duplica_e_limpar_recria(self):
        call_command("popular_dados_teste", stdout=StringIO())
        call_command("popular_dados_teste", stdout=StringIO())
        self.assertEqual(Morador.objects.count(), 8)
        call_command("popular_dados_teste", "--limpar", stdout=StringIO())
        self.assertEqual(Morador.objects.count(), 8)
        self.assertEqual(Visitante.objects.count(), 5)


# Senha usada só nos testes (banco de teste é descartado ao final).
SENHA_TESTE = "Senha-de-teste-123"


def criar_porteiro(**kwargs):
    dados = {"username": "porteiro.teste", "email": "porteiro.teste@exemplo.com.br"}
    dados.update(kwargs)
    return get_user_model().objects.create_user(password=SENHA_TESTE, **dados)


class AcessoTest(TestCase):
    def test_anonimo_redirecionado_ao_login(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertRedirects(resp, f"{reverse('login')}?next=/")

    def test_logado_acessa_dashboard(self):
        self.client.force_login(criar_porteiro())
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Painel da portaria")
        self.assertContains(resp, "Sair")

    def test_pagina_de_login_publica_com_labels_e_csrf(self):
        resp = self.client.get(reverse("login"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="csrfmiddlewaretoken"')
        self.assertContains(resp, '<label for="id_username" class="form-label">E-mail ou usuário</label>', html=True)
        self.assertContains(resp, '<label for="id_password" class="form-label">Senha</label>', html=True)
        self.assertContains(resp, 'id="id_username"')
        self.assertContains(resp, 'id="id_password"')
        self.assertContains(resp, "Entrar")

    def test_login_com_usuario_redireciona_ao_dashboard(self):
        criar_porteiro()
        resp = self.client.post(
            reverse("login"), {"username": "porteiro.teste", "password": SENHA_TESTE}
        )
        self.assertRedirects(resp, reverse("dashboard"))

    def test_login_com_email_sem_diferenciar_maiusculas(self):
        criar_porteiro()
        resp = self.client.post(
            reverse("login"),
            {"username": "Porteiro.Teste@Exemplo.com.br", "password": SENHA_TESTE},
        )
        self.assertRedirects(resp, reverse("dashboard"))

    def test_login_respeita_next(self):
        criar_porteiro()
        resp = self.client.post(
            reverse("login") + "?next=/",
            {"username": "porteiro.teste", "password": SENHA_TESTE, "next": "/"},
        )
        self.assertRedirects(resp, "/")

    def test_senha_errada_mostra_erro(self):
        criar_porteiro()
        resp = self.client.post(
            reverse("login"), {"username": "porteiro.teste", "password": "errada"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "E-mail/usuário ou senha incorretos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_por_post_volta_ao_login(self):
        self.client.force_login(criar_porteiro())
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("login"))
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_post_sem_csrf_e_rejeitado(self):
        criar_porteiro()
        client = Client(enforce_csrf_checks=True)
        resp = client.post(
            reverse("login"), {"username": "porteiro.teste", "password": SENHA_TESTE}
        )
        self.assertEqual(resp.status_code, 403)

    def test_logado_e_redirecionado_ao_abrir_login(self):
        self.client.force_login(criar_porteiro())
        resp = self.client.get(reverse("login"))
        self.assertRedirects(resp, reverse("dashboard"))


@mock.patch("core.management.commands.criar_porteiro_demo.config")
class CriarPorteiroDemoCommandTest(TestCase):
    def test_cria_porteiro_com_senha_do_ambiente(self, config):
        config.return_value = SENHA_TESTE
        call_command("criar_porteiro_demo", stdout=StringIO())
        user = get_user_model().objects.get(username="porteiro.demo")
        self.assertTrue(user.check_password(SENHA_TESTE))
        self.assertTrue(user.email.endswith("@exemplo.com.br"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_rodar_de_novo_atualiza_senha(self, config):
        config.return_value = SENHA_TESTE
        call_command("criar_porteiro_demo", stdout=StringIO())
        config.return_value = "Outra-senha-456"
        call_command("criar_porteiro_demo", stdout=StringIO())
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertTrue(get_user_model().objects.get().check_password("Outra-senha-456"))

    def test_senha_fraca_recusada(self, config):
        config.return_value = "123"
        with self.assertRaises(CommandError):
            call_command("criar_porteiro_demo", stdout=StringIO())
        self.assertFalse(get_user_model().objects.exists())

    @mock.patch("sys.stdin")
    def test_sem_senha_e_sem_terminal_falha(self, stdin, config):
        config.return_value = ""
        stdin.isatty.return_value = False
        with self.assertRaises(CommandError):
            call_command("criar_porteiro_demo", stdout=StringIO())
