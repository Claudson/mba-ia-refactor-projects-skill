================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.12.10 + Flask 3.1.1 (SQLite via sqlite3 / SQL puro)
Files:   4 analyzed | ~780 lines of code
Date:    2026-10-23

## Summary
CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 5

| # | Severity | Finding | Catalog | Location |
|---|---|---|---|---|
| F01 | CRITICAL | SECRET_KEY hardcoded no código | AP-01 | app.py:7 |
| F02 | CRITICAL | SQL Injection em todo o acesso a dados | AP-02 | models.py:28 |
| F03 | CRITICAL | Endpoints administrativos sem autenticação (SQL arbitrário e reset do banco) | AP-05 | app.py:47-78 |
| F04 | CRITICAL | Senhas armazenadas e comparadas em texto puro | AP-03 | models.py:109-111 |
| F05 | CRITICAL | Senhas, segredos, config e exceções expostos nas respostas | AP-04 | models.py:83 |
| F06 | CRITICAL | God Module: models.py e database.py concentram todas as responsabilidades | AP-06 | models.py:1-314 |
| F07 | HIGH | Debug ligado, bind 0.0.0.0 e CORS irrestrito hardcoded | AP-07 | app.py:8 |
| F08 | HIGH | Regras de negócio espalhadas em controllers e models | AP-08 | controllers.py:24-62 |
| F09 | HIGH | Alto acoplamento ao módulo de banco (sem injeção de dependência) | AP-09 | models.py:1 |
| F10 | HIGH | Conexão global mutável compartilhada entre threads | AP-10 | database.py:4-10 |
| F11 | HIGH | Criação de pedido não atômica (sem transação/rollback) | AP-11 | models.py:133-169 |
| F12 | MEDIUM | Validação de entrada ausente ou fraca | AP-14 | controllers.py:37-50 |
| F13 | MEDIUM | try/except genérico em todo handler e nenhum handler central de erros | AP-15 | controllers.py:6-12 |
| F14 | MEDIUM | Mapeamentos e validações duplicados | AP-13 | models.py:12-21 |
| F15 | MEDIUM | Exclusão de produto deixa itens de pedido órfãos | AP-16 | models.py:65-70 |
| F16 | MEDIUM | Queries N+1 na listagem de pedidos e no relatório | AP-12 | models.py:186-199 |
| F17 | LOW | `print` usado como log e como "notificação" | AP-17 | controllers.py:8 |
| F18 | LOW | Magic numbers e listas de valores inline | AP-18 | controllers.py:52 |
| F19 | LOW | Nomenclatura ruim (`id` sombreando built-in, `cursor2`, `cursor3`, `prod`) | AP-19 | models.py:24 |
| F20 | LOW | Imports não usados e código morto | AP-20 | database.py:2 |
| F21 | LOW | Condicionais redundantes | AP-21 | controllers.py:200 |

## Findings

### F01 [CRITICAL] SECRET_KEY hardcoded no código
File: app.py:7
File: controllers.py:289
Catalog: AP-01 — Credenciais / Segredos Hardcoded
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` é um literal no código-fonte e o mesmo valor é repetido literalmente na resposta do `/health` (`"secret_key": "minha-chave-super-secreta-123"`).
Impact: Qualquer pessoa com acesso ao repositório (ou a `GET /health`) conhece a chave usada para assinar sessões/tokens do Flask, podendo forjá-los; a chave não pode ser trocada por ambiente sem alterar código.
Recommendation: Criar um módulo de configuração que lê `SECRET_KEY` de variável de ambiente (com default apenas de desenvolvimento), carregá-lo na composition root e documentar a variável em `.env.example`; nenhum literal de segredo permanece no código (Playbook P-01).

### F02 [CRITICAL] SQL Injection em todo o acesso a dados
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-297
Catalog: AP-02 — SQL Injection
Description: Todas as queries são montadas por concatenação de strings, ex.: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`, `"INSERT INTO produtos ... VALUES ('" + nome + "', '" + descricao + "', ..."` e `" AND (nome LIKE '%" + termo + "%' ..."` na busca.
Impact: `POST /login` com email `' OR 1=1 --` autentica como o primeiro usuário (admin) sem senha; `GET /produtos/busca?q=' UNION SELECT ...` lê qualquer tabela; `POST /produtos` e `POST /usuarios` permitem injetar SQL pelos campos de texto (e quebram com qualquer apóstrofo legítimo, ex.: `Monitor 27''`).
Recommendation: Reescrever todo acesso a dados com queries parametrizadas (placeholders `?` + tupla de parâmetros), inclusive os filtros dinâmicos da busca (`LIKE ?` com `%termo%` como parâmetro) (Playbook P-02).

