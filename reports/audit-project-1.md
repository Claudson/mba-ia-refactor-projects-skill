================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.12.10 + Flask 3.1.1 (SQLite via driver sqlite3, SQL puro)
Files:   4 analyzed | ~780 lines of code
Date:    2026-10-10

## Summary
CRITICAL: 7 | HIGH: 4 | MEDIUM: 5 | LOW: 5

| # | Severity | Finding | Catalog | Location |
|---|---|---|---|---|
| F01 | CRITICAL | Segredo de aplicação hardcoded e devolvido pela API | AP-01 | app.py:7 |
| F02 | CRITICAL | SQL Injection em toda a camada de dados | AP-02 | models.py:28 |
| F03 | CRITICAL | Senhas armazenadas e comparadas em texto puro | AP-03 | models.py:126-129 |
| F04 | CRITICAL | Exposição de senhas, config interna e stack traces nas respostas | AP-04 | models.py:84 |
| F05 | CRITICAL | Endpoints administrativos destrutivos sem autenticação | AP-05 | app.py:59-78 |
| F06 | CRITICAL | Modo debug ligado com bind público e segredos expostos | AP-07 | app.py:8 |
| F07 | CRITICAL | God Module: models.py acumula dados, regra de negócio e serialização | AP-06 | models.py:1-314 |
| F08 | HIGH | Regra de negócio e efeitos colaterais nos controllers | AP-08 | controllers.py:24-62 |
| F09 | HIGH | Alto acoplamento ao módulo de banco, sem injeção de dependência | AP-09 | models.py:5 |
| F10 | HIGH | Conexão global mutável compartilhada entre threads | AP-10 | database.py:4-11 |
| F11 | HIGH | Criação de pedido não atômica e sem rollback | AP-11 | models.py:133-169 |
| F12 | MEDIUM | Queries N+1 na listagem de pedidos e no relatório | AP-12 | models.py:187-199 |
| F13 | MEDIUM | Mapeamento linha→dict e validações duplicados | AP-13 | models.py:12-21 |
| F14 | MEDIUM | Validação de entrada ausente ou fraca | AP-14 | controllers.py:39-46 |
| F15 | MEDIUM | Tratamento de erros repetido, sem handler central | AP-15 | controllers.py:10-12 |
| F16 | MEDIUM | Sem integridade referencial: dados órfãos ao apagar | AP-16 | database.py:37-53 |
| F17 | LOW | `print` usado como log de aplicação | AP-17 | controllers.py:8 |
| F18 | LOW | Magic numbers e listas de domínio inline | AP-18 | models.py:256-262 |
| F19 | LOW | Nomenclatura ruim (`id` sombreando built-in, `cursor2`/`cursor3`) | AP-19 | models.py:24 |
| F20 | LOW | Imports não utilizados | AP-20 | database.py:2 |
| F21 | LOW | Condicionais verbosas e redundantes | AP-21 | controllers.py:200 |

## Findings

