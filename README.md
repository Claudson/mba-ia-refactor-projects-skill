# Refatoração Arquitetural Automatizada com Skills — `refactor-arch`

Entrega do desafio de **Criação de Skills** do MBA. O enunciado original está em [DESAFIO.md](DESAFIO.md).

A skill `refactor-arch` (Claude Code) analisa uma codebase, audita anti-patterns por severidade, gera um relatório e — após confirmação humana — refatora o projeto para o padrão **MVC**, validando que a aplicação continua funcionando. Ela foi executada em três projetos legados de stacks diferentes:

| # | Projeto | Stack | Domínio |
|---|---|---|---|
| 1 | [code-smells-project](code-smells-project/) | Python + Flask + sqlite3 (SQL puro) | API de E-commerce |
| 2 | [ecommerce-api-legacy](ecommerce-api-legacy/) | Node.js + Express + sqlite3 | LMS com fluxo de checkout |
| 3 | [task-manager-api](task-manager-api/) | Python + Flask + SQLAlchemy | Task Manager |

---

## A) Análise Manual

Antes de construir a skill, os três projetos foram lidos integralmente e executados para registrar o comportamento original de todos os endpoints (baseline em [reports/logs/](reports/logs/), gerado por [scripts/smoke_test.py](scripts/smoke_test.py)). A escala de severidade segue o enunciado:

- **CRITICAL** — segurança grave ou violação total da separação de responsabilidades
- **HIGH** — forte violação de MVC/SOLID que dificulta manutenção e testes
- **MEDIUM** — padronização, duplicação, performance moderada, validações ausentes
- **LOW** — legibilidade, nomenclatura, magic numbers

### Projeto 1 — code-smells-project (Python/Flask)

Estrutura original: 4 arquivos (`app.py`, `controllers.py`, `models.py`, `database.py`), ~780 linhas, sem camadas reais — `models.py` mistura SQL, regra de negócio e serialização dos 4 domínios (produtos, usuários, pedidos, relatórios).

| # | Severidade | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **SQL Injection** — queries montadas por concatenação de strings com entrada do usuário | `models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 174, 279-281, 290-297` | `POST /login` com `email = "' OR 1=1 --"` autentica sem senha; a busca permite ler/alterar qualquer tabela. |
| 2 | CRITICAL | **Endpoint de execução de SQL arbitrário e reset de banco sem autenticação** | `app.py:47-76` | `POST /admin/query` executa qualquer SQL enviado no body (inclusive `DROP`); `POST /admin/reset-db` apaga todos os dados — ambos públicos. |
| 3 | CRITICAL | **Credenciais hardcoded e vazamento de segredo** — `SECRET_KEY` fixa no código e devolvida pelo `/health`; `debug=True` em produção | `app.py:7-8, 88`; `controllers.py:287-289` | Qualquer cliente lê a chave de assinatura de sessão; modo debug do Werkzeug expõe console interativo (RCE). |
| 4 | CRITICAL | **Senhas em texto puro e expostas na API** — armazenadas sem hash e devolvidas em `GET /usuarios` | `database.py:31, 75-79`; `models.py:83, 99, 110` | Vazamento direto de credenciais de todos os usuários. |
| 5 | HIGH | **God Module / ausência de camadas** — `models.py` concentra acesso a dados, regras (estoque, total, descontos) e formatação de 4 domínios; controllers chamam SQL direto (`health_check`) | `models.py:1-314`; `controllers.py:264-292`; `app.py:47-76` | Impossível testar regra de negócio sem banco; qualquer mudança afeta tudo. |
| 6 | HIGH | **Estado global mutável** — conexão SQLite única em variável global, compartilhada entre threads (`check_same_thread=False`) e criação de schema + seed acoplados ao `get_db()` | `database.py:4-11` | Condições de corrida sob concorrência, sem ciclo de vida de conexão e sem injeção de dependência. |
| 7 | MEDIUM | **Queries N+1** — para cada pedido, uma query de itens; para cada item, uma query de produto | `models.py:171-201, 203-233` | Número de queries cresce com pedidos × itens; `GET /pedidos` degrada linearmente. |
| 8 | MEDIUM | **Pedido sem transação/atomicidade** e preço consultado duas vezes por item | `models.py:133-169` | Falha no meio do loop deixa pedido sem itens ou estoque inconsistente. |
| 9 | MEDIUM | **Duplicação de código** — mapeamento `row → dict` repetido; validação de produto duplicada entre criar/atualizar; queries de pedidos duplicadas | `models.py:11-20, 31-40, 304-313`; `controllers.py:28-50, 72-90` | Mudanças de schema exigem editar vários pontos. |
| 10 | MEDIUM | **Efeitos colaterais/notificações simulados com `print` dentro do controller** e erros internos devolvidos ao cliente (`str(e)`) | `controllers.py:208-210, 248-250, 12, 22…` | Mistura de responsabilidades e vazamento de detalhes internos. |
| 11 | LOW | **Magic numbers** nas faixas de desconto (`10000`, `0.1`, `5000`, `0.05`, `1000`, `0.02`) e listas de status/categorias inline | `models.py:256-262`; `controllers.py:52, 242` | Regra de negócio sem nome; difícil de alterar com segurança. |
| 12 | LOW | **Logging com `print` e nomes sombreando built-ins** (`id`) | `controllers.py:8, 57, 106, 161, 179…`; `models.py:24, 54, 65` | Sem nível de log nem destino configurável; legibilidade. |

### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

Estrutura original: 3 arquivos (`app.js`, `AppManager.js`, `utils.js`), ~180 linhas. A classe `AppManager` cria o banco, faz seed, define rotas e executa toda a regra de negócio.

| # | Severidade | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Credenciais hardcoded** — senha de banco e chave **live** do gateway de pagamento no código | `src/utils.js:1-7` | Segredos de produção versionados no Git. |
| 2 | CRITICAL | **Dados sensíveis em log** — número completo do cartão e chave do gateway impressos no console | `src/AppManager.js:45` | Violação de PCI-DSS; logs passam a conter dados de cartão. |
| 3 | CRITICAL | **Hash de senha inseguro** — `badCrypto` só repete base64 dos 2 primeiros caracteres (reversível, colisões triviais) e senha default `"123456"` | `src/utils.js:17-23`; `src/AppManager.js:68` | Senhas efetivamente em texto puro; usuários criados sem senha recebem senha conhecida. |
| 4 | CRITICAL | **God Class** — `AppManager` contém conexão, DDL, seed, rotas HTTP, regra de pagamento, matrícula e auditoria | `src/AppManager.js:1-141` | Nenhuma separação de camadas; impossível testar checkout sem HTTP + banco. |
| 5 | HIGH | **Callback hell** e regra de negócio dentro do handler — checkout aninha 6 níveis de callbacks sem transação | `src/AppManager.js:28-78` | Fluxo ilegível; falha no meio deixa matrícula sem pagamento. |
| 6 | HIGH | **Estado global mutável** — `globalCache` e `totalRevenue` em escopo de módulo | `src/utils.js:9-15, 25` | Estado compartilhado entre requisições, sem limite (vazamento de memória). |
| 7 | MEDIUM | **Queries N+1** no relatório financeiro — para cada curso → matrículas → usuário + pagamento | `src/AppManager.js:80-129` | 1 + C + 2·M queries; contagem manual de pendências propensa a bugs. |
| 8 | MEDIUM | **Exclusão sem integridade referencial** — `DELETE /api/users/:id` deixa matrículas e pagamentos órfãos (a própria resposta admite) e ignora `err` | `src/AppManager.js:131-136` | Dados inconsistentes; erros silenciosos. |
| 9 | MEDIUM | **Erros ignorados / tratamento inconsistente** — callbacks descartam `err` (relatório, auditoria) e respostas misturam texto puro e JSON | `src/AppManager.js:57, 92, 104, 106, 133` | Falhas viram respostas parciais ou crashes; contrato da API imprevisível. |
| 10 | MEDIUM | **Validação de entrada fraca** — só checa presença dos campos; e-mail, cartão e `c_id` não são validados | `src/AppManager.js:35` | Entradas inválidas chegam ao banco/gateway. |
| 11 | LOW | **Nomes crípticos** — `u`, `e`, `p`, `cid`, `cc` e payload `usr/eml/pwd/c_id` | `src/AppManager.js:29-33` | Legibilidade; `e` ainda conflita com convenção de `error`. |
| 12 | LOW | **Magic values** — aprovação de pagamento por `cc.startsWith("4")`, status `"PAID"`/`"DENIED"` como string solta, import não usado (`totalRevenue`) | `src/AppManager.js:2, 46, 47` | Regra de negócio escondida em literal. |

### Projeto 3 — task-manager-api (Python/Flask + SQLAlchemy)

Estrutura original: já separa `models/`, `routes/`, `services/`, `utils/` (~1.150 linhas), porém **não há camada de controller**: as rotas contêm validação, regra de negócio, queries e serialização.