### F03 [CRITICAL] Endpoints administrativos sem autenticação (SQL arbitrário e reset do banco)
File: app.py:47-57, 59-78
Catalog: AP-05 — Endpoints Perigosos sem Proteção / Autenticação Quebrada
Description: `POST /admin/query` executa o SQL enviado no corpo (`cursor.execute(query)` com `dados.get("sql")`) e `POST /admin/reset-db` apaga `itens_pedido`, `pedidos`, `produtos` e `usuarios` — ambos sem qualquer verificação de autenticação.
Impact: Qualquer cliente anônimo pode ler a tabela `usuarios` inteira (com senhas), alterar preços/estoques, criar admins ou apagar todos os dados da loja com uma única requisição.
Recommendation: Rota a rota: **remover** `POST /admin/query` por completo — rota, handler e código exclusivo dela, sem versão "restrita" (Playbook P-13a); **manter e proteger** `POST /admin/reset-db` exigindo o header `X-Admin-Token` igual a `ADMIN_TOKEN` lido da config (comparação com `hmac.compare_digest`), respondendo `401` sem token válido e `403` quando `ADMIN_TOKEN` não estiver configurado (Playbook P-13b).

### F04 [CRITICAL] Senhas armazenadas e comparadas em texto puro
File: models.py:109-111, 126-129
File: database.py:75-83
Catalog: AP-03 — Armazenamento Inseguro de Senhas
Description: `criar_usuario` grava `senha` exatamente como veio da requisição; `login_usuario` compara `WHERE ... AND senha = '" + senha + "'"`; o seed grava `"admin123"`, `"123456"`, `"senha123"` em claro.
Impact: Qualquer vazamento do banco (ou do endpoint de SQL / listagem de usuários) entrega as senhas reais de todos os clientes, reutilizáveis em outros serviços.
Recommendation: Gravar `generate_password_hash(senha)` (`werkzeug.security`, já instalado com o Flask) na criação e no seed; no login, buscar o usuário por email (query parametrizada) e validar com `check_password_hash`; no boot, converter para hash as senhas legadas ainda em texto puro no banco existente (Playbook P-07).

### F05 [CRITICAL] Senhas, segredos, config e exceções expostos nas respostas
File: models.py:83, 99
File: controllers.py:12, 22, 62, 96, 109, 126, 134, 144, 165, 186, 220, 227, 235, 255, 262, 285-292
File: app.py:78
Catalog: AP-04 — Exposição de Dados Sensíveis
Description: Os dicts de usuário incluem `"senha": row["senha"]`, devolvidos por `GET /usuarios` e `GET /usuarios/<id>`; `GET /health` devolve `"secret_key"`, `"db_path": "loja.db"`, `"debug": True` e `"ambiente": "producao"`; todos os handlers devolvem `{"erro": str(e)}` (ou `"detalhes": str(e)`) em erros 500.
Impact: Um `GET /usuarios` anônimo entrega email e senha de todos os usuários; `/health` entrega a chave de assinatura e detalhes da infraestrutura; mensagens de exceção vazam nomes de tabelas/colunas e trechos de SQL que facilitam a exploração do F02.
Recommendation: Serializar usuários apenas com campos públicos (`id`, `nome`, `email`, `tipo`, `criado_em`), removendo `senha` de toda resposta (Playbook P-08); `/health` passa a devolver apenas `status`, `database`, `counts` e `versao` — sem `secret_key`, `db_path`, `debug` e `ambiente` (Playbook P-08); erros 500 passam a responder uma mensagem genérica (`{"erro": "Erro interno do servidor"}`) com o detalhe apenas no log (Playbook P-10).

