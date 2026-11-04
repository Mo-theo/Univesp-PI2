from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Encomenda, Morador, Visitante


class ViewTestBase(TestCase):
    """Usuário logado e dados fictícios básicos."""

    def setUp(self):
        user = get_user_model().objects.create_user("porteiro.teste")
        self.client.force_login(user)
        self.ana = Morador.objects.create(
            nome="Ana Fictícia", cpf="000.000.000-01", bloco="A", apartamento="101"
        )
        self.bruno = Morador.objects.create(
            nome="Bruno Exemplo", cpf="000.000.000-02", bloco="B", apartamento="202"
        )


class ProtecaoLoginTest(TestCase):
    def test_paginas_exigem_login(self):
        urls = [
            reverse("morador_list"),
            reverse("morador_create"),
            reverse("morador_update", args=[1]),
            reverse("morador_delete", args=[1]),
            reverse("visitante_list"),
            reverse("visitante_create"),
        ]
        for url in urls:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertRedirects(resp, f"{reverse('login')}?next={url}", fetch_redirect_response=False)

    def test_saida_exige_login(self):
        resp = self.client.post(reverse("visitante_saida", args=[1]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith(reverse("login")))


class DashboardViewTest(ViewTestBase):
    def test_mostra_contadores_e_navbar(self):
        Visitante.objects.create(nome="V", documento="TESTE-1", morador=self.ana)
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.context["visitantes_presentes"], 1)
        self.assertEqual(resp.context["moradores_ativos"], 2)
        self.assertContains(resp, 'href="/moradores/"')
        self.assertContains(resp, 'href="/visitantes/"')


class MoradorViewsTest(ViewTestBase):
    def test_lista(self):
        resp = self.client.get(reverse("morador_list"))
        self.assertContains(resp, "Ana Fictícia")
        self.assertContains(resp, "Bruno Exemplo")
        self.assertContains(resp, 'aria-current="page"')

    def test_busca_por_nome(self):
        resp = self.client.get(reverse("morador_list"), {"q": "ana"})
        self.assertContains(resp, "Ana Fictícia")
        self.assertNotContains(resp, "Bruno Exemplo")

    def test_busca_por_apartamento(self):
        resp = self.client.get(reverse("morador_list"), {"q": "202"})
        self.assertContains(resp, "Bruno Exemplo")
        self.assertNotContains(resp, "Ana Fictícia")

    def test_formulario_tem_labels(self):
        resp = self.client.get(reverse("morador_create"))
        self.assertContains(resp, 'for="id_nome"')
        self.assertContains(resp, 'for="id_cpf"')
        self.assertContains(resp, 'name="csrfmiddlewaretoken"')

    def test_cria_morador_e_formata_cpf(self):
        resp = self.client.post(
            reverse("morador_create"),
            {
                "nome": "Carla Teste",
                "cpf": "00000000003",
                "bloco": "C",
                "apartamento": "303",
                "status": "ativo",
            },
            follow=True,
        )
        self.assertRedirects(resp, reverse("morador_list"))
        self.assertContains(resp, "Morador Carla Teste cadastrado.")
        self.assertEqual(Morador.objects.get(nome="Carla Teste").cpf, "000.000.000-03")

    def test_cpf_invalido_ou_duplicado(self):
        dados = {"nome": "X", "bloco": "C", "apartamento": "1", "status": "ativo"}
        resp = self.client.post(reverse("morador_create"), {**dados, "cpf": "123"})
        self.assertContains(resp, "O CPF deve ter 11 dígitos.")
        self.assertContains(resp, "is-invalid")
        resp = self.client.post(reverse("morador_create"), {**dados, "cpf": "00000000001"})
        self.assertContains(resp, "Já existe um morador com este CPF.")

    def test_edita_morador(self):
        resp = self.client.post(
            reverse("morador_update", args=[self.ana.pk]),
            {
                "nome": "Ana Fictícia",
                "cpf": self.ana.cpf,
                "bloco": "A",
                "apartamento": "102",
                "status": "inativo",
            },
        )
        self.assertRedirects(resp, reverse("morador_list"))
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.apartamento, "102")
        self.assertEqual(self.ana.status, Morador.Status.INATIVO)

    def test_exclui_morador_sem_registros(self):
        resp = self.client.get(reverse("morador_delete", args=[self.bruno.pk]))
        self.assertContains(resp, "Tem certeza")
        resp = self.client.post(reverse("morador_delete", args=[self.bruno.pk]))
        self.assertRedirects(resp, reverse("morador_list"))
        self.assertFalse(Morador.objects.filter(pk=self.bruno.pk).exists())

    def test_nao_exclui_morador_com_registros(self):
        Encomenda.objects.create(descricao="Caixa", morador=self.ana)
        resp = self.client.post(reverse("morador_delete", args=[self.ana.pk]), follow=True)
        self.assertRedirects(resp, reverse("morador_update", args=[self.ana.pk]))
        self.assertContains(resp, "não pode ser excluído")
        self.assertTrue(Morador.objects.filter(pk=self.ana.pk).exists())