| # | Severidade | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Hash de senha com MD5** (sem salt) | `models/user.py:27-32` | MD5 é quebrável por rainbow tables em segundos. |
| 2 | CRITICAL | **Senha (hash) exposta na API** — `to_dict()` inclui `password`, usado em `GET /users/<id>`, `POST /users`, `PUT /users`, `POST /login` | `models/user.py:16-25`; `routes/user_routes.py:33, 85, 129, 209` | Vazamento de hashes fracos para qualquer cliente. |
| 3 | CRITICAL | **Credenciais hardcoded** — `SECRET_KEY` e senha SMTP no código; `debug=True` | `app.py:13, 34`; `services/notification_service.py:7-10` | Segredos versionados; console de debug exposto. |
| 4 | HIGH | **Regra de negócio nas rotas (sem controllers/services)** — validação, cálculo de atraso, estatísticas e serialização dentro dos handlers | `routes/task_routes.py:11-299`; `routes/report_routes.py:12-101`; `routes/user_routes.py:42-90` | Rotas "gordas" não testáveis; `services/` existe mas não é usado. |
| 5 | HIGH | **Autenticação falsa** — login devolve `'fake-jwt-token-' + id` e nenhuma rota exige autenticação | `routes/user_routes.py:207-211` | Qualquer cliente altera/deleta qualquer recurso. |
| 6 | MEDIUM | **Queries N+1** — `User.query.get` e `Category.query.get` por task; contagem por usuário/categoria em loop | `routes/task_routes.py:40-56`; `routes/report_routes.py:53-68, 159-165`; `routes/user_routes.py:22` | Número de queries cresce com o volume de tasks/usuários. |
| 7 | MEDIUM | **APIs deprecated** — `Model.query.get()` (legado no SQLAlchemy 2.x → `db.session.get(Model, id)`) e `datetime.utcnow()` (deprecated no Python 3.12 → `datetime.now(timezone.utc)`) | `routes/*.py` (16 ocorrências de `.query.get(`); `models/*.py:11-16, 52`; `routes/report_routes.py:35-71`… | Gera `DeprecationWarning` hoje e quebra em versões futuras. |
| 8 | MEDIUM | **Duplicação de lógica** — cálculo de "overdue" repetido 6× (existe `Task.is_overdue()` sem uso); validação de task duplicada entre rotas e `utils/helpers.process_task_data` (código morto) | `routes/task_routes.py:30-39, 71-80, 283-287`; `routes/user_routes.py:171-180`; `routes/report_routes.py:33-43, 132-135`; `utils/helpers.py:57-107` | Regra muda em um lugar e não nos outros. |
| 9 | MEDIUM | **`except:` genérico** engolindo qualquer exceção (inclusive `KeyboardInterrupt`) | `routes/task_routes.py:62, 137, 204, 236`; `routes/user_routes.py:130, 149`; `routes/report_routes.py:186, 207, 221`; `utils/helpers.py:46, 49, 88` | Esconde bugs e dificulta diagnóstico. |
| 10 | MEDIUM | **Validação ausente** — `PUT /categories` não valida body nulo nem cor; `priority` não checa tipo (string → `TypeError` 500) | `routes/report_routes.py:196-202`; `routes/task_routes.py:110, 182` | Entrada inválida gera erro 500. |
| 11 | LOW | **Imports não utilizados** (`os, sys, json, time, hashlib, math`) | `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`; `routes/report_routes.py:8`; `utils/helpers.py:3-7` | Ruído e acoplamento aparente. |
| 12 | LOW | **Magic numbers e booleanos verbosos** — `3`, `200`, `4`, `1..5`, `7` dias espalhados (constantes existem em `helpers.py:110-116` mas não são usadas); `if x: return True else: return False` | `routes/task_routes.py:94-111`; `routes/user_routes.py:64, 115`; `models/task.py:37-60`; `models/user.py:34-38` | Legibilidade e consistência. |

### Padrões recorrentes → insumo para a skill

| Padrão | P1 | P2 | P3 |
|---|:-:|:-:|:-:|
| Credenciais/segredos hardcoded | ✓ | ✓ | ✓ |
| Senha sem hash forte / exposta | ✓ | ✓ | ✓ |
| SQL Injection | ✓ | | |
| Endpoint administrativo perigoso sem auth | ✓ | | ✓ (auth falsa) |
| God Class / ausência de camadas | ✓ | ✓ | parcial |
| Regra de negócio em rota/controller | ✓ | ✓ | ✓ |
| Estado global mutável | ✓ | ✓ | ✓ (`notifications`) |
| Queries N+1 | ✓ | ✓ | ✓ |
| Duplicação de lógica | ✓ | | ✓ |
| Erros engolidos / tratamento não centralizado | ✓ | ✓ | ✓ |
| APIs deprecated | | | ✓ |
| Magic numbers / nomes ruins | ✓ | ✓ | ✓ |

---

## B) Construção da Skill

_Em construção._

## C) Resultados

_Pendente — preenchido após a execução da skill nos 3 projetos._

## D) Como Executar

_Pendente._