### F06 [CRITICAL] God Module: models.py e database.py concentram todas as responsabilidades
File: models.py:1-314
File: database.py:7-86
Catalog: AP-06 — God Class / God Module
Description: `models.py` (314 linhas) mistura SQL dos três domínios (produtos, usuários, pedidos), regras de negócio (checagem de estoque e cálculo de total em `criar_pedido` linhas 139-146, faixas de desconto em `relatorio_vendas` linhas 256-262) e formatação JSON; `database.py::get_db()` faz conexão, criação de schema e seed na mesma função.
Impact: Qualquer mudança num domínio exige editar o mesmo arquivo dos outros; regras de negócio não podem ser testadas sem banco; o schema e o seed rodam escondidos na primeira chamada de qualquer query.
Recommendation: Separar em camadas MVC: `config/` (configuração), `database.py` (só conexão + `init_db` explícito), `models/` por domínio (`produto_model`, `usuario_model`, `pedido_model` — só acesso a dados), `services/` para regras de pedido/relatório/notificação, `controllers/` por domínio, `views/` com Blueprints por domínio e `app.py` como composition root (`create_app`) (Playbook P-03 + P-04).

### F07 [HIGH] Debug ligado, bind 0.0.0.0 e CORS irrestrito hardcoded
File: app.py:8, 9, 88
Catalog: AP-07 — Modo Debug / Configuração de Runtime Insegura
Description: `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)` ligam o debugger do Werkzeug em todas as interfaces; `CORS(app)` libera qualquer origem; nada disso pode ser alterado sem editar o código.
Impact: Com o servidor exposto na rede, o console interativo do debugger e os tracebacks completos ficam acessíveis a terceiros; qualquer site pode chamar a API pelo navegador do usuário.
Recommendation: Ler `DEBUG` (default `false`), `HOST` (default `127.0.0.1`), `PORT` (default `5000`) e `CORS_ORIGINS` (lista separada por vírgula) do módulo de configuração via variáveis de ambiente, usá-los em `app.run`/`CORS(..., origins=...)` e documentá-los em `.env.example` (Playbook P-01).

### F08 [HIGH] Regras de negócio espalhadas em controllers e models
File: controllers.py:24-62, 64-96, 188-220, 237-255
File: models.py:139-146, 256-262
Catalog: AP-08 — Regra de Negócio nas Rotas / Fat Controllers
Description: `criar_produto`/`atualizar_produto` fazem toda a validação inline; `criar_pedido` (controller) orquestra o fluxo e dispara "notificações" (`print("ENVIANDO EMAIL...")`, SMS, PUSH, linhas 208-210); `atualizar_status_pedido` contém as reações de negócio a `aprovado`/`cancelado` (linhas 247-250); o model calcula total/estoque (139-146) e as faixas de desconto do relatório (256-262).
Impact: Não há um lugar único para as regras de pedido e faturamento; testar o cálculo de desconto ou o fluxo de pedido exige HTTP + banco; as notificações estão acopladas ao handler.
Recommendation: Extrair `services/pedido_service.py` (validação de itens, checagem de estoque, cálculo de total, criação transacional), `services/relatorio_service.py` (faixas de desconto e métricas), `services/notification_service.py` (notificações de pedido criado/aprovado/cancelado) e `validators/` para os payloads; controllers apenas recebem a requisição, chamam validator/service e devolvem a resposta (Playbook P-04).

### F09 [HIGH] Alto acoplamento ao módulo de banco (sem injeção de dependência)
File: models.py:1, 5, 25, 44, 55, 66, 73, 90, 106, 123, 134, 172, 204, 236, 276, 286
File: controllers.py:3, 266-274
Catalog: AP-09 — Alto Acoplamento / Sem Injeção de Dependência
Description: Toda função de model chama `get_db()` do módulo global (que também cria schema e seed); o controller `health_check` importa `get_db` e executa SQL diretamente (`cursor.execute("SELECT COUNT(*) FROM produtos")` ...).
Impact: Impossível trocar o banco ou usar um banco de teste sem monkeypatch; o controller conhece SQL, quebrando a separação de camadas.
Recommendation: `database.py` fornece a conexão da requisição (`get_db()` sobre `flask.g`) e `init_db(app)` explícito chamado pela composition root; as contagens do `/health` vão para funções de model; controllers nunca importam o módulo de banco (Playbook P-03 / P-06).