### F01 [CRITICAL] Segredo de aplicação hardcoded e devolvido pela API
File: app.py:7
File: controllers.py:289
Catalog: AP-01 — Credenciais / Segredos Hardcoded
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` é um literal versionado no código (app.py:7). O mesmo valor é devolvido ao cliente em `GET /health`, no campo `"secret_key": "minha-chave-super-secreta-123"` (controllers.py:289).
Impact: Qualquer pessoa com acesso ao repositório — ou apenas a `GET /health`, que é público — obtém a chave usada para assinar sessões e qualquer dado assinado pelo Flask, permitindo forjar sessões/cookies. Rotacionar a chave exige alterar e reimplantar o código.
Recommendation: Externalizar a configuração para variáveis de ambiente (`os.environ`), com `.env.example` documentando `SECRET_KEY`, e falhar o boot se a chave não estiver definida fora de desenvolvimento; remover o campo `secret_key` da resposta de `/health` (Playbook P-01).

### F02 [CRITICAL] SQL Injection em toda a camada de dados
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-299
Catalog: AP-02 — SQL Injection
Description: Nenhuma query usa placeholders; todas são montadas por concatenação de string com valores vindos da requisição. Exemplos: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` (models.py:109-111); `"INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES ('" + nome + "', '" + descricao + "', " + str(preco) + ...` (models.py:47-50); `"UPDATE pedidos SET status = '" + novo_status + "' WHERE id = " + str(pedido_id)` (models.py:279-281); e a busca `" AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"` (models.py:291), cujo `termo` vem direto de `request.args.get("q")` (controllers.py:113).
Impact: `POST /login` com email `' OR 1=1 --` autentica como o primeiro usuário da tabela sem senha válida. `GET /produtos/busca?q=' UNION SELECT ...` lê qualquer tabela, inclusive a coluna `senha` de `usuarios`. Um `nome` de produto contendo apóstrofo já quebra o INSERT (500), e payloads com `;` em `atualizar_status_pedido` permitem escrita arbitrária. Observação: os parâmetros de rota declarados como `<int:id>` são convertidos pelo Flask e não são injetáveis, mas `email`, `senha`, `nome`, `descricao`, `categoria`, `termo`, `novo_status` e os campos de `itens` são todos strings livres do corpo/querystring.
Recommendation: Substituir toda concatenação por queries parametrizadas (`?` + tupla de parâmetros) no repositório de cada agregado, inclusive montando o `WHERE` dinâmico da busca como lista de cláusulas + lista de parâmetros (Playbook P-02).

### F03 [CRITICAL] Senhas armazenadas e comparadas em texto puro
File: models.py:105-120, 126-129
File: database.py:75-83
Catalog: AP-03 — Armazenamento Inseguro de Senhas
Description: `criar_usuario` grava a senha recebida sem qualquer transformação: `"INSERT INTO usuarios (nome, email, senha, tipo) VALUES ('" + nome + "', '" + email + "', '" + senha + "', '" + tipo + "')"` (models.py:126-129). O login compara o texto puro dentro do próprio SQL (`AND senha = '" + senha + "'`, models.py:110). O seed grava `("Admin", "admin@loja.com", "admin123", "admin")` e `"123456"` em claro (database.py:76-78).
Impact: Um vazamento do arquivo `loja.db` — ou a SQL injection do F02, ou simplesmente o `GET /usuarios` do F04 — entrega todas as senhas em claro, incluindo a do usuário `admin`. Como usuários reutilizam senhas, o impacto extrapola a aplicação.
Recommendation: Usar `werkzeug.security.generate_password_hash` / `check_password_hash` (já disponível via Flask, sem nova dependência): hash na criação e verificação em memória no login — o SQL passa a buscar apenas por email (Playbook P-07).

### F04 [CRITICAL] Exposição de senhas, config interna e stack traces nas respostas
File: models.py:79-86, 95-102
File: controllers.py:286-288
File: controllers.py:12, 22, 62, 96, 109, 126, 134, 144, 165, 186, 220, 227, 235, 262, 292
Catalog: AP-04 — Exposição de Dados Sensíveis
Description: `get_todos_usuarios` e `get_usuario_por_id` incluem `"senha": row["senha"]` no dict serializado (models.py:84, 99), então `GET /usuarios` e `GET /usuarios/<id>` devolvem as senhas de todos os usuários sem qualquer autenticação. `GET /health` devolve configuração interna: `"ambiente": "producao"`, `"db_path": "loja.db"`, `"debug": True` (controllers.py:286-288). Além disso, os 15 blocos `except` devolvem `str(e)` ao cliente (ex.: `return jsonify({"erro": str(e)}), 500`, controllers.py:12).
Impact: `curl http://host/usuarios` é um dump completo de credenciais. O `str(e)` de erros de SQLite revela nomes de tabelas, colunas e trechos da query montada, dando ao atacante o mapa do schema para explorar o F02.
Recommendation: Criar serializadores explícitos por entidade que nunca exponham `senha`, reduzir `/health` a `status` + checagem de banco, e centralizar o tratamento de erros devolvendo mensagem genérica ao cliente e o detalhe apenas no log (Playbook P-08 + P-10).

