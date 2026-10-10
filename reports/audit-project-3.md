================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.12.10 + Flask 3.0.0 (SQLite / ORM Flask-SQLAlchemy 3.1.1 + SQLAlchemy 2.1.4)
Files:   15 analyzed | ~1158 lines of code
Date:    2026-10-10

## Summary
CRITICAL: 4 | HIGH: 3 | MEDIUM: 6 | LOW: 5

| # | Severity | Finding | Catalog | Location |
|---|---|---|---|---|
| F01 | CRITICAL | Secret key e senha SMTP hardcoded | AP-01 | app.py:13 |
| F02 | CRITICAL | Senhas com hash MD5 sem salt | AP-03 | models/user.py:27-32 |
| F03 | CRITICAL | Hash de senha exposto nas respostas da API | AP-04 | models/user.py:21 |
| F04 | CRITICAL | Token falso no login e endpoints destrutivos sem autenticação | AP-05 | routes/user_routes.py:210 |
| F05 | HIGH | Debug ligado em 0.0.0.0 e CORS irrestrito | AP-07 | app.py:15, 34 |
| F06 | HIGH | Regra de negócio, queries e serialização nas rotas (fat controllers) | AP-08 | routes/task_routes.py:11-299 |
| F07 | HIGH | Alto acoplamento: sem app factory, config inline, infra concreta instanciada nas camadas | AP-09 | app.py:9-31 |
| F08 | MEDIUM | Validação de entrada fraca (500 com tipos inválidos, body nulo, cor não validada) | AP-14 | routes/task_routes.py:113, 167-170, 182, 261, 264 |
| F09 | MEDIUM | `except:` genérico e ausência de tratamento de erros centralizado | AP-15 | routes/task_routes.py:13, 62-63 |
| F10 | MEDIUM | Queries N+1 e contagens repetidas | AP-12 | routes/task_routes.py:41-57 |
| F11 | MEDIUM | Lógica duplicada (atraso, serialização de task, validações) | AP-13 | routes/task_routes.py:17-39 |
| F12 | MEDIUM | Tasks órfãs ao apagar categoria | AP-16 | routes/report_routes.py:211-223 |
| F13 | MEDIUM | APIs deprecated: `datetime.utcnow()` e `Query.get()` | AP-DEP | models/task.py:15-16 |
| F14 | LOW | `print` usado como log | AP-17 | routes/task_routes.py:149 |
| F15 | LOW | Magic numbers / strings e constantes não usadas | AP-18 | routes/task_routes.py:96-114 |
| F16 | LOW | Nomenclatura ruim | AP-19 | routes/report_routes.py:24-28 |
| F17 | LOW | Código morto, imports e dependências não usados | AP-20 | app.py:7 |
| F18 | LOW | Condicionais verbosas / redundantes | AP-21 | models/task.py:38-60 |

## Findings

