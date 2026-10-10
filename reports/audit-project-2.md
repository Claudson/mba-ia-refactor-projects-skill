================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js v24.20.0) + Express 4.22.1 (SQLite em memória via driver sqlite3 5.1.7, SQL puro)
Files:   3 analyzed | ~180 lines of code
Date:    2026-10-10

## Summary
CRITICAL: 5 | HIGH: 4 | MEDIUM: 5 | LOW: 4

| # | Severity | Finding | Catalog | Location |
|---|---|---|---|---|
| F01 | CRITICAL | Credenciais de produção e chave de gateway hardcoded | AP-01 | src/utils.js:2-5 |
| F02 | CRITICAL | Hash de senha caseiro e reversível, com senha padrão "123456" | AP-03 | src/utils.js:17-23 |
| F03 | CRITICAL | Número de cartão e chave do gateway impressos no log | AP-04 | src/AppManager.js:45 |
| F04 | CRITICAL | Relatório financeiro e exclusão de usuários sem autenticação | AP-05 | src/AppManager.js:80 |
| F05 | CRITICAL | God Class `AppManager`: conexão, schema, seed, rotas e regras | AP-06 | src/AppManager.js:4-139 |
| F06 | HIGH | Regras de negócio de checkout e relatório dentro dos handlers | AP-08 | src/AppManager.js:28-78 |
| F07 | HIGH | Banco instanciado dentro da classe, sem injeção de dependência | AP-09 | src/AppManager.js:7 |
| F08 | HIGH | Estado global mutável (`globalCache`, `totalRevenue`) | AP-10 | src/utils.js:9-15 |
| F09 | HIGH | Checkout não atômico e callback hell com contadores manuais | AP-11 | src/AppManager.js:50-63 |
| F10 | MEDIUM | Queries N+1 no relatório financeiro | AP-12 | src/AppManager.js:92 |
| F11 | MEDIUM | Validação de entrada fraca no checkout e na exclusão | AP-14 | src/AppManager.js:35 |
| F12 | MEDIUM | Erros ignorados nos callbacks e formatos de erro inconsistentes | AP-15 | src/AppManager.js:57 |
| F13 | MEDIUM | Exclusão de usuário deixa matrículas e pagamentos órfãos | AP-16 | src/AppManager.js:133-135 |
| F14 | MEDIUM | Dependências transitivas deprecated do driver sqlite3 | AP-DEP | package-lock.json |
| F15 | LOW | `console.log` como mecanismo de log | AP-17 | src/app.js:13 |
| F16 | LOW | Magic strings na regra de pagamento e nos status | AP-18 | src/AppManager.js:46 |
| F17 | LOW | Nomenclatura ruim/enganosa | AP-19 | src/AppManager.js:29-33 |
| F18 | LOW | Código morto: config e variáveis exportadas não usadas | AP-20 | src/AppManager.js:2 |

## Findings

### F01 [CRITICAL] Credenciais de produção e chave de gateway hardcoded
File: src/utils.js:2-5
Catalog: AP-01 — Credenciais / Segredos Hardcoded
Description: O objeto `config` contém literais `dbPass: "senha_super_secreta_prod_123"`, `dbUser: "admin_master"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` (prefixo de chave *live*) e `smtpUser`, além de `port: 3000` fixa.
Impact: Qualquer pessoa com acesso ao repositório obtém a chave de produção do gateway de pagamento e a senha do banco; trocar credenciais exige alterar código e novo deploy.
Recommendation: Externalizar toda configuração para variáveis de ambiente lidas em um módulo `config/`, com defaults apenas de desenvolvimento e `.env.example` sem valores reais (Playbook P-01).

### F02 [CRITICAL] Hash de senha caseiro e reversível, com senha padrão "123456"
File: src/utils.js:17-23
File: src/AppManager.js:18, 68
Catalog: AP-03 — Armazenamento Inseguro de Senhas
Description: `badCrypto(pwd)` repete os 2 primeiros caracteres do base64 da senha e trunca em 10 chars — é uma codificação reversível sem salt (senhas com o mesmo prefixo colidem). No checkout, `badCrypto(p || "123456")` atribui a senha `"123456"` quando `pwd` não é enviado; o seed grava `pass = '123'` em texto puro.
Impact: Um vazamento da tabela `users` revela trivialmente as senhas (ou prefixos delas); contas criadas sem `pwd` ficam com senha conhecida por qualquer atacante.
Recommendation: Usar hash forte com salt da biblioteca padrão (`crypto.scrypt` + `crypto.randomBytes`, comparação com `timingSafeEqual`); não inventar senha padrão — gerar um segredo aleatório quando ausente; aplicar o mesmo hash ao seed (Playbook P-07).