### F05 [CRITICAL] Endpoints administrativos destrutivos sem autenticação
File: app.py:59-78
File: app.py:47-57
File: controllers.py:167-186
Catalog: AP-05 — Endpoints Perigosos sem Proteção / Autenticação Quebrada
Description: `POST /admin/query` executa SQL arbitrário enviado no corpo: `query = dados.get("sql", "")` seguido de `cursor.execute(query)` (app.py:62-69), devolvendo o resultado de SELECTs e commitando qualquer outro comando. `POST /admin/reset-db` apaga as quatro tabelas (`DELETE FROM itens_pedido/pedidos/produtos/usuarios`, app.py:51-54). Nenhuma das duas rotas verifica autenticação ou perfil — e o `POST /login` (controllers.py:167-186) não emite token nem sessão, de modo que *nenhum* endpoint do projeto é protegido.
Impact: Um único `curl -X POST http://host/admin/query -d '{"sql":"DROP TABLE usuarios"}'` destrói os dados; um `SELECT` arbitrário exfiltra tudo. `POST /admin/reset-db` sem corpo zera a base. Combinado ao F06 (bind em `0.0.0.0`), isso é acesso administrativo total a quem alcança a porta 5000.
Recommendation: Remover `/admin/query` (não há uso legítimo de execução de SQL arbitrário via HTTP) e proteger `/admin/reset-db` com checagem de token administrativo lido da configuração, mantendo rota, método e formato de resposta para os chamadores autorizados (Playbook P-13).

### F06 [CRITICAL] Modo debug ligado com bind público e segredos expostos
File: app.py:8, 88
File: app.py:9
Catalog: AP-07 — Modo Debug / Configuração de Runtime Insegura
Description: `app.config["DEBUG"] = True` (app.py:8) e `app.run(host="0.0.0.0", port=5000, debug=True)` (app.py:88) são valores fixos, sem leitura de ambiente. `CORS(app)` (app.py:9) libera a origem `*` para todas as rotas, incluindo `/login` e `/admin/*`. O próprio `/health` se anuncia como `"ambiente": "producao"` (controllers.py:286).
Impact: O debugger interativo do Werkzeug fica servido em todas as interfaces de rede; qualquer exceção não tratada expõe código-fonte e variáveis locais, e o console do debugger permite execução de código Python no servidor. O catálogo trata AP-07 como CRITICAL justamente quando os stack traces são publicamente acessíveis *e* combinados com segredos — é o caso aqui (F01 e F04). O CORS aberto ainda permite que qualquer site dispare as chamadas administrativas pelo navegador da vítima.
Recommendation: Ler `DEBUG`, `HOST`, `PORT` e a lista de origens permitidas do ambiente, com padrões seguros (debug desligado, bind em `127.0.0.1`, CORS restrito por `CORS_ORIGINS`) (Playbook P-01).

### F07 [CRITICAL] God Module: models.py acumula dados, regra de negócio e serialização
File: models.py:1-314
File: database.py:7-86
File: app.py:1-88
Catalog: AP-06 — God Class / God Module
Description: `models.py` tem 314 linhas e cobre os três domínios ao mesmo tempo (produtos, usuários, pedidos), misturando numa mesma função SQL, regra de negócio e formatação de resposta: `criar_pedido` valida estoque, calcula `total`, insere pedido e itens e dá baixa no estoque (models.py:133-169); `relatorio_vendas` executa cinco queries e aplica a política de desconto por faixa de faturamento (models.py:235-273); todas as funções de leitura montam o dict de resposta campo a campo. `database.py` concentra conexão + criação de schema + seed na mesma função `get_db()` (database.py:7-86). `app.py` acumula configuração, registro das 19 rotas e dois handlers que acessam o banco diretamente (app.py:47-78).
Impact: Nenhuma responsabilidade é testável isoladamente: exercitar a regra de desconto exige um banco real com pedidos; importar `models` já carrega o módulo de banco. Qualquer mudança de persistência (SQLite → outro engine) obriga a reescrever a regra de negócio, e vice-versa. Os nomes `models.py`/`controllers.py` dão a falsa impressão de camadas que não existem.
Recommendation: Separar em camadas reais — `config/`, `models/` (repositórios por agregado, só SQL parametrizado), `services/` (regra de negócio: estoque, totais, descontos, status), `controllers/` (HTTP), `routes/` (blueprints) — e mover conexão, schema e seed para módulos distintos (Playbook P-03 + P-04).