### F01 [CRITICAL] Secret key e senha SMTP hardcoded
File: app.py:13
File: services/notification_service.py:7-10
Catalog: AP-01 — Credenciais / Segredos Hardcoded
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` e, no serviço de e-mail, `self.email_user = 'taskmanager@gmail.com'` / `self.email_password = 'senha123'` (host `smtp.gmail.com`, porta `587`) como literais; a URI do banco (`'sqlite:///tasks.db'`, app.py:11) também é fixa.
Impact: Qualquer pessoa com acesso ao repositório obtém a chave usada para assinar sessões/cookies e a credencial da conta SMTP; trocar os valores por ambiente exige editar código.
Recommendation: Externalizar para um módulo `config` lido de variáveis de ambiente (`.env` via python-dotenv, já declarado), sem defaults de produção, e documentar em `.env.example` (Playbook P-01).

### F02 [CRITICAL] Senhas com hash MD5 sem salt
File: models/user.py:27-32
File: seed.py:19, 26, 33
Catalog: AP-03 — Armazenamento Inseguro de Senhas
Description: `set_password` grava `hashlib.md5(pwd.encode()).hexdigest()` e `check_password` compara `self.password == hashlib.md5(...)`; o seed cria usuários com senhas `'1234'`, `'abcd'`, `'pass'`.
Impact: MD5 sem salt é revertido por rainbow tables em segundos; senhas iguais geram hashes iguais. Atinge `POST /users`, `PUT /users/<id>` e `POST /login`.
Recommendation: Usar `werkzeug.security.generate_password_hash` / `check_password_hash` (Werkzeug já é dependência do Flask), com verificação compatível com hashes MD5 legados apenas para migração no login (Playbook P-07).

### F03 [CRITICAL] Hash de senha exposto nas respostas da API
File: models/user.py:21
File: routes/user_routes.py:33, 85, 129, 209
Catalog: AP-04 — Exposição de Dados Sensíveis
Description: `User.to_dict()` inclui `'password': self.password`, e é devolvido por `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login` (`'user': user.to_dict()`).
Impact: Qualquer cliente recebe o hash MD5 de qualquer usuário (combinado com F02, equivale à senha em texto puro).
Recommendation: Remover `password` da serialização pública (serializer seguro no model) (Playbook P-08).

### F04 [CRITICAL] Token falso no login e endpoints destrutivos sem autenticação
File: routes/user_routes.py:52, 71, 134-151, 210
File: routes/task_routes.py:225-238
File: routes/report_routes.py:211-223
Catalog: AP-05 — Endpoints Perigosos sem Proteção / Autenticação Quebrada
Description: O login devolve `'token': 'fake-jwt-token-' + str(user.id)` — previsível e nunca verificado; nenhuma rota exige autenticação, inclusive `DELETE /users/<id>` (que apaga também todas as tasks do usuário), `DELETE /tasks/<id>` e `DELETE /categories/<id>`; `POST /users` aceita `role: 'admin'` do próprio cliente.
Impact: Qualquer cliente anônimo pode apagar usuários/tasks/categorias e se auto-registrar como admin; o "token" pode ser forjado para qualquer id.
Recommendation: Emitir token assinado (HMAC com `SECRET_KEY` via `itsdangerous`, já dependência do Flask) no login e exigir token válido nos endpoints destrutivos (Playbook P-13).

### F05 [HIGH] Debug ligado em 0.0.0.0 e CORS irrestrito
File: app.py:15, 34
Catalog: AP-07 — Modo Debug / Configuração de Runtime Insegura
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` e `CORS(app)` sem restrição de origens.
Impact: O debugger interativo do Werkzeug fica exposto na rede (execução remota de código se o PIN vazar) e qualquer origem pode chamar a API pelo navegador.
Recommendation: Ler `DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` do ambiente, com debug desligado e host `127.0.0.1` por padrão (Playbook P-01).

### F06 [HIGH] Regra de negócio, queries e serialização nas rotas (fat controllers)
File: routes/task_routes.py:11-63, 85-154, 156-223, 240-271, 273-299
File: routes/user_routes.py:42-90, 92-132, 153-183, 185-211
File: routes/report_routes.py:12-101, 103-155, 157-223
File: services/notification_service.py:4-48
Catalog: AP-08 — Regra de Negócio nas Rotas / Fat Controllers
Description: Os handlers fazem `Task.query...`/`db.session.commit()` direto, validam campos, calculam estatísticas (`completion_rate`, contagens por status/prioridade, `days_overdue`) e montam dicts à mão — `create_task` tem 70 linhas e `summary_report` 90; o CRUD de categorias está dentro de `report_routes.py`; `NotificationService` e `utils.helpers.process_task_data` existem mas nunca são importados.
Impact: Impossível testar regras sem HTTP; qualquer mudança de regra (ex.: o que é "atrasada") exige editar vários handlers; responsabilidades de domínio misturadas.
Recommendation: Extrair controllers/services por domínio (tasks, users, categories, reports) e deixar as rotas finas apenas mapeando HTTP → controller (Playbook P-04).