### F10 [HIGH] Conexão global mutável compartilhada entre threads
File: database.py:4-5, 8-11
Catalog: AP-10 — Estado Global Mutável
Description: `db_connection = None` em nível de módulo, alterada via `global db_connection` e aberta com `sqlite3.connect(db_path, check_same_thread=False)` — uma única conexão para todas as requisições/threads; `db_path = "loja.db"` fixo.
Impact: Requisições concorrentes compartilham o mesmo estado de transação (um `commit()` de uma requisição grava escritas pendentes de outra; uma falha deixa a conexão suja para as seguintes); o caminho do banco não é configurável.
Recommendation: Abrir uma conexão por requisição guardada em `flask.g` e fechada em `teardown_appcontext`, com o caminho do banco vindo da config (`DATABASE_PATH`) (Playbook P-06).

### F11 [HIGH] Criação de pedido não atômica (sem transação/rollback)
File: models.py:133-169
Catalog: AP-11 — Escritas Multi-etapa Não Atômicas / Callback Hell
Description: `criar_pedido` faz `INSERT INTO pedidos`, depois em loop `INSERT INTO itens_pedido` e `UPDATE produtos SET estoque = estoque - ...`, com um único `db.commit()` no final e nenhum rollback; a checagem de estoque (linha 144) é feita antes e separada do decremento.
Impact: Uma exceção no meio do loop (ex.: item sem `quantidade`) deixa pedido/itens parciais pendentes na conexão compartilhada, que são gravados pelo próximo `commit()` de outra requisição; dois pedidos simultâneos podem vender o mesmo estoque.
Recommendation: Validar todos os itens primeiro e gravar pedido, itens e baixa de estoque dentro de uma única transação (`with conn:` — commit ou rollback atômico), com o decremento condicionado (`UPDATE ... SET estoque = estoque - ? WHERE id = ? AND estoque >= ?`, abortando a transação se nenhuma linha for afetada) (Playbook P-09).

### F12 [MEDIUM] Validação de entrada ausente ou fraca
File: controllers.py:37-50, 81-90, 113-121, 169-171, 195-201, 239-240
Catalog: AP-14 — Validação de Entrada Ausente ou Fraca
Description: `preco < 0`/`estoque < 0` sobre valores não tipados (string → `TypeError` → 500); `atualizar_produto` não valida tamanho do nome nem categoria; `float(preco_min)` com texto → 500; `login` e `atualizar_status_pedido` chamam `dados.get(...)` sem tratar body ausente (`None` → 500); os itens do pedido não são validados (`item["produto_id"]` ausente → `KeyError` → 500; `quantidade` negativa ou zero é aceita e **aumenta** o estoque); `usuario_id` não é verificado.
Impact: Entradas inválidas viram 500 com mensagem de exceção em vez de 400; quantidades negativas permitem pedidos de total negativo e manipulação de estoque; pedidos são criados para usuários inexistentes.
Recommendation: Criar validadores na borda dos controllers (`validators/produto_validator.py`, `usuario_validator.py`, `pedido_validator.py`) que checam presença, tipo e faixa (`preco`/`estoque` numéricos não negativos, `quantidade` inteira > 0, `produto_id` presente, body JSON obrigatório, filtros de preço numéricos) e respondem `400` no formato atual `{"erro": ...}`; aplicar a mesma validação de nome/categoria em criar e atualizar; rejeitar com `400` (`"Usuário não encontrado"`) pedido para `usuario_id` inexistente (Playbook P-12).