### F08 [HIGH] Regra de negócio e efeitos colaterais nos controllers
File: controllers.py:24-62, 64-96, 111-126, 188-220, 237-255, 264-292
File: app.py:47-57, 59-78
Catalog: AP-08 — Regra de Negócio nas Rotas / Fat Controllers
Description: `criar_produto` (39 linhas) embute as regras de domínio: faixas de `preco`/`estoque`, limites de tamanho de nome (`len(nome) < 2`, `> 200`) e a lista de categorias válidas `["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]` (controllers.py:43-54). `criar_pedido` dispara as notificações dentro do handler (`print("ENVIANDO EMAIL: ...")`, `"ENVIANDO SMS"`, `"ENVIANDO PUSH"`, controllers.py:208-210) e `atualizar_status_pedido` decide as ações por status (controllers.py:247-250). `health_check` executa SQL cru no handler (controllers.py:266-274), assim como os dois handlers administrativos (app.py:49-55 e 66-76).
Impact: As mesmas regras não podem ser reaproveitadas por outro ponto de entrada (CLI, job, outra rota) e já estão divergindo: `atualizar_produto` repete as validações de preço/estoque mas esqueceu as de nome e categoria (controllers.py:87-90), de modo que um PUT aceita nome vazio e categoria inválida que o POST rejeita. Testar a regra de notificação exige subir o Flask e um banco.
Recommendation: Extrair as regras para serviços de domínio (`ProdutoService`, `PedidoService`) e um serviço de notificação injetado; o controller passa a validar o contrato HTTP, delegar e traduzir o resultado em status code (Playbook P-04).

### F09 [HIGH] Alto acoplamento ao módulo de banco, sem injeção de dependência
File: models.py:5, 25, 44, 55, 66, 73, 90, 106, 123, 134, 172, 204, 236, 276, 286
File: controllers.py:3, 266
File: app.py:4, 49, 66, 82
Catalog: AP-09 — Alto Acoplamento / Sem Injeção de Dependência
Description: Todas as 15 funções de `models.py` começam com `db = get_db()`, chamando a função de módulo que também cria o schema e o seed (database.py:7-86). Os controllers importam o banco diretamente (`from database import get_db`, controllers.py:3) e o usam em `health_check` (controllers.py:266); `app.py` faz o mesmo nos handlers administrativos e no boot (app.py:82).
Impact: Não existe ponto de substituição: nenhum teste pode injetar uma conexão em memória ou um fake sem monkey-patch do módulo `database`, e importar `models` já tem efeito colateral de criar `loja.db`. Trocar o engine de banco exige editar todos os arquivos.
Recommendation: Receber a conexão por parâmetro ou construtor (repositórios), montando as dependências em um composition root no app factory (Playbook P-03 + P-06).