### F07 [HIGH] Alto acoplamento: sem app factory, config inline, infra concreta instanciada nas camadas
File: app.py:9-31
File: services/notification_service.py:5-10
File: seed.py:2
Catalog: AP-09 — Alto Acoplamento / Sem Injeção de Dependência
Description: `app = Flask(__name__)` em nível de módulo com config inline e `db.create_all()` executado no import (`with app.app_context()`); rotas importam `db` e models concretos diretamente; `NotificationService.__init__` fixa host/credenciais SMTP; `seed.py` importa a instância global `app`.
Impact: Não dá para criar a aplicação com outra config (testes, outro banco) nem substituir dependências; importar `app` já toca no banco.
Recommendation: Composition root com `create_app(config)` que carrega config, inicializa extensões, registra blueprints e handlers de erro; serviços recebem config por parâmetro (Playbook P-03 / P-06).

### F08 [MEDIUM] Validação de entrada fraca (500 com tipos inválidos, body nulo, cor não validada)
File: routes/task_routes.py:113, 167-170, 182, 261, 264
File: routes/user_routes.py:102-103, 124-125
File: routes/report_routes.py:179-180, 196-202
Catalog: AP-14 — Validação de Entrada Ausente ou Fraca
Description: `priority < 1` com `priority` string lança `TypeError` (500); `len(data['title'])` com `title: null` idem; `int(priority)`/`int(user_id)` na busca lançam `ValueError` com query inválida; `update_category` faz `'name' in data` sem checar `data` nulo; `name` vazio e `active` não booleano aceitos em `PUT /users`; `color` nunca validado (existe `is_valid_color` não usado).
Impact: Entradas malformadas viram 500 em vez de 400 e dados inconsistentes são persistidos.
Recommendation: Validadores únicos na borda do controller retornando 400 com a mensagem existente (Playbook P-12).

### F09 [MEDIUM] `except:` genérico e ausência de tratamento de erros centralizado
File: routes/task_routes.py:13, 62-63, 137, 151, 204, 221, 236
File: routes/user_routes.py:87, 130, 149
File: routes/report_routes.py:186, 207, 221
File: utils/helpers.py:46, 49, 88
Catalog: AP-15 — Tratamento de Erros Engolido / Inconsistente
Description: Vários `except:` nus (que capturam até `KeyboardInterrupt`), `get_tasks` embrulha o handler inteiro num `try` que devolve `{'error': 'Erro interno'}` sem log; não há `@app.errorhandler`, então 404/405/500 do Flask saem em HTML.
Impact: Erros reais são escondidos sem rastro; formato de erro inconsistente entre JSON e HTML.
Recommendation: Exceções de domínio (`ValidationError`, `NotFoundError`, ...) + handlers centralizados que devolvem `{'error': ...}` e logam o 500 (Playbook P-10).

### F10 [MEDIUM] Queries N+1 e contagens repetidas
File: routes/task_routes.py:41-57, 275-281
File: routes/user_routes.py:14-22
File: routes/report_routes.py:15-30, 53-56, 159-163
Catalog: AP-12 — Queries N+1
Description: `GET /tasks` faz `User.query.get(t.user_id)` e `Category.query.get(t.category_id)` por task; `GET /users` acessa `len(u.tasks)` (lazy) por usuário; `summary_report` roda 12 `count()` separados + `Task.query.filter_by(user_id=u.id)` por usuário; `GET /categories` faz um `count()` por categoria.
Impact: O número de queries cresce linearmente com os dados (2N+1 em `/tasks`).
Recommendation: Eager loading (`joinedload`/`selectinload`) e agregações com `GROUP BY` (Playbook P-05).

