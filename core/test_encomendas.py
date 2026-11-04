from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Encomenda, Morador, Visitante


class EncomendaTestBase(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("porteiro.teste"))
        self.ana = Morador.objects.create(
            nome="Ana Fictícia", cpf="000.000.000-01", bloco="A", apartamento="101"
        )
        self.bruno = Morador.objects.create(
            nome="Bruno Exemplo", cpf="000.000.000-02", bloco="B", apartamento="202"
        )
        self.pendente = Encomenda.objects.create(
            descricao="Caixa pequena", transportadora="Correios",
            codigo_rastreio="TESTE000001BR", morador=self.ana,
        )
        self.retirada = Encomenda.objects.create(descricao="Envelope", morador=self.bruno)
        Encomenda.objects.filter(pk=self.retirada.pk).update(
            status=Encomenda.Status.RETIRADA,
            data_retirada=timezone.now(),
            nome_retirou="Pessoa Fictícia",
            documento_retirou="TESTE-R1",
        )
        self.retirada.refresh_from_db()
        self.url_baixa = reverse("encomenda_baixa", args=[self.pendente.pk])


class BaixaEncomendaTest(EncomendaTestBase):
    def test_formulario_de_baixa(self):
        resp = self.client.get(self.url_baixa)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Caixa pequena")
        self.assertContains(resp, 'for="id_nome_retirou"')
        self.assertContains(resp, 'for="id_documento_retirou"')
        self.assertContains(resp, 'name="csrfmiddlewaretoken"')

    def test_baixa_valida_muda_status_e_preenche_data(self):
        antes = timezone.now()
        resp = self.client.post(
            self.url_baixa,
            {"nome_retirou": "Ana Fictícia", "documento_retirou": "TESTE-R2"},
            follow=True,
        )
        self.assertRedirects(resp, reverse("encomenda_list"))
        self.assertContains(resp, "Baixa registrada: Caixa pequena retirada por Ana Fictícia.")
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.status, Encomenda.Status.RETIRADA)
        self.assertEqual(self.pendente.nome_retirou, "Ana Fictícia")
        self.assertEqual(self.pendente.documento_retirou, "TESTE-R2")
        self.assertGreaterEqual(self.pendente.data_retirada, antes)
        self.pendente.full_clean()  # registro final é válido

    def test_baixa_sem_campos_obrigatorios(self):
        resp = self.client.post(self.url_baixa, {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Informe quem retirou a encomenda.")
        self.assertContains(resp, "Informe o documento de quem retirou.")
        self.assertContains(resp, "is-invalid")
        self._assert_continua_pendente()

    def test_baixa_sem_documento(self):
        resp = self.client.post(self.url_baixa, {"nome_retirou": "Ana Fictícia"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(list(resp.context["form"].errors), ["documento_retirou"])
        self._assert_continua_pendente()

    def test_baixa_sem_nome(self):
        resp = self.client.post(self.url_baixa, {"documento_retirou": "TESTE-R2"})
        self.assertEqual(list(resp.context["form"].errors), ["nome_retirou"])
        self._assert_continua_pendente()

    def test_baixa_somente_com_espacos_e_recusada(self):
        resp = self.client.post(self.url_baixa, {"nome_retirou": "   ", "documento_retirou": "  "})
        self.assertEqual(set(resp.context["form"].errors), {"nome_retirou", "documento_retirou"})
        self._assert_continua_pendente()

    def test_baixa_de_encomenda_ja_retirada_e_bloqueada(self):
        url = reverse("encomenda_baixa", args=[self.retirada.pk])
        original = self.retirada.data_retirada
        for metodo in (self.client.get, self.client.post):
            with self.subTest(metodo=metodo.__name__):
                resp = metodo(url, {"nome_retirou": "Outra", "documento_retirou": "X"}, follow=True)
                self.assertRedirects(resp, reverse("encomenda_list"))
                self.assertContains(resp, "Esta encomenda já foi retirada.")
        self.retirada.refresh_from_db()
        self.assertEqual(self.retirada.nome_retirou, "Pessoa Fictícia")
        self.assertEqual(self.retirada.data_retirada, original)

    def test_baixa_de_encomenda_inexistente(self):
        resp = self.client.get(reverse("encomenda_baixa", args=[9999]))
        self.assertEqual(resp.status_code, 404)

    def test_baixa_exige_login(self):
        self.client.logout()
        resp = self.client.post(self.url_baixa, {"nome_retirou": "X", "documento_retirou": "Y"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith(reverse("login")))
        self._assert_continua_pendente()

    def _assert_continua_pendente(self):
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.status, Encomenda.Status.PENDENTE)
        self.assertIsNone(self.pendente.data_retirada)


class EncomendaViewsTest(EncomendaTestBase):
    def test_lista_separa_pendentes_e_historico(self):
        resp = self.client.get(reverse("encomenda_list"))
        self.assertEqual(list(resp.context["pendentes"]), [self.pendente])
        self.assertEqual(list(resp.context["encomenda_list"]), [self.retirada])
        self.assertContains(resp, "Dar baixa")
        self.assertContains(resp, "Pessoa Fictícia")

    def test_busca_por_rastreio_e_apartamento(self):
        resp = self.client.get(reverse("encomenda_list"), {"q": "TESTE000001"})
        self.assertEqual(list(resp.context["pendentes"]), [self.pendente])
        self.assertEqual(list(resp.context["encomenda_list"]), [])
        resp = self.client.get(reverse("encomenda_list"), {"q": "202"})
        self.assertEqual(list(resp.context["pendentes"]), [])
        self.assertEqual(list(resp.context["encomenda_list"]), [self.retirada])

    def test_registra_chegada_como_pendente(self):
        resp = self.client.post(
            reverse("encomenda_create"),
            {"morador": self.bruno.pk, "descricao": "Caixa média", "transportadora": "Exemplo"},
            follow=True,
        )
        self.assertRedirects(resp, reverse("encomenda_list"))
        self.assertContains(resp, "Chegada de encomenda (Caixa média) registrada.")
        e = Encomenda.objects.get(descricao="Caixa média")
        self.assertEqual(e.status, Encomenda.Status.PENDENTE)
        self.assertIsNotNone(e.data_recebimento)
        self.assertIsNone(e.data_retirada)

    def test_chegada_exige_morador_e_descricao(self):
        resp = self.client.post(reverse("encomenda_create"), {})
        self.assertEqual(set(resp.context["form"].errors), {"morador", "descricao"})

    def test_chegada_pre_seleciona_morador_e_lista_so_ativos(self):
        self.bruno.status = Morador.Status.INATIVO
        self.bruno.save()
        resp = self.client.get(reverse("encomenda_create"), {"morador": self.ana.pk})
        form = resp.context["form"]
        self.assertEqual(form.initial["morador"], str(self.ana.pk))
        self.assertEqual(list(form.fields["morador"].queryset), [self.ana])


class DashboardTest(EncomendaTestBase):
    def test_cards_e_ultimos_registros(self):
        hoje = Visitante.objects.create(nome="Visitante Hoje", documento="TESTE-1", morador=self.ana)
        ontem = Visitante.objects.create(nome="Visitante Ontem", documento="TESTE-2", morador=self.ana)
        Visitante.objects.filter(pk=ontem.pk).update(
            data_entrada=timezone.now() - timedelta(days=1),
            data_saida=timezone.now() - timedelta(days=1) + timedelta(hours=1),
        )
        resp = self.client.get(reverse("dashboard"))
        ctx = resp.context
        self.assertEqual(ctx["visitantes_presentes"], 1)
        self.assertEqual(ctx["visitantes_hoje"], 1)
        self.assertEqual(ctx["encomendas_pendentes"], 1)
        self.assertEqual(list(ctx["ultimos_visitantes"])[0], hoje)
        self.assertIn(self.pendente, list(ctx["ultimas_encomendas"]))
        self.assertContains(resp, "Visitantes presentes agora")
        self.assertContains(resp, "Visitantes hoje")
        self.assertContains(resp, "Encomendas pendentes")
        self.assertContains(resp, reverse("encomenda_baixa", args=[self.pendente.pk]))

    def test_ultimos_registros_limitados_a_cinco(self):
        for i in range(7):
            Encomenda.objects.create(descricao=f"Pacote {i}", morador=self.ana)
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(len(resp.context["ultimas_encomendas"]), 5)
        self.assertEqual(resp.context["encomendas_pendentes"], 8)

    def test_baixa_atualiza_contador_de_pendentes(self):
        self.client.post(self.url_baixa, {"nome_retirou": "Ana", "documento_retirou": "TESTE-R3"})
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.context["encomendas_pendentes"], 0)