### F10 [HIGH] Conexão global mutável compartilhada entre threads
File: database.py:4-11, 54, 84
Catalog: AP-10 — Estado Global Mutável
Description: `db_connection = None` e `db_path = "loja.db"` são variáveis mutáveis de módulo (database.py:4-5), reatribuídas em runtime via `global db_connection` (database.py:8). A conexão única é aberta com `check_same_thread=False` (database.py:10) e reutilizada por todas as requisições.
Impact: Com o servidor multi-thread do Flask, requisições concorrentes compartilham a mesma conexão e a mesma transação implícita: um `commit()` de uma requisição persiste as escritas pendentes de outra, e um erro em uma requisição deixa a transação aberta para as demais (ver F11). O `check_same_thread=False` apenas silencia a proteção do sqlite3 contra exatamente esse uso.
Recommendation: Conexão por requisição no contexto da aplicação (`flask.g` + `teardown_appcontext`), com `db_path` vindo de configuração imutável (Playbook P-06).

### F11 [HIGH] Criação de pedido não atômica e sem rollback
File: models.py:133-169
File: app.py:49-55
Catalog: AP-11 — Escritas Multi-etapa Não Atômicas / Callback Hell
Description: `criar_pedido` insere o pedido (models.py:148-151), depois, dentro de um loop, insere cada item (models.py:157-161) e dá baixa no estoque (models.py:163-166), com um único `db.commit()` só no fim (models.py:168). Não há `rollback()` em nenhum ponto do projeto — os `except Exception` dos controllers (ex.: controllers.py:218-220) devolvem 500 sem desfazer nada. `reset_database` executa quatro `DELETE` na mesma situação (app.py:51-54).
Impact: Se o segundo item falhar (produto apagado entre a validação e a escrita, ou erro de SQL vindo do F02), o pedido e o primeiro item ficam pendentes na transação aberta da conexão global; a próxima requisição que chamar `commit()` grava esse estado parcial — pedido com itens faltando e estoque baixado a mais. A validação de estoque do primeiro loop também não protege contra duas requisições simultâneas vendendo o mesmo item.
Recommendation: Envolver a operação em transação explícita com `rollback()` no erro (`with conn:` do sqlite3, ou `BEGIN IMMEDIATE`), e fazer a baixa de estoque condicional (`UPDATE ... WHERE estoque >= ?`) para evitar estoque negativo em concorrência (Playbook P-09).

### F12 [MEDIUM] Queries N+1 na listagem de pedidos e no relatório
File: models.py:171-201, 203-233
File: models.py:154-161, 239-254
File: controllers.py:268-274
Catalog: AP-12 — Queries N+1
Description: `get_pedidos_usuario` e `get_todos_pedidos` executam, para cada pedido, uma query de itens (`"SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"])`, models.py:188 e 220) e, para cada item, uma query do nome do produto (models.py:192 e 224) — ou seja 1 + N + N·M queries. `criar_pedido` também relê o preço do produto item por item no segundo loop (models.py:155), repetindo o SELECT já feito no primeiro (models.py:140). `relatorio_vendas` faz cinco round-trips (um `COUNT`, um `SUM` e três `COUNT` por status, models.py:239-254) onde um `GROUP BY` resolveria, e `health_check` faz quatro (controllers.py:268-274).
Impact: `GET /pedidos` com 100 pedidos de 5 itens dispara mais de 600 queries; o tempo de resposta cresce linearmente com o volume e, por compartilhar a conexão global (F10), serializa as demais requisições.
Recommendation: Buscar itens e nomes de produto em uma única query com `JOIN` (ou um `IN (...)` por lote) e consolidar o relatório em uma query agregada com `GROUP BY status` (Playbook P-05).

### F13 [MEDIUM] Mapeamento linha→dict e validações duplicados
File: models.py:12-21, 31-40, 304-313
File: models.py:79-86, 95-102
File: models.py:171-201, 203-233
File: controllers.py:28-54, 72-90
Catalog: AP-13 — Código / Lógica Duplicada
Description: O dict de produto com os mesmos 8 campos é montado três vezes (models.py:12-21, 31-40, 304-313) e o de usuário duas (models.py:79-86, 95-102). `get_pedidos_usuario` e `get_todos_pedidos` são idênticas exceto pelo `WHERE` (models.py:171-201 vs 203-233), incluindo o bloco N+1 copiado. O bloco de validação de produto aparece em `criar_produto` e `atualizar_produto` (controllers.py:28-54 vs 72-90), já divergindo (ver F08).
Impact: Acrescentar um campo a `produtos` exige editar três lugares; corrigir uma regra de validação exige lembrar das duas cópias — e o projeto já tem a prova de que isso falha (o PUT perdeu as regras de nome e categoria).
Recommendation: Um serializador por entidade como fonte única de verdade, um validador de payload de produto reutilizado por criação e atualização, e uma função de listagem de pedidos parametrizada pelo filtro (Playbook P-12).