### F03 [CRITICAL] Número de cartão e chave do gateway impressos no log
File: src/AppManager.js:45
Catalog: AP-04 — Exposição de Dados Sensíveis
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava o PAN completo do cartão e a chave *live* do gateway em stdout a cada checkout.
Impact: Logs passam a conter dados de cartão (violação direta de PCI-DSS) e o segredo do gateway, expostos a qualquer sistema/pessoa com acesso aos logs.
Recommendation: Nunca logar cartão nem chaves; se necessário, registrar apenas os 4 últimos dígitos mascarados via logger central (Playbook P-08 + P-14).

### F04 [CRITICAL] Relatório financeiro e exclusão de usuários sem autenticação
File: src/AppManager.js:80, 131-137
Catalog: AP-05 — Endpoints Perigosos sem Proteção / Autenticação Quebrada
Description: `GET /api/admin/financial-report` expõe receita por curso e nomes de alunos, e `DELETE /api/users/:id` apaga qualquer usuário — ambos sem nenhuma verificação de identidade ou perfil.
Impact: Qualquer cliente anônimo lê dados financeiros/pessoais e apaga contas arbitrárias (ex.: `DELETE /api/users/1` remove o usuário seed).
Recommendation: Proteger as rotas administrativas/destrutivas com um middleware de autorização baseado em token configurado por variável de ambiente (`ADMIN_TOKEN`), respondendo 401 sem credencial (Playbook P-13).

### F05 [CRITICAL] God Class `AppManager`: conexão, schema, seed, rotas e regras
File: src/AppManager.js:4-139
Catalog: AP-06 — God Class / God Module
Description: A classe `AppManager` abre a conexão (`new sqlite3.Database(':memory:')`, linha 7), cria o schema e o seed (`initDb()`, linhas 10-23) e registra todas as rotas com suas regras de negócio, SQL e respostas HTTP (`setupRoutes(app)`, linhas 25-138) para os domínios de usuários, cursos, matrículas, pagamentos e auditoria.
Impact: Nenhuma parte pode ser testada ou reutilizada isoladamente; qualquer mudança em um domínio arrisca quebrar os demais; não há fronteira entre dados, regra e transporte HTTP.
Recommendation: Separar em `config/`, `database/` (conexão + schema/seed), `models/` (acesso a dados por entidade), `services/`/`controllers/` (regras) e `routes/` (mapeamento HTTP), compostos em `app.js` (Playbook P-03 + P-04).

### F06 [HIGH] Regras de negócio de checkout e relatório dentro dos handlers
File: src/AppManager.js:28-78, 80-129
Catalog: AP-08 — Regra de Negócio nas Rotas / Fat Controllers
Description: O handler de `POST /api/checkout` (51 linhas) decide aprovação de pagamento (`cc.startsWith("4")`), cria usuário, matrícula, pagamento e auditoria; o handler do relatório (50 linhas) agrega receita (`courseData.revenue += payment.amount`) e monta o JSON.
Impact: Regras de pagamento e cálculo de receita ficam acopladas ao Express e só são testáveis via HTTP; impossível reaproveitá-las em outro fluxo.
Recommendation: Extrair `CheckoutService`/`ReportService` com as regras e deixar controllers finos que só leem a requisição, chamam o service e formatam a resposta (Playbook P-04).

### F07 [HIGH] Banco instanciado dentro da classe, sem injeção de dependência
File: src/AppManager.js:7
File: src/app.js:8-10
Catalog: AP-09 — Alto Acoplamento / Sem Injeção de Dependência
Description: O construtor faz `this.db = new sqlite3.Database(':memory:')` e os handlers usam `this.db`/`self.db` diretamente; `app.js` apenas chama `new AppManager()`, `initDb()` e `setupRoutes(app)`.
Impact: Não é possível trocar o banco (ex.: arquivo, banco de teste) nem testar regras com dublês sem alterar a classe.
Recommendation: Criar a conexão em um composition root (`app.js`/`createApp`) e injetá-la nos models, que por sua vez são injetados nos services e controllers (Playbook P-03 / P-06).

