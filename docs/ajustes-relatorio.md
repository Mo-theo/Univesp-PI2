# Ajustes em relação ao relatório parcial

**Projeto:** CondoPort – sistema web para gestão de visitantes e encomendas em portaria condominial
**Disciplina:** Projeto Integrador em Computação II (PJI240) – UNIVESP

> **Nota de uso.** Este documento compara o sistema efetivamente implementado (código no repositório,
> branch `main`) com o que foi previsto no relatório parcial. As afirmações sobre o *relatório parcial*
> baseiam-se nos pontos informados pela equipe (uso de MySQL, perfis de usuário e funcionalidades
> previstas) e devem ser conferidas com o texto original antes da inclusão no relatório final.
> As afirmações sobre o *sistema implementado* refletem o código-fonte.

---

## 1. Visão geral

Durante o desenvolvimento, o escopo do sistema foi delimitado a um Produto Mínimo Viável (MVP)
voltado à rotina da portaria: cadastro e consulta de moradores, controle de entrada e saída de
visitantes e controle de recebimento e retirada de encomendas. Algumas decisões de projeto
descritas no relatório parcial foram revistas para adequar a solução ao prazo da disciplina,
à infraestrutura gratuita disponível para hospedagem e aos princípios de minimização de dados
da Lei Geral de Proteção de Dados (LGPD). As seções a seguir descrevem cada ajuste e sua
justificativa.

## 2. Tecnologias adotadas

| Componente | Implementação final |
|---|---|
| Linguagem | Python 3.12 |
| Framework web | Django 5.2 (versão LTS) |
| Interface | Templates do Django, Bootstrap 5.3 (via CDN) |
| Banco de dados (desenvolvimento) | SQLite |
| Banco de dados (produção) | PostgreSQL, configurado pela variável `DATABASE_URL` (biblioteca `dj-database-url`, driver `psycopg` 3) |
| Servidor de aplicação | gunicorn |
| Arquivos estáticos | WhiteNoise |
| Hospedagem (configurada) | Render (web service + PostgreSQL gerenciado, descritos em `render.yaml`) |
| Controle de versão | Git e GitHub |

### 2.1 Substituição do MySQL pelo PostgreSQL

O relatório parcial previa o uso do MySQL como sistema gerenciador de banco de dados. Na
implementação, adotou-se o **PostgreSQL** em produção e o **SQLite** no ambiente de
desenvolvimento. A mudança justifica-se por três fatores:

1. **Hospedagem:** a plataforma Render, escolhida para a publicação, oferece PostgreSQL
   gerenciado de forma integrada ao serviço web, o que dispensa a contratação e a configuração
   de um servidor de banco de dados separado.
2. **Integração com o Django:** o PostgreSQL é plenamente suportado pelo framework, e a
   conexão é definida por uma única variável de ambiente (`DATABASE_URL`), sem credenciais no
   código-fonte.
3. **Portabilidade:** como o acesso aos dados é feito pelo ORM do Django, o mesmo código
   funciona com SQLite (desenvolvimento local, sem instalação de servidor) e com PostgreSQL
   (produção). As tabelas são criadas pelo mecanismo de migrações do framework.

## 3. Perfil de usuário

O MVP implementa um **único perfil operacional: o porteiro**. Todas as telas da aplicação
exigem autenticação, garantida globalmente pelo middleware `LoginRequiredMiddleware` do Django;
apenas as telas de login (a da aplicação e a do painel administrativo) são públicas. O porteiro pode entrar com nome de usuário ou com e-mail.

Não foram implementados perfis de morador, síndico ou administrador da aplicação com telas
próprias. Os moradores são apenas *registros* cadastrados pelo porteiro e não acessam o sistema.

Para fins de demonstração, o comando `criar_porteiro_demo` cria um usuário porteiro fictício.
A senha não fica no código: ela é lida de uma variável de ambiente ou digitada no terminal e
passa pelos validadores de senha do Django.

> **Observação técnica.** O painel administrativo padrão do Django (`/admin/`) permanece
> habilitado e é acessível apenas a superusuários criados manualmente. O usuário porteiro não
> tem acesso a esse painel. Trata-se de uma ferramenta de manutenção, e não de um segundo
> perfil da aplicação (ver Seção 8).

## 4. Entidades implementadas

O modelo de dados foi simplificado para três entidades, todas no aplicativo `core`.

### 4.1 Morador

| Campo | Tipo / regra |
|---|---|
| `nome` | texto, obrigatório |
| `cpf` | texto, obrigatório e único; o formulário aceita o número com ou sem pontuação, exige 11 dígitos e o armazena no formato `000.000.000-00` |
| `telefone`, `email` | opcionais |
| `bloco`, `apartamento` | obrigatórios |
| `status` | `ativo` ou `inativo` (padrão: `ativo`) |