### F14 [MEDIUM] Validação de entrada ausente ou fraca
File: controllers.py:39-46, 83-90
File: controllers.py:169-171, 239-240
File: controllers.py:195-203
File: controllers.py:153-160
Catalog: AP-14 — Validação de Entrada Ausente ou Fraca
Description: `preco` e `estoque` vêm de `request.get_json()` e vão direto para comparações numéricas (`if preco < 0`, controllers.py:43) sem checagem de tipo — um `"preco": "abc"` levanta `TypeError` e devolve 500 em vez de 400. `login` e `atualizar_status_pedido` chamam `dados.get(...)` sem verificar se o corpo é `None` (controllers.py:169-171, 239-240): requisição sem JSON resulta em erro 500. Em `criar_pedido`, `itens` é passado adiante sem validar a forma de cada item (controllers.py:196-203), e `models.criar_pedido` então acessa `item["produto_id"]` e `item["quantidade"]` (models.py:140, 144) → `KeyError`/500; `quantidade` negativa é aceita e *aumenta* o estoque (models.py:163-166). `usuario_id` não é verificado contra a tabela `usuarios` (models.py:148-151 insere pedido para usuário inexistente), e `criar_usuario` não valida formato nem unicidade de email (controllers.py:153-160), permitindo cadastros duplicados.
Impact: Entradas malformadas viram 500 com detalhe interno (F04) em vez de 400 descritivo; pedidos com `quantidade` negativa corrompem o estoque e o faturamento do relatório; emails duplicados tornam o login ambíguo.
Recommendation: Validar tipo, faixa e obrigatoriedade na borda do controller com um validador reutilizável que produz 400 com mensagem, incluindo checagem de existência de `usuario_id`/`produto_id` e unicidade de email (índice `UNIQUE` no schema) (Playbook P-12).

### F15 [MEDIUM] Tratamento de erros repetido, sem handler central
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 261-262, 291-292
File: app.py:77-78
File: app.py:47-57
Catalog: AP-15 — Tratamento de Erros Engolido / Inconsistente
Description: Os handlers repetem o mesmo `try: ... except Exception as e: return jsonify({"erro": str(e)}), 500`, sem distinguir erro do cliente de erro do servidor e sem registrar o traceback. Não existe `@app.errorhandler` nem handler de 404/405, então rota inexistente devolve HTML do Flask em uma API JSON. O formato das respostas de erro também varia: às vezes só `{"erro": ...}` (controllers.py:29), às vezes com `"sucesso": False` (controllers.py:20, 183, 206). `reset_database` (app.py:47-57) não tem nenhum tratamento.
Impact: Toda falha de programação é mascarada como 500 genérico e nada é logado para diagnóstico, enquanto o detalhe interno vai para o cliente (F04). Clientes da API não conseguem tratar erros de forma uniforme porque o envelope muda por endpoint.
Recommendation: Definir exceções de domínio (`ValidationError`, `NotFoundError`, `BusinessRuleError`) e registrar `@app.errorhandler` central que as mapeia para status code e um envelope único, logando o traceback no servidor; incluir handlers de 404/405 para manter respostas JSON (Playbook P-10).