### F08 [HIGH] Estado global mutável (`globalCache`, `totalRevenue`)
File: src/utils.js:9-15, 25
File: src/AppManager.js:59
Catalog: AP-10 — Estado Global Mutável
Description: `let globalCache = {}` é alterado em runtime por `logAndCache()` a cada checkout (`last_checkout_${userId}`) e exportado; `let totalRevenue = 0` é exportado como variável mutável de módulo.
Impact: Cache sem limite cresce indefinidamente (vazamento de memória por usuário), é compartilhado por todo o processo e nunca é lido — estado oculto que dificulta testes e raciocínio.
Recommendation: Remover o estado global; se um cache for necessário, encapsulá-lo em uma instância injetada pelo composition root (Playbook P-06).

### F09 [HIGH] Checkout não atômico e callback hell com contadores manuais
File: src/AppManager.js:37-77, 50-63, 69-72
File: src/AppManager.js:83-127, 86-98, 117-122
Catalog: AP-11 — Escritas Multi-etapa Não Atômicas / Callback Hell
Description: O checkout aninha 6 níveis de callbacks (`db.get` → `db.get` → `db.run` users → `db.run` enrollments → `db.run` payments → `db.run` audit_logs) sem transação; o relatório usa contadores manuais `coursesPending--` / `enrPending--` para saber quando responder.
Impact: Falha no INSERT de pagamento deixa usuário e matrícula gravados sem pagamento (matrícula gratuita); a lógica de contadores é frágil e ordena o relatório pela ordem de chegada das queries.
Recommendation: Promisificar o driver, reescrever com `async/await` e envolver as escritas do checkout em `BEGIN`/`COMMIT`/`ROLLBACK` (Playbook P-09).

### F10 [MEDIUM] Queries N+1 no relatório financeiro
File: src/AppManager.js:92, 104, 106
Catalog: AP-12 — Queries N+1
Description: Para cada curso, `SELECT * FROM enrollments WHERE course_id = ?`; para cada matrícula, `SELECT name, email FROM users WHERE id = ?` e `SELECT amount, status FROM payments WHERE enrollment_id = ?` — 1 + C + 2·M queries.
Impact: O tempo do relatório cresce linearmente com matrículas e dispara centenas de queries com poucos dados.
Recommendation: Uma única query com `LEFT JOIN` entre courses, enrollments, users e payments, agregando em memória no model/service (Playbook P-05).

### F11 [MEDIUM] Validação de entrada fraca no checkout e na exclusão
File: src/AppManager.js:35, 46
File: src/AppManager.js:132
Catalog: AP-14 — Validação de Entrada Ausente ou Fraca
Description: `if (!u || !e || !cid || !cc)` só verifica presença; `card` numérico faz `cc.startsWith` lançar `TypeError` dentro de um callback do sqlite3 (fora do ciclo do Express), derrubando o processo; e-mail não é validado; `req.params.id` é usado sem checar se é inteiro.
Impact: Um único `POST /api/checkout` com `"card": 4111` encerra a API inteira (negação de serviço trivial).
Recommendation: Validador na borda do controller verificando tipos (strings não vazias, `c_id` inteiro, `card` string de dígitos), respondendo 400 (Playbook P-12).

### F12 [MEDIUM] Erros ignorados nos callbacks e formatos de erro inconsistentes
File: src/AppManager.js:57, 92-93, 104, 106, 133-135
Catalog: AP-15 — Tratamento de Erros Engolido / Inconsistente
Description: Os callbacks de auditoria, enrollments, users, payments e DELETE recebem `err` e o ignoram (em `92-93`, um erro deixa `enrollments` `undefined` e `enrollments.length` lança); o DELETE responde sucesso mesmo com erro; não existe middleware de erro e as respostas misturam texto puro e JSON.
Impact: Falhas de banco viram crash do processo ou sucesso falso; não há um lugar único para logar/formatar erros.
Recommendation: Propagar erros via `async/await` + `next(err)` para um middleware de erro central do Express, com classes de erro de domínio que carregam status e mensagem (Playbook P-10).

### F13 [MEDIUM] Exclusão de usuário deixa matrículas e pagamentos órfãos
File: src/AppManager.js:133-135
File: src/AppManager.js:14-15
Catalog: AP-16 — Dados Órfãos / Integridade Referencial Ausente
Description: `DELETE FROM users WHERE id = ?` não trata `enrollments`/`payments`; as tabelas não declaram FKs. A própria resposta admite: "as matrículas e pagamentos ficaram sujos no banco".
Impact: O relatório passa a listar alunos "Unknown" com receita contabilizada de usuários inexistentes.
Recommendation: Declarar FKs e apagar em transação as matrículas e pagamentos do usuário antes do usuário (Playbook P-09), mantendo status e corpo da resposta.