### F13 [MEDIUM] try/except genérico em todo handler e nenhum handler central de erros
File: controllers.py:6-12, 15-22, 25-62, 65-96, 99-109, 112-126, 129-134, 137-144, 147-165, 168-186, 189-220, 223-227, 230-235, 238-255, 258-262, 265-292
File: app.py:6-30
Catalog: AP-15 — Tratamento de Erros Engolido / Inconsistente
Description: Cada handler repete `try: ... except Exception as e: return jsonify({"erro": str(e)}), 500`; não existe `@app.errorhandler`, então 404/405 do roteamento saem como página HTML do Flask; o formato de erro é inconsistente (às vezes com `"sucesso": False`, às vezes sem; `/health` usa `"detalhes"`).
Impact: Bugs de programação viram respostas 500 silenciosas sem log estruturado; clientes recebem HTML em rotas inexistentes; a mesma estrutura é duplicada 16 vezes.
Recommendation: Remover os try/except dos handlers e registrar um handler central (`middlewares/error_handler.py`) com uma exceção de aplicação (`AppError(mensagem, status)`), um handler para `HTTPException` (404/405 em JSON `{"erro": ...}`) e um handler para `Exception` que loga o traceback e responde `500` genérico (Playbook P-10).

### F14 [MEDIUM] Mapeamentos e validações duplicados
File: models.py:12-21, 31-40, 304-313, 79-86, 95-102, 178-200, 211-232
File: controllers.py:28-46, 72-90
Catalog: AP-13 — Código / Lógica Duplicada
Description: O mapeamento linha→dict de produto aparece 3 vezes, o de usuário 2 vezes; `get_pedidos_usuario` e `get_todos_pedidos` têm o mesmo corpo de montagem de pedidos+itens (só muda o `WHERE`); o bloco de validação de produto é copiado entre `criar_produto` e `atualizar_produto` (com divergência: o update não valida nome/categoria).
Impact: Correções precisam ser replicadas em vários pontos e já divergiram (validação de update mais fraca).
Recommendation: Fonte única: um serializer por entidade no model (`_to_dict`/`to_public_dict`), uma única função de carregamento de pedidos com filtro opcional por usuário e um único validador de produto usado em criar e atualizar (Playbook P-12).

### F15 [MEDIUM] Exclusão de produto deixa itens de pedido órfãos
File: models.py:65-70, 196, 228
File: database.py:46-52
Catalog: AP-16 — Dados Órfãos / Integridade Referencial Ausente
Description: `deletar_produto` executa `DELETE FROM produtos WHERE id = ...` sem tratar `itens_pedido` que o referenciam; a tabela `itens_pedido` não declara FK; a listagem de pedidos já admite dados sujos (`prod["nome"] if prod else "Desconhecido"`).
Impact: Após excluir um produto vendido, o histórico de pedidos perde o nome do produto e os itens apontam para um id inexistente; o histórico fiscal fica inconsistente.
Recommendation: Corrigir sem mudar a resposta do endpoint usando exclusão lógica: `DELETE /produtos/<id>` passa a marcar `ativo = 0`; listagem, busca, detalhe, atualização, criação de pedido e contagem do `/health` consideram apenas produtos com `ativo = 1` (produto excluído continua respondendo `404`), enquanto a listagem de pedidos continua resolvendo o nome do produto do histórico (Playbook P-09).

### F16 [MEDIUM] Queries N+1 na listagem de pedidos e no relatório
File: models.py:186-199, 219-231, 154-156, 239-254
Catalog: AP-12 — Queries N+1
Description: Para cada pedido é feita uma query de itens (`cursor2`) e, para cada item, uma query do nome do produto (`cursor3`); `criar_pedido` relê `SELECT preco FROM produtos` por item já lido antes; `relatorio_vendas` faz 5 queries separadas (`COUNT`, `SUM`, 3× `COUNT ... WHERE status = ...`).
Impact: `GET /pedidos` com N pedidos e M itens executa 1 + N + N·M queries; o tempo de resposta cresce linearmente com o histórico.
Recommendation: Carregar pedidos e itens com uma query `JOIN itens_pedido` + `LEFT JOIN produtos` agrupada em memória; reaproveitar os preços já lidos em `criar_pedido`; calcular o relatório com uma única query agregada (`COUNT`, `COALESCE(SUM(total), 0)`, `SUM(CASE WHEN status = ... )`) (Playbook P-05).