class VisitanteViewsTest(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.presente = Visitante.objects.create(
            nome="Visitante Presente", documento="TESTE-1", morador=self.ana
        )
        self.saiu = Visitante.objects.create(
            nome="Visitante Antigo", documento="TESTE-2", morador=self.bruno
        )
        Visitante.objects.filter(pk=self.saiu.pk).update(data_saida=self.saiu.data_entrada)

    def test_lista_separa_presentes_e_historico(self):
        resp = self.client.get(reverse("visitante_list"))
        self.assertEqual(list(resp.context["presentes"]), [self.presente])
        self.assertEqual(list(resp.context["visitante_list"]), [self.saiu])
        self.assertContains(resp, "Registrar saída")

    def test_busca_por_apartamento_do_morador(self):
        resp = self.client.get(reverse("visitante_list"), {"q": "202"})
        self.assertEqual(list(resp.context["presentes"]), [])
        self.assertEqual(list(resp.context["visitante_list"]), [self.saiu])

    def test_busca_por_nome_do_visitante(self):
        resp = self.client.get(reverse("visitante_list"), {"q": "presente"})
        self.assertEqual(list(resp.context["presentes"]), [self.presente])
        self.assertEqual(list(resp.context["visitante_list"]), [])

    def test_formulario_pre_seleciona_morador(self):
        resp = self.client.get(reverse("visitante_create"), {"morador": self.ana.pk})
        self.assertEqual(resp.context["form"].initial["morador"], str(self.ana.pk))
        self.assertContains(resp, 'for="id_morador"')

    def test_formulario_lista_somente_moradores_ativos(self):
        self.bruno.status = Morador.Status.INATIVO
        self.bruno.save()
        resp = self.client.get(reverse("visitante_create"))
        self.assertEqual(list(resp.context["form"].fields["morador"].queryset), [self.ana])

    def test_registra_entrada(self):
        resp = self.client.post(
            reverse("visitante_create"),
            {"morador": self.ana.pk, "nome": "Novo Visitante", "documento": "TESTE-3"},
            follow=True,
        )
        self.assertRedirects(resp, reverse("visitante_list"))
        self.assertContains(resp, "Entrada de Novo Visitante registrada.")
        v = Visitante.objects.get(nome="Novo Visitante")
        self.assertIsNotNone(v.data_entrada)
        self.assertIsNone(v.data_saida)

    def test_entrada_exige_campos_obrigatorios(self):
        resp = self.client.post(reverse("visitante_create"), {})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["form"].errors)
        self.assertEqual(Visitante.objects.count(), 2)

    def test_registra_saida(self):
        resp = self.client.post(reverse("visitante_saida", args=[self.presente.pk]), follow=True)
        self.assertRedirects(resp, reverse("visitante_list"))
        self.assertContains(resp, "Saída de Visitante Presente registrada.")
        self.presente.refresh_from_db()
        self.assertIsNotNone(self.presente.data_saida)

    def test_saida_repetida_nao_altera_data(self):
        original = Visitante.objects.get(pk=self.saiu.pk).data_saida
        resp = self.client.post(reverse("visitante_saida", args=[self.saiu.pk]), follow=True)
        self.assertContains(resp, "já havia sido registrada")
        self.assertEqual(Visitante.objects.get(pk=self.saiu.pk).data_saida, original)

    def test_saida_aceita_somente_post(self):
        resp = self.client.get(reverse("visitante_saida", args=[self.presente.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_saida_volta_para_next_seguro(self):
        url = reverse("visitante_list") + "?q=ana"
        resp = self.client.post(reverse("visitante_saida", args=[self.presente.pk]), {"next": url})
        self.assertRedirects(resp, url)

    def test_saida_ignora_next_externo(self):
        resp = self.client.post(
            reverse("visitante_saida", args=[self.presente.pk]), {"next": "https://exemplo.com/"}
        )
        self.assertRedirects(resp, reverse("visitante_list"))

    def test_saida_de_visitante_inexistente(self):
        resp = self.client.post(reverse("visitante_saida", args=[9999]))
        self.assertEqual(resp.status_code, 404)
