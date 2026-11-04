"""Popula o banco com dados FICTÍCIOS para testes e demonstrações.

Todos os dados são inventados e claramente falsos (LGPD):
- CPFs no formato 000.000.000-XX (inválidos de propósito)
- documentos com prefixo "TESTE-"
- e-mails no domínio reservado exemplo.com.br
- telefones (00) 00000-XXXX
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Encomenda, Morador, Visitante

PREFIXO_CPF_FICTICIO = "000.000.000-"

MORADORES = [
    ("Ana Fictícia Teste", "A", "101"),
    ("Bruno Exemplo Silva", "A", "102"),
    ("Carla Demonstração Souza", "A", "201"),
    ("Daniel Teste Oliveira", "B", "101"),
    ("Elisa Fictícia Lima", "B", "202"),
    ("Fábio Exemplo Costa", "B", "301"),
    ("Gabriela Teste Rocha", "C", "102"),
    ("Henrique Fictício Alves", "C", "203", Morador.Status.INATIVO),
]

VISITANTES = [
    # (nome, morador_idx, motivo, horas_atras_entrada, horas_ate_saida ou None)
    ("Visitante Teste Um", 0, "Visita familiar", 5, 2),
    ("Visitante Teste Dois", 1, "Entrega de móveis", 3, None),
    ("Técnico Fictício Net", 3, "Manutenção de internet", 26, 1),
    ("Visitante Teste Quatro", 4, "Visita social", 1, None),
    ("Diarista Exemplo", 6, "Prestação de serviço", 30, 8),
]

ENCOMENDAS = [
    # (descricao, transportadora, morador_idx, horas_atras, retirada_por ou None)
    ("Caixa pequena", "Correios", 0, 48, "Ana Fictícia Teste"),
    ("Envelope", "Transportadora Exemplo", 1, 20, None),
    ("Caixa média", "Entregas Fictícias Ltda", 2, 6, None),
    ("Pacote de livros", "Correios", 3, 72, "Parente Fictício"),
    ("Caixa grande", "Transportadora Exemplo", 5, 2, None),
]


class Command(BaseCommand):
    help = "Popula o banco com moradores, visitantes e encomendas FICTÍCIOS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Apaga os dados fictícios criados por este comando antes de popular.",
        )

    @transaction.atomic
    def handle(self, *args, limpar=False, **options):
        ficticios = Morador.objects.filter(cpf__startswith=PREFIXO_CPF_FICTICIO)

        if limpar:
            Visitante.objects.filter(morador__in=ficticios).delete()
            Encomenda.objects.filter(morador__in=ficticios).delete()
            total, _ = ficticios.delete()
            self.stdout.write(f"Dados fictícios anteriores removidos ({total} moradores).")
        elif ficticios.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Dados fictícios já existem. Use --limpar para recriá-los."
                )
            )
            return

        agora = timezone.now()

        moradores = []
        for i, item in enumerate(MORADORES, start=1):
            nome, bloco, ap, *resto = item
            moradores.append(
                Morador.objects.create(
                    nome=nome,
                    cpf=f"{PREFIXO_CPF_FICTICIO}{i:02d}",
                    telefone=f"(00) 00000-{i:04d}",
                    email=f"morador{i:02d}@exemplo.com.br",
                    bloco=bloco,
                    apartamento=ap,
                    status=resto[0] if resto else Morador.Status.ATIVO,
                )
            )

        for i, (nome, idx, motivo, h_entrada, h_saida) in enumerate(VISITANTES, start=1):
            v = Visitante.objects.create(
                nome=nome,
                documento=f"TESTE-V{i:04d}",
                telefone=f"(00) 00000-9{i:03d}",
                motivo=motivo,
                morador=moradores[idx],
            )
            # data_entrada é auto_now_add; ajusta via update para simular histórico.
            entrada = agora - timedelta(hours=h_entrada)
            saida = entrada + timedelta(hours=h_saida) if h_saida is not None else None
            Visitante.objects.filter(pk=v.pk).update(data_entrada=entrada, data_saida=saida)

        for i, (descricao, transp, idx, h_receb, retirou) in enumerate(ENCOMENDAS, start=1):
            e = Encomenda.objects.create(
                descricao=descricao,
                transportadora=transp,
                codigo_rastreio=f"TESTE{i:06d}BR",
                morador=moradores[idx],
            )
            recebimento = agora - timedelta(hours=h_receb)
            campos = {"data_recebimento": recebimento}
            if retirou:
                campos.update(
                    status=Encomenda.Status.RETIRADA,
                    data_retirada=recebimento + timedelta(hours=3),
                    nome_retirou=retirou,
                    documento_retirou=f"TESTE-R{i:04d}",
                )
            Encomenda.objects.filter(pk=e.pk).update(**campos)

        self.stdout.write(
            self.style.SUCCESS(
                f"Criados {len(moradores)} moradores, {len(VISITANTES)} visitantes "
                f"e {len(ENCOMENDAS)} encomendas fictícios."
            )
        )