### F17 [LOW] `print` usado como log e como "notificação"
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
File: app.py:56, 83-86
Catalog: AP-17 — `print` / `console.log` como Log
Description: Eventos e erros são registrados com `print("ERRO: " + str(e))`, `print("Login falhou: " + email)`, `print("ENVIANDO EMAIL: ...")` e banner `print("SERVIDOR INICIADO")`.
Impact: Sem níveis, timestamps nem destino configurável; impossível filtrar erros em produção.
Recommendation: Criar um módulo `logger` (biblioteca `logging`, nível via config `LOG_LEVEL`) e substituir todos os `print`; as notificações passam a ser registradas pelo `notification_service` através do logger (Playbook P-14).

### F18 [LOW] Magic numbers e listas de valores inline
File: controllers.py:47-50, 52, 242
File: models.py:247-253, 256-262
Catalog: AP-18 — Magic Numbers / Strings
Description: Limites `len(nome) < 2` / `> 200`, a lista `categorias_validas` inline, a lista de status `["pendente", "aprovado", "enviado", "entregue", "cancelado"]` inline, strings de status repetidas nas queries do relatório e faixas de desconto `> 10000 → 0.1`, `> 5000 → 0.05`, `> 1000 → 0.02`.
Impact: Regras de negócio sem nome nem fonte única; mudar uma categoria ou faixa exige caçar literais.
Recommendation: Constantes nomeadas no model/service (`NOME_MIN`, `NOME_MAX`, `CATEGORIAS_VALIDAS`, `STATUS_VALIDOS`, `FAIXAS_DESCONTO`) usadas por validators e services (Playbook P-12).

### F19 [LOW] Nomenclatura ruim (`id` sombreando built-in, `cursor2`, `cursor3`, `prod`)
File: models.py:24, 54, 65, 89, 187-193, 219-225
File: controllers.py:14, 56, 64, 98, 136, 160
Catalog: AP-19 — Nomenclatura Ruim
Description: Parâmetros e variáveis chamados `id` (sombreando o built-in), cursores numerados `cursor2`/`cursor3` e abreviação `prod`.
Impact: Legibilidade baixa e risco de bug ao usar `id()` no mesmo escopo.
Recommendation: Renomear ao mover o código (`produto_id`, `usuario_id`, `pedido_id`, `produto`), sem mudar os paths das rotas (Playbook P-03/P-04).

### F20 [LOW] Imports não usados e código morto
File: database.py:2
File: models.py:2, 63, 70, 283
File: controllers.py:268
Catalog: AP-20 — Código Morto / Imports Não Usados
Description: `import os` e `import sqlite3` nunca usados; `return True` em `atualizar_produto`, `deletar_produto` e `atualizar_status_pedido` nunca é lido; `cursor.execute("SELECT 1")` no health é descartado.
Impact: Ruído que sugere dependências e contratos inexistentes.
Recommendation: Apagar imports, retornos e queries sem uso (Playbook P-03).

### F21 [LOW] Condicionais redundantes
File: controllers.py:200
File: models.py:244-245
Catalog: AP-21 — Condicionais Verbosas / Redundantes
Description: `if not itens or len(itens) == 0` (a segunda condição é implicada pela primeira); `if faturamento is None: faturamento = 0` após `SUM(total)`.
Impact: Código mais longo sem ganho; lógica que pertence à query.
Recommendation: Usar apenas `if not itens` e `COALESCE(SUM(total), 0)` na query (Playbook P-12).

## Deprecated APIs
None detected for Python 3.12.10 + Flask 3.1.1 + flask-cors 5.0.1 + sqlite3 (stdlib).

## Architecture Notes
- Current: Monolítica / sem camadas — rotas em `app.py`, handlers com validação e SQL em `controllers.py`, um `models.py` com SQL + regras de negócio dos três domínios e `database.py` misturando conexão, schema e seed; separação só no nome dos arquivos.
- Missing layers: config | services | validators | views/routes (Blueprints) | error handling | composition root
- Proposed target: `src/` com `config/settings.py`, `database.py`, `models/` por domínio, `validators/`, `services/`, `controllers/`, `views/` (Blueprints), `middlewares/` (auth admin + error handler), `logger.py` e `app.py` com `create_app()`; `app.py` na raiz apenas sobe a aplicação.

================================
Total: 21 findings
================================