Bloco e apartamento são atributos do morador; não há uma entidade “Unidade” separada. Somente
moradores ativos aparecem como opção nos formulários de visita e de encomenda. A exclusão de um
morador que possua visitas ou encomendas registradas é bloqueada (`on_delete=PROTECT`), para
preservar o histórico; nesse caso, o sistema orienta a marcá-lo como inativo.

### 4.2 Visitante

| Campo | Tipo / regra |
|---|---|
| `nome`, `documento` | obrigatórios |
| `telefone`, `motivo` | opcionais |
| `morador` | morador/apartamento visitado (obrigatório) |
| `data_entrada` | preenchida automaticamente no registro |
| `data_saida` | vazia enquanto o visitante está no condomínio |

A saída é registrada por uma ação rápida (“Registrar saída”), que grava a data e a hora atuais.
Uma segunda tentativa de registrar a saída não altera o horário já gravado. O modelo impede que
a saída seja anterior à entrada.

### 4.3 Encomenda

| Campo | Tipo / regra |
|---|---|
| `descricao` | obrigatória |
| `transportadora`, `codigo_rastreio` | opcionais |
| `morador` | destinatário (obrigatório) |
| `data_recebimento` | preenchida automaticamente na chegada |
| `status` | `pendente` (padrão) ou `retirada` |
| `data_retirada` | preenchida automaticamente na baixa |
| `nome_retirou`, `documento_retirou` | obrigatórios na baixa |

## 5. Registro da retirada de encomendas

A retirada de uma encomenda é **registrada pelo porteiro**, e não pelo morador. No momento da
entrega, o porteiro abre a tela de baixa e informa o **nome** e o **documento (RG ou CPF)** de
quem está retirando, que pode ser o próprio morador ou outra pessoa. Ao confirmar:

- o status da encomenda passa de `pendente` para `retirada`;
- a data e a hora da retirada são registradas automaticamente pelo sistema, e não digitadas
  pelo porteiro;
- a baixa é recusada se o nome ou o documento estiverem vazios, inclusive quando contêm apenas
  espaços;
- uma encomenda já retirada não pode receber nova baixa, o que preserva o registro original.

Essas regras são aplicadas no formulário e também na validação do próprio modelo (`clean`).

## 6. Funcionalidades implementadas

- **Autenticação:** login e logout (o logout é feito por requisição POST, com proteção CSRF).
- **Painel inicial (dashboard):** contadores de visitantes presentes, de visitantes que entraram
  no dia (pelo fuso horário de São Paulo) e de encomendas pendentes, além das cinco entradas de
  visitantes e das cinco encomendas mais recentes.
- **Moradores:** listagem com busca por nome, bloco ou apartamento, paginação, cadastro, edição
  e exclusão (com a restrição descrita na Seção 4.1).
- **Visitantes:** listas separadas de “presentes agora” e “histórico”, com busca por visitante,
  documento, morador ou apartamento; registro de entrada e ação rápida de saída.
- **Encomendas:** listas separadas de “pendentes” e “histórico de retiradas”, com busca;
  registro de chegada e baixa (Seção 5).
- **Dados de demonstração:** o comando `popular_dados_teste` gera moradores, visitantes e
  encomendas **fictícios**, com CPFs no padrão `000.000.000-XX`, documentos com prefixo `TESTE-`
  e e-mails no domínio `exemplo.com.br`, em conformidade com a LGPD.
- **Acessibilidade básica:** rótulos (`label`) associados a todos os campos, destaque visual de
  foco para navegação por teclado, link “Pular para o conteúdo”, legendas em tabelas, nomes
  acessíveis em botões de ação e cores padrão do Bootstrap.
- **Segurança:** proteção CSRF em todos os formulários; em produção (`DEBUG=False`), HTTPS
  obrigatório, cookies seguros e cabeçalho HSTS. Segredos e credenciais ficam em variáveis de
  ambiente e não são versionados.

## 7. Funcionalidades não implementadas (próximas etapas)

As funcionalidades abaixo **não fazem parte** da versão atual e ficam registradas como trabalhos
futuros:

- **Notificações:** não há envio de avisos aos moradores (por e-mail, SMS ou aplicativo de
  mensagens) sobre a chegada de encomendas ou de visitantes.
- **Relatórios:** não há geração de relatórios gerenciais (por período, por morador ou por
  bloco) nem exportação em PDF ou planilha. A consulta a registros anteriores limita-se às
  listas de histórico com busca textual e aos contadores do painel.
- **Outros perfis de acesso:** área do morador, do síndico ou de administração pela própria
  aplicação.
