from datetime import timedelta
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
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
