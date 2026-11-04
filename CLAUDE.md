# CondoPort

Sistema web acadêmico (UNIVESP, PJI240) para gestão de visitantes e encomendas em portaria condominial.

## Stack
- Python 3.12+, Django (versão LTS atual), templates Django + Bootstrap 5 (CDN) + JavaScript simples
- Banco: SQLite em desenvolvimento, PostgreSQL em produção (via `DATABASE_URL` e `dj-database-url`)
- Deploy: Render (gunicorn + whitenoise). Controle de versão: GitHub

## Escopo do MVP
- Um único tipo de usuário: o porteiro (operador). Ele faz login e registra tudo.
- Moradores/unidades: cadastro e consulta.
- Visitantes: o porteiro registra entrada e saída, vinculando ao morador/apartamento visitado.
- Encomendas: o porteiro registra a chegada e dá baixa informando nome e RG/CPF de quem retirou, com data e hora.
- Fora do escopo: biometria, catracas, pagamentos, notificações (futuro).

## Modelos (app `core`)
- **Morador:** nome, cpf, telefone, email, apartamento, bloco, status (ativo/inativo)
- **Visitante:** nome, documento, telefone, data_entrada (auto), data_saida (opcional), motivo, morador (FK)
- **Encomenda:** descricao, transportadora, codigo_rastreio, data_recebimento (auto), data_retirada (opcional), status (pendente/retirada), morador (FK), nome_retirou, documento_retirou

## Regras
- Interface e textos em português do Brasil; código e nomes de variáveis em inglês ou português, mas consistente.
- Nunca commitar `.env`, senhas ou dados reais. Usar apenas dados fictícios em seeds e demonstrações (LGPD).
- Todas as telas exigem login. Validar entradas e usar proteção CSRF do Django.
- Acessibilidade básica: labels nos campos, contraste, navegação por teclado.
- Escrever testes para models e views principais. Commits pequenos, mensagens claras.
- Antes de grandes mudanças, explique o plano em poucas linhas.