- **Edição e cancelamento de registros pela interface do porteiro:** visitas e encomendas já
  registradas não podem ser editadas ou excluídas pelas telas da aplicação. Isso só é possível
  pelo painel administrativo do Django.
- **Validação dos dígitos verificadores do CPF:** o sistema verifica a quantidade de dígitos e
  a unicidade, mas não o cálculo dos dígitos verificadores.
- Itens já excluídos do escopo desde o início: biometria, integração com catracas e pagamentos.

## 8. Divergências entre a especificação do projeto e o código

Durante a revisão, foram identificados os seguintes pontos em que a especificação interna do
projeto (`CLAUDE.md`) e o código não coincidem integralmente. Eles são registrados aqui para
decisão da equipe, e não como funcionalidades adicionais:

1. **Perfil único × painel administrativo:** a especificação prevê um único tipo de usuário (o
   porteiro). O código mantém o painel `/admin/` do Django, acessível a superusuários. Cabe à
   equipe decidir se o relatório o descreve como ferramenta de manutenção ou se ele deve ser
   desativado.
2. **“Moradores/unidades”:** a especificação menciona unidades, mas não existe entidade
   “Unidade”; bloco e apartamento são campos do morador.
3. **Data e hora da baixa:** a especificação diz que a baixa é feita “com data e hora”. No
   código, elas são registradas automaticamente pelo sistema, e não informadas pelo porteiro.
4. **Funcionalidades além da especificação:** o painel inicial (dashboard) e a exclusão de
   moradores não constavam explicitamente da especificação do MVP, mas foram implementados.

## 9. Testes realizados

### 9.1 Testes automatizados

O projeto possui **69 testes automatizados** (framework de testes do Django), todos aprovados
na versão atual. Eles são executados com `python manage.py test`.

| Arquivo | Quantidade | O que verifica |
|---|---:|---|
| `core/tests.py` | 27 | **Modelos:** representação textual, valores padrão, unicidade do CPF, ordenação, bloqueio de exclusão de morador com registros, saída anterior à entrada, regras de retirada de encomenda. **Autenticação:** redirecionamento de usuário anônimo ao login, acesso de usuário autenticado, login por usuário e por e-mail, senha incorreta, logout, rejeição de envio sem token CSRF, presença de rótulos no formulário de login. **Comandos:** geração de dados fictícios e criação do porteiro de demonstração (inclusive recusa de senha fraca). |
| `core/test_views.py` | 25 | Exigência de login em todas as páginas; listagem, busca, cadastro, edição e exclusão de moradores (incluindo CPF inválido ou duplicado); separação entre visitantes presentes e histórico, busca, registro de entrada, registro de saída, saída repetida, redirecionamento seguro e método HTTP permitido. |
| `core/test_encomendas.py` | 17 | **Fluxo de baixa** (9 testes): baixa válida, ausência de nome, de documento ou de ambos, campos contendo apenas espaços, baixa repetida, encomenda inexistente e acesso sem login. Também listagem, busca e registro de chegada de encomendas e os contadores e últimos registros do painel. |

### 9.2 Verificações complementares

- `python manage.py check`: sem problemas.
- `python manage.py check --deploy`, com as configurações de produção: resta apenas o aviso
  `security.W021`, que recomenda inscrever o domínio na lista de *HSTS preload* dos navegadores.
  Essa inscrição não se aplica a um subdomínio de terceiros (`*.onrender.com`) e é de difícil
  reversão.
- **Simulação local de produção** (`DEBUG=False`): arquivos estáticos servidos pelo WhiteNoise,
  redirecionamento de HTTP para HTTPS, cabeçalhos de segurança e bloqueio de requisição de
  origem externa por CSRF.

### 9.3 Limitações dos testes

- **Acessibilidade:** os testes automatizados verificam apenas a presença de rótulos nos campos.
  O contraste de cores e a navegação por teclado não são testados automaticamente e dependem de
  verificação manual.
- **Ambiente de produção:** os testes automatizados rodam com SQLite. O funcionamento com
  PostgreSQL e a publicação no Render dependem da verificação no ambiente publicado (Seção 10).
- **Testes com usuários reais:** não foram realizados. Todos os dados utilizados são fictícios.

## 10. Situação da publicação

A configuração de deploy (arquivos `render.yaml` e `build.sh`, além das variáveis de ambiente)
está pronta no repositório. **A confirmação de que o sistema está publicado e funcional no
Render, incluindo o endereço (URL) a citar no relatório, deve ser feita pela equipe no painel
da plataforma**, pois depende da criação do serviço na conta do grupo.

No plano gratuito do Render, o serviço web é suspenso após um período sem acesso, e o primeiro
acesso seguinte é mais lento. O banco PostgreSQL gratuito tem prazo de validade limitado. Esses
fatores devem ser considerados na data da apresentação.