### F14 [MEDIUM] Dependências transitivas deprecated do driver sqlite3
File: package-lock.json
Catalog: AP-DEP — APIs Deprecated / Obsoletas
Description: `sqlite3@5.1.7` traz pacotes marcados como deprecated pelo npm: `glob` e `tar` (versões antigas com vulnerabilidades conhecidas), `inflight` (vaza memória), `rimraf` < 4, `npmlog`, `gauge`, `are-we-there-yet`, `prebuild-install`, `@npmcli/move-file`.
Impact: Avisos de deprecação a cada `npm install` e superfície de vulnerabilidades na cadeia de build do módulo nativo.
Recommendation: Avaliar a migração para o módulo nativo `node:sqlite` (Node ≥ 22.5) ou atualizar o driver quando houver versão sem essas dependências (Playbook P-11). Fora do escopo da refatoração estrutural.

### F15 [LOW] `console.log` como mecanismo de log
File: src/app.js:13
File: src/utils.js:13
Catalog: AP-17 — `print` / `console.log` como Log
Description: Banner de startup e `console.log(\`[LOG] Salvando no cache: ${key}\`)` usam `console.log` direto (o log de cartão está em F03).
Impact: Sem níveis nem formato; impossível silenciar ou redirecionar logs de forma central.
Recommendation: Módulo `logger` simples com níveis, usado em todo o código (Playbook P-14).

### F16 [LOW] Magic strings na regra de pagamento e nos status
File: src/AppManager.js:46, 48, 108
Catalog: AP-18 — Magic Numbers / Strings
Description: Aprovação definida por `cc.startsWith("4")` e status `"PAID"` / `"DENIED"` repetidos como literais.
Impact: A regra de aprovação fica escondida no handler; um erro de digitação em um status quebra o cálculo de receita silenciosamente.
Recommendation: Constantes nomeadas (`PAYMENT_STATUS`, prefixo de cartão aprovado) no model de pagamento (Playbook P-12).

### F17 [LOW] Nomenclatura ruim/enganosa
File: src/AppManager.js:4, 29-33
File: src/utils.js:1, 17
Catalog: AP-19 — Nomenclatura Ruim
Description: Variáveis `u`, `e`, `p`, `cid`, `cc`; classe genérica `AppManager`; `utils.js` guardando configuração; função `badCrypto`.
Impact: Leitura e manutenção dificultadas; nomes não revelam a responsabilidade.
Recommendation: Renomear ao mover o código (`name`, `email`, `password`, `courseId`, `cardNumber`; `config/`, `passwordHasher`) mantendo os nomes dos campos do payload (contrato) (Playbook P-03/P-04).

### F18 [LOW] Código morto: config e variáveis exportadas não usadas
File: src/AppManager.js:2
File: src/utils.js:2-3, 5, 10, 25
Catalog: AP-20 — Código Morto / Imports Não Usados
Description: `totalRevenue` é importado e nunca usado; `config.dbUser`, `config.dbPass` e `config.smtpUser` não são lidos em lugar nenhum (banco é em memória, não há SMTP); `globalCache` é exportado e nunca lido.
Impact: Ruído e falsa impressão de funcionalidades (SMTP, banco autenticado) inexistentes.
Recommendation: Apagar o que não é usado.

## Deprecated APIs
| Location | Deprecated usage | Modern equivalent |
|---|---|---|
| package-lock.json (`node_modules/glob`, `tar`, `rimraf`, `inflight`) | Versões antigas deprecated pelo npm, trazidas por `sqlite3@5.1.7` | `node:sqlite` nativo ou driver atualizado |
| package-lock.json (`npmlog`, `gauge`, `are-we-there-yet`, `prebuild-install`, `@npmcli/move-file`) | Pacotes "no longer supported" | idem |
| src/AppManager.js:37-133 | API de callbacks do `sqlite3` (estilo, LOW — causa o callback hell de F09) | wrapper com Promise + `async/await` |

## Architecture Notes
- Current: God Class — `AppManager` concentra conexão, schema, seed, rotas e regras de negócio; `utils.js` mistura config, cache global e "criptografia".
- Missing layers: config | models | controllers | views/routes | error handling | composition root
- Proposed target: `src/config` + `src/database` + `src/models` + `src/services` + `src/controllers` + `src/routes` + `src/middlewares` (auth admin + erro central), compostos em `src/app.js` com `src/server.js`/entry inalterado (`npm start`).

================================
Total: 18 findings
================================