### F16 [MEDIUM] Sem integridade referencial: dados órfãos ao apagar
File: database.py:37-53
File: models.py:65-70
File: app.py:51-54
Catalog: AP-16 — Dados Órfãos / Integridade Referencial Ausente
Description: As tabelas `pedidos` e `itens_pedido` declaram `usuario_id`, `pedido_id` e `produto_id` como `INTEGER` simples, sem `FOREIGN KEY` nem `ON DELETE` (database.py:37-53) — e o SQLite não aplicaria FKs sem `PRAGMA foreign_keys = ON`, que não é executado em nenhum ponto. `deletar_produto` executa apenas `"DELETE FROM produtos WHERE id = " + str(id)` (models.py:68), sem tratar os `itens_pedido` que referenciam o produto.
Impact: Após `DELETE /produtos/5`, os pedidos existentes passam a listar `"produto_nome": "Desconhecido"` (models.py:196, 228) e o histórico fica inconsistente. `POST /pedidos` aceita `usuario_id` inexistente (F14), criando pedidos sem dono, que aparecem em `GET /pedidos` e no faturamento do relatório.
Recommendation: Declarar as FKs com `ON DELETE RESTRICT`/`CASCADE` conforme a regra, ativar `PRAGMA foreign_keys = ON` na abertura da conexão e fazer a exclusão de produto dentro de transação — bloqueando a exclusão quando houver pedidos, ou usando desativação lógica via coluna `ativo`, já existente no schema (Playbook P-09).

### F17 [LOW] `print` usado como log de aplicação
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
File: app.py:56, 83-86
Catalog: AP-17 — `print` / `console.log` como Log
Description: Eventos e erros são escritos com `print`: `print("ERRO: " + str(e))` (controllers.py:11), `print("Login bem-sucedido: " + email)` (controllers.py:179), `print("!!! BANCO DE DADOS RESETADO !!!")` (app.py:56) e o banner de startup (app.py:83-86). Vários deles ainda registram dados identificáveis (email do usuário em controllers.py:161, 179, 182).
Impact: Sem nível, timestamp ou destino configurável, não há como filtrar, silenciar em produção ou enviar para um agregador; o email em log de login é dado pessoal gravado em texto no stdout.
Recommendation: Usar o módulo `logging` da biblioteca padrão com nível por ambiente, substituindo os `print` por chamadas de logger e removendo identificadores pessoais das mensagens (Playbook P-14).

### F18 [LOW] Magic numbers e listas de domínio inline
File: models.py:256-262
File: controllers.py:47-50, 52, 242
File: app.py:36, 88
File: controllers.py:285
Catalog: AP-18 — Magic Numbers / Strings
Description: A política de desconto usa faixas e percentuais sem nome: `if faturamento > 10000: desconto = faturamento * 0.1` / `elif faturamento > 5000: ... * 0.05` / `elif faturamento > 1000: ... * 0.02` (models.py:256-262). Os limites de nome (`< 2`, `> 200`, controllers.py:47-50), a lista de categorias válidas (controllers.py:52) e a de status de pedido (controllers.py:242) são literais inline. A versão `"1.0.0"` está duplicada em app.py:36 e controllers.py:285, e a porta `5000` está fixa em app.py:88.
Impact: Alterar uma faixa de desconto ou adicionar um status exige caçar literais espalhados, sem garantia de ter achado todas as ocorrências; qualquer nova validação duplicaria as listas inline.
Recommendation: Nomear como constantes/enums no módulo de domínio (`FAIXAS_DESCONTO`, `CATEGORIAS_VALIDAS`, `STATUS_PEDIDO`, `NOME_MIN`/`NOME_MAX`) e mover versão e porta para a configuração (Playbook P-12).