### F11 [MEDIUM] Lógica duplicada (atraso, serialização de task, validações)
File: routes/task_routes.py:17-39, 71-80, 92-114, 166-184, 283-287
File: routes/user_routes.py:61, 64, 106, 115, 162-180
File: routes/report_routes.py:33-36, 132-135
File: models/task.py:50-60
File: utils/helpers.py:19-23, 57-108
Catalog: AP-13 — Código / Lógica Duplicada
Description: A regra "atrasada" (`due_date < utcnow()` e status ≠ done/cancelled) é reescrita em 6 lugares enquanto `Task.is_overdue()` existe; a serialização de task é refeita à mão em `get_tasks` e `get_user_tasks` em vez de `to_dict()`; validação de task duplicada entre criar/atualizar (e de novo em `process_task_data`, não usado); regex de e-mail repetida em vez de `validate_email`.
Impact: Regras divergem com facilidade (ex.: criar valida `len < 3` com strip diferente do helper).
Recommendation: Fonte única: `Task.is_overdue()`/serializer no model e validadores compartilhados (Playbook P-12).

### F12 [MEDIUM] Tasks órfãs ao apagar categoria
File: routes/report_routes.py:211-223
File: models/task.py:14, 21
Catalog: AP-16 — Dados Órfãos / Integridade Referencial Ausente
Description: `delete_category` apaga a categoria sem tratar as tasks; a FK `category_id` não tem `ondelete` e o SQLite não aplica FKs por padrão.
Impact: Tasks ficam com `category_id` apontando para uma categoria inexistente.
Recommendation: Na mesma transação, desassociar (`category_id = NULL`) as tasks da categoria antes de apagá-la, mantendo status e formato da resposta (Playbook P-09).

### F13 [MEDIUM] APIs deprecated: `datetime.utcnow()` e `Query.get()`
File: models/task.py:15-16, 52
File: models/user.py:14
File: models/category.py:11
File: routes/task_routes.py:31, 42, 51, 67, 72, 117, 122, 158, 188, 195, 215, 227, 285
File: routes/user_routes.py:29, 94, 136, 155, 172
File: routes/report_routes.py:35, 42, 45, 71, 105, 133, 192, 214
File: services/notification_service.py:35
File: utils/helpers.py:38
File: seed.py:66-74
Catalog: AP-DEP — APIs Deprecated / Obsoletas
Description: `datetime.utcnow()` é deprecated no Python 3.12 (emite `DeprecationWarning`); `Model.query.get(id)` é API legada no SQLAlchemy 2.x (emite `LegacyAPIWarning`).
Impact: Warnings em runtime e quebra na remoção futura dessas APIs.
Recommendation: `datetime.now(timezone.utc)` (gravando naive UTC para manter o formato) e `db.session.get(Model, id)` (Playbook P-11).

### F14 [LOW] `print` usado como log
File: routes/task_routes.py:149, 153, 219, 234
File: routes/user_routes.py:83, 89, 147
File: services/notification_service.py:21, 24
File: utils/helpers.py:39-41
Catalog: AP-17 — `print` / `console.log` como Log
Description: Eventos e erros registrados com `print(f"Task criada: ...")`, `print(f"ERRO: {str(e)}")`.
Impact: Sem nível, sem timestamp padronizado, sem como desligar/redirecionar.
Recommendation: Módulo `logging` configurado no composition root (Playbook P-14).

### F15 [LOW] Magic numbers / strings e constantes não usadas
File: routes/task_routes.py:96-104, 110-114, 177, 182
File: routes/user_routes.py:52, 64, 71, 115, 120
File: routes/report_routes.py:24-28, 129, 180
File: utils/helpers.py:110-116
Catalog: AP-18 — Magic Numbers / Strings
Description: Listas `['pending', 'in_progress', 'done', 'cancelled']` e `['user', 'admin', 'manager']` inline, faixas `1..5`, `3`/`200`, `< 4` para senha, `priority <= 2` como "alta", `'#000000'`; enquanto `VALID_STATUSES`, `VALID_ROLES`, `MIN_PASSWORD_LENGTH` etc. estão definidas em `helpers.py` e não são usadas.
Impact: Mudar uma regra exige caçar literais espalhados.
Recommendation: Constantes nomeadas nos models (Playbook P-12).