### F19 [LOW] Nomenclatura ruim (`id` sombreando built-in, `cursor2`/`cursor3`)
File: models.py:24, 43, 54, 65, 89
File: controllers.py:14, 56, 64, 98, 160
File: models.py:187-193, 219-225
Catalog: AP-19 — Nomenclatura Ruim
Description: O parâmetro/variável `id` sombreia o built-in do Python em dez pontos (ex.: `def get_produto_por_id(id)`, models.py:24; `id = models.criar_produto(...)`, controllers.py:56). Nas listagens de pedidos os cursores são numerados por ordem de criação — `cursor2`, `cursor3` (models.py:187, 191, 219, 223) — sem indicar o que consultam.
Impact: Nomes sem significado dificultam a leitura exatamente nas funções mais complexas, e o sombreamento de `id` impede usar o built-in no mesmo escopo, um erro sutil de manutenção.
Recommendation: Renomear para `produto_id`/`usuario_id`/`novo_id` e `cursor_itens`/`cursor_produto` ao mover o código para as novas camadas (Playbook P-03/P-04).

### F20 [LOW] Imports não utilizados
File: database.py:2
File: models.py:2
Catalog: AP-20 — Código Morto / Imports Não Usados
Description: `import os` em database.py:2 e `import sqlite3` em models.py:2 nunca são referenciados nos respectivos arquivos (o acesso a dados em `models.py` se dá apenas via `get_db()`).
Impact: Sugere dependências que não existem — por exemplo, que `models.py` conheça o driver — e esconde o fato de que `database.py` não lê nada do ambiente.
Recommendation: Remover os imports ao reorganizar os módulos; em `database.py`, `os` passará a ser realmente necessário para ler a configuração (F01).

### F21 [LOW] Condicionais verbosas e redundantes
File: controllers.py:200
File: controllers.py:19-20, 141-142, 181-183
File: models.py:294-297
Catalog: AP-21 — Condicionais Verbosas / Redundantes
Description: `if not itens or len(itens) == 0` (controllers.py:200) testa duas vezes a mesma coisa — `not itens` já cobre a lista vazia. Vários handlers usam `else` depois de um `return` (controllers.py:19-20, 141-142, 181-183), aumentando o aninhamento sem necessidade. Em `buscar_produtos`, os filtros usam checagem de verdade sobre números (`if preco_min:`, models.py:294-297), de modo que `preco_min=0` é silenciosamente ignorado.
Impact: Leitura mais pesada e, no caso de `preco_min=0`/`preco_max=0`, um filtro que o cliente envia e a API descarta sem aviso.
Recommendation: Simplificar para `if not itens:`, usar early return sem `else` e comparar explicitamente com `None` nos filtros numéricos.

## Deprecated APIs
None detected for Python 3.12.10 + Flask 3.1.1 + flask-cors 5.0.1 — nenhuma ocorrência de `datetime.utcnow()`, `@app.before_first_request`, `app.json_encoder`/`flask.json.JSONEncoder`, `flask.escape`/`flask.Markup`, `imp`/`distutils`, nem de API legada de ORM. O projeto usa `sqlite3` da biblioteca padrão e `app.add_url_rule`, ambos suportados nas versões detectadas.

## Architecture Notes
- Current: Monolítica / sem camadas — existem arquivos chamados `models.py` e `controllers.py`, mas a separação é só no nome: `models.py` concentra SQL, regra de negócio (estoque, totais, faixas de desconto) e serialização JSON dos três domínios, e `app.py` acessa o banco diretamente nos handlers `/admin/*`.
- Missing layers: config (valores fixos em app.py:7-8, 88), models (repositórios por agregado com SQL parametrizado), services (regra de negócio hoje dividida entre models.py e controllers.py), views/routes (19 rotas registradas manualmente em app.py, sem blueprints), error handling (nenhum `@app.errorhandler`; `try/except` copiado em 16 handlers), composition root (nenhum app factory; `get_db()` global cria conexão, schema e seed).
- Proposed target: MVC em camadas com app factory — `config/` (ambiente + `.env.example`), `models/` (conexão por requisição + repositórios de `produto`, `usuario` e `pedido` com queries parametrizadas), `services/` (regras de produto, autenticação com hash, pedido transacional, relatório, notificações), `controllers/` (tradução HTTP), `routes/` (blueprints por domínio preservando os paths atuais), `errors/` (exceções de domínio + handler central) e `app.py` como composition root.

================================
Total: 21 findings
================================