### F16 [LOW] Nomenclatura ruim
File: routes/report_routes.py:24-28
File: routes/task_routes.py:16, 51, 268
File: models/category.py:14
Catalog: AP-19 — Nomenclatura Ruim
Description: `p1`..`p5`, `t`, `u`, `c`, `cat`, `d`, `e`.
Impact: Leitura mais difícil.
Recommendation: Renomear ao mover o código (Playbook P-04).

### F17 [LOW] Código morto, imports e dependências não usados
File: app.py:7
File: routes/task_routes.py:7
File: routes/user_routes.py:6
File: routes/report_routes.py:7-8
File: models/task.py:3, 38-48
File: models/user.py:34-38
File: utils/helpers.py:3-7, 9-116
File: services/notification_service.py:1-48
File: requirements.txt:4-5
Catalog: AP-20 — Código Morto / Imports Não Usados
Description: `import os, sys, json` (app.py), `json, os, sys, time` (task_routes), `hashlib, json` (user_routes), `format_date, calculate_percentage, json` (report_routes), `json` (task.py), `os, json, sys, math, hashlib` (helpers); `Task.validate_status/validate_priority`, `User.is_admin`, quase todo `helpers.py` e o `NotificationService` inteiro nunca chamados; `marshmallow` e `requests` declarados e não usados.
Impact: Ruído e superfície de manutenção inútil.
Recommendation: Apagar o que não for reaproveitado na refatoração.

### F18 [LOW] Condicionais verbosas / redundantes
File: models/task.py:38-60
File: models/user.py:34-38
File: utils/helpers.py:21-23, 53-55
File: routes/task_routes.py:141, 210
Catalog: AP-21 — Condicionais Verbosas / Redundantes
Description: `if ...: return True else: return False`, pirâmide de 3 `if` aninhados em `is_overdue`, `type(tags) == list`.
Impact: Leitura mais difícil.
Recommendation: Retornar a expressão booleana; usar `isinstance`.

## Deprecated APIs
| Location | Deprecated usage | Modern equivalent |
|---|---|---|
| models/task.py:15-16, 52; models/user.py:14; models/category.py:11; routes/task_routes.py:31, 72, 215, 285; routes/user_routes.py:172; routes/report_routes.py:35, 42, 45, 71, 133; services/notification_service.py:35; utils/helpers.py:38; seed.py:66-74 | `datetime.utcnow()` (Python 3.12) | `datetime.now(timezone.utc)` |
| routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227; routes/user_routes.py:29, 94, 136, 155; routes/report_routes.py:105, 192, 214 | `Model.query.get(id)` (SQLAlchemy 2.1) | `db.session.get(Model, id)` |

## Architecture Notes
- Current: Parcialmente em camadas — há pastas `models/`, `routes/`, `services/`, `utils/`, mas as rotas fazem queries, validação, regras e serialização; `services/` e `utils/` não são usados; config inline em `app.py`.
- Missing layers: config | controllers | error handling | composition root
- Proposed target: reorganização no lugar — `config.py` + `models/` (com serialização e regras de domínio) + `controllers/` por domínio + `routes/` finos (blueprints) + `middlewares/` (erros, auth) + `create_app()` em `app.py`.

================================
Total: 18 findings
================================

## Errata (Fase 3)
- F12: na validação ficou comprovado que o backref `Category.tasks` do ORM já zera `category_id` das tasks ao apagar a categoria via `db.session.delete` — não havia órfãos na prática. A desassociação passou a ser explícita (`Task.detach_category`) na mesma transação; severidade real: LOW.
