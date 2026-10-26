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
| 2 | CRITICAL | **Endpoint de execução de SQL arbitrário e reset de banco sem autenticação** | `app.py:47-78` | `POST /admin/query` executa qualquer SQL enviado no body (inclusive `DROP`); `POST /admin/reset-db` apaga todos os dados — ambos públicos. |
| 3 | CRITICAL | **Credenciais hardcoded e vazamento de segredo** — `SECRET_KEY` fixa no código e devolvida pelo `/health`; `debug=True` em produção | `app.py:7-8, 88`; `controllers.py:287-289` | Qualquer cliente lê a chave de assinatura de sessão; modo debug do Werkzeug expõe console interativo (RCE). |
| 4 | CRITICAL | **Senhas em texto puro e expostas na API** — armazenadas sem hash e devolvidas em `GET /usuarios` | `database.py:31, 75-79`; `models.py:83, 99, 110` | Vazamento direto de credenciais de todos os usuários. |
| 5 | HIGH | **God Module / ausência de camadas** — `models.py` concentra acesso a dados, regras (estoque, total, descontos) e formatação de 4 domínios; controllers chamam SQL direto (`health_check`) | `models.py:1-314`; `controllers.py:264-292`; `app.py:47-78` | Impossível testar regra de negócio sem banco; qualquer mudança afeta tudo. |
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

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                              # orquestrador: as 3 fases, regras globais e formatos de saída
└── references/
    ├── project-analysis.md               # Fase 1 — heurísticas de detecção e mapeamento
    ├── anti-patterns-catalog.md          # Fase 2 — 21 anti-patterns + APIs deprecated
    ├── report-template.md                # Fase 2 — formato do relatório
    ├── mvc-guidelines.md                 # Fase 3 — arquitetura alvo e regras de contrato
    └── refactoring-playbook.md           # Fase 3 — 14 transformações antes/depois
```

| Área de conhecimento exigida | Arquivo | Conteúdo principal |
|---|---|---|
| Análise de projeto | [project-analysis.md](code-smells-project/.claude/skills/refactor-arch/references/project-analysis.md) | Tabelas manifesto → linguagem/versão, dependência + sinal no código → framework, sinais de banco/ORM, padrões de rota por framework, inferência de domínio, 4 rótulos de arquitetura, regras de estado de runtime (venv, banco descartável, reloader) |
| Catálogo de anti-patterns | [anti-patterns-catalog.md](code-smells-project/.claude/skills/refactor-arch/references/anti-patterns-catalog.md) | 21 entradas (6 CRITICAL, 5 HIGH, 5 MEDIUM, 5 LOW) + AP-DEP com 13 linhas de APIs deprecated; cada entrada com sinais (regex), falsos positivos e padrão do playbook |
| Template de relatório | [report-template.md](code-smells-project/.claude/skills/refactor-arch/references/report-template.md) | Estrutura fixa, 7 regras (ordenação, `arquivo:linha`, contagens, seção deprecated obrigatória) e um finding de calibração |
| Guidelines de arquitetura | [mvc-guidelines.md](code-smells-project/.claude/skills/refactor-arch/references/mvc-guidelines.md) | Responsabilidades DEVE / NÃO DEVE por camada, 7 regras, layouts Flask e Express, tabela de estratégia, lista fechada de mudanças de contrato permitidas |
| Playbook de refatoração | [refactoring-playbook.md](code-smells-project/.claude/skills/refactor-arch/references/refactoring-playbook.md) | 14 padrões (P-01 a P-14) com código antes/depois em Python e JavaScript + ordem de execução |

### Decisões de design

1. **O SKILL.md é o roteiro, as referências são o conhecimento.** O SKILL.md diz *o que* fazer em cada fase e *qual* arquivo ler; os detalhes ficam nas referências, carregadas só na fase em que são necessárias. Isso mantém o prompt principal curto e evita que a Fase 1 seja influenciada pelo catálogo.
2. **Formatos de saída fixos.** Os blocos `PHASE 1`, `ARCHITECTURE AUDIT REPORT` e `PHASE 3` têm rótulos literais (em inglês, iguais aos do enunciado); o conteúdo sai em português. Resultado: os 3 relatórios têm exatamente a mesma estrutura.
3. **Evidência obrigatória.** Regra global: todo finding precisa de `arquivo:linha` que o agente leu, e as linhas devem ser reconferidas antes de escritas.
4. **Pausa explícita.** A Fase 2 termina com uma linha exata de confirmação e instrui o agente a encerrar o turno; silêncio ou pergunta não contam como "sim". O único arquivo escrito antes disso é o relatório, cujo caminho é passado como argumento (`/refactor-arch ../reports/audit-project-N.md`).
5. **Validação comparativa, não só "subiu".** A Fase 3 começa registrando um *baseline* da aplicação original (status + chaves de resposta de cada endpoint) e termina repetindo as mesmas chamadas no código novo.
6. **Contrato da API preservado, com exceções declaradas.** As guidelines listam as únicas mudanças permitidas (remover campos sensíveis, proteger endpoints perigosos, trocar 500 por 400/404, corrigir integridade). Toda mudança tem que aparecer na seção *Intentional Contract Changes* — nada some em silêncio.
7. **`disable-model-invocation: true`.** A skill altera muitos arquivos, então só roda quando chamada explicitamente.
8. **O relatório é a especificação da Fase 3.** Cada *Recommendation* é uma ação concreta que o playbook sabe executar (ex.: "remover `POST /admin/query` (P-13a); proteger `POST /admin/reset-db` (P-13b)"), e a Fase 3 a aplica por inteiro. Se não puder, o finding sai como `◐ PARCIAL` ou `✗ NÃO RESOLVIDO` no resumo — nunca trocado por outra solução. O resumo da Fase 3 mostra, por finding, *recomendação → o que foi feito*, e termina com `Every finding matches its Phase 2 recommendation`.
9. **Aderência comprovada por chamada, não por leitura.** Toda recomendação com efeito observável precisa de uma requisição HTTP que a comprove: rota removida → `404` no formato de erro da API; handler central → rota inexistente e método não permitido também em JSON; campo removido → ausente; credencial → `401/403` sem ela.

### Anti-patterns do catálogo e por quê

O catálogo nasceu da tabela "Padrões recorrentes" da análise manual: cada padrão encontrado em pelo menos um projeto virou uma entrada, generalizada para outras stacks.

| Severidade | Anti-patterns | Motivação |
|---|---|---|
| CRITICAL | AP-01 Segredos hardcoded · AP-02 SQL Injection · AP-03 Senha insegura · AP-04 Exposição de dados sensíveis · AP-05 Endpoints perigosos / auth quebrada · AP-06 God Class | Presentes nos 3 projetos (segredos, senhas) ou com impacto direto de segurança/arquitetura |
| HIGH | AP-07 Debug/config insegura · AP-08 Regra de negócio nas rotas · AP-09 Sem DI · AP-10 Estado global · AP-11 Escrita não atômica / callback hell | Violações de MVC/SOLID que impedem testar e evoluir |
| MEDIUM | AP-12 N+1 · AP-13 Duplicação · AP-14 Validação fraca · AP-15 Erros engolidos · AP-16 Dados órfãos · **AP-DEP APIs deprecated** | Performance e consistência; AP-DEP cobre Python, SQLAlchemy, Flask, Node, Express e pacotes npm |
| LOW | AP-17 `print` como log · AP-18 Magic numbers · AP-19 Nomes ruins · AP-20 Código morto · AP-21 Condicionais verbosas | Legibilidade |

As regras de severidade do catálogo exigem classificar pelo **impacto no código analisado** (ex.: no projeto 1 a skill manteve `debug=True` como HIGH e justificou no próprio finding: os handlers capturam as exceções e o console do Werkzeug exige PIN, embora o risco suba combinado com a secret key exposta).

### Como a skill ficou agnóstica de tecnologia

- **Detecção por evidência, não por suposição:** tabelas de manifestos (`requirements.txt`, `package.json`, `pom.xml`, `go.mod`…) e de sinais de código por framework (Flask, FastAPI, Django, Express, NestJS, Spring, Gin…).
- **Sinais de detecção em várias linguagens:** cada anti-pattern traz exemplos/regex para Python e JavaScript (`execute("..." + x)` e `` db.run(`...${x}`) ``, `hashlib.md5` e `createHash('md5')`).
- **Arquitetura alvo descrita por responsabilidade**, com layouts concretos para Flask e Express e um mapeamento para outras stacks.
- **Estratégia adaptativa:** a Fase 1 classifica a arquitetura atual e a Fase 3 escolhe entre *extração completa* (monolito / God Class) e *reorganização no lugar* (parcialmente em camadas). Os projetos 1 e 2 receberam extração; o projeto 3, reorganização.
- **Prova:** a mesma pasta, copiada sem nenhuma alteração (`diff -r` idêntico), rodou nos 3 projetos.

### Desafios encontrados e como foram resolvidos

| Desafio | Solução |
|---|---|
| Garantir que a Fase 3 faça exatamente o que a auditoria recomendou (ex.: *remover* um console de SQL em vez de apenas protegê-lo) | O catálogo distingue execução arbitrária (→ remover, P-13a) de operação administrativa legítima (→ proteger, P-13b); as guidelines tratam o relatório como especificação; o SKILL.md exige checagem de aderência finding a finding, comprovada por chamadas HTTP. |
| Como provar que "os endpoints continuam respondendo" sem testes automatizados nos projetos | Baseline obrigatório antes da refatoração (Fase 3.1) e comparação das mesmas chamadas depois. Fora da skill, criei [scripts/smoke_test.py](scripts/smoke_test.py) e [scripts/compare_results.py](scripts/compare_results.py) para validar de forma independente. |
| Corrigir segurança sem "quebrar" a API | Lista fechada de mudanças intencionais nas guidelines: operações administrativas legítimas (`/admin/reset-db`) continuam existindo, protegidas por `X-Admin-Token`; endpoints de execução arbitrária (`/admin/query`) são removidos — não existe versão segura de um console de SQL exposto por HTTP. |
| Dados diferentes entre baseline e pós-refatoração | Regras de *runtime state* na análise: banco ignorado pelo git e recriado por seed pode ser apagado entre execuções; banco versionado é copiado e restaurado. |
| Flask com `debug=True` cria um processo filho e a porta 5000 continuava ocupada | Instrução explícita para encerrar a árvore de processos e confirmar que a porta foi liberada. |
| O Python global da máquina não tinha Flask instalado | Iteração na heurística de runtime: usar o virtualenv local (`venv/`) quando existir (commit `4c8baf5`). |
| npm 11 bloqueia o script de instalação do `sqlite3` (sem binário nativo) | `allowScripts` no `package.json` do projeto 2. |
| Idioma | Primeira versão em inglês; traduzida para português mantendo os rótulos dos blocos de saída em inglês (commit `1d79889`). |
| Saída longa no terminal (cópia truncada) | Relatório gravado em arquivo pela própria skill; sessões completas salvas com `/export` em `reports/logs/project-N/session.txt`. |

**Iterações:** como o enunciado prevê, a skill foi ajustada ao longo das execuções (virtualenv, idioma, aderência da Fase 3 ao relatório, erros 404/405 do framework no formato da API). O projeto 1 foi executado de novo do zero com a versão final da skill e atingiu todos os critérios em uma única passada. Os projetos 2 e 3 foram executados com a versão anterior; os ajustes finais não mudam o resultado deles, porque não têm endpoint de execução arbitrária e seus endpoints administrativos já ficaram protegidos por token.

---

## C) Resultados

### Resumo das auditorias

| Projeto | Stack detectada | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| 1 — code-smells-project | Python 3.12 + Flask 3.1.1 (sqlite3, SQL puro) | 6 | 5 | 5 | 5 | **21** | [audit-project-1.md](reports/audit-project-1.md) |
| 2 — ecommerce-api-legacy | Node.js 24 + Express 4.22.1 (sqlite3 em memória) | 5 | 4 | 5 | 4 | **18** | [audit-project-2.md](reports/audit-project-2.md) |
| 3 — task-manager-api | Python 3.12 + Flask 3.0.0 + SQLAlchemy 2.1 | 4 | 3 | 6 | 5 | **18** | [audit-project-3.md](reports/audit-project-3.md) |

Todos os problemas da Análise Manual (seção A) foram encontrados pela skill nos 3 projetos. Ela ainda apontou problemas que a análise manual não pegou — por exemplo, no projeto 2, que um `"card": 4111` (número em vez de string) derruba o processo Node inteiro, e no projeto 3, que `POST /users` aceita `role: "admin"` vindo do cliente.

### Antes e depois

<table>
<tr><th>Projeto</th><th>Antes</th><th>Depois</th></tr>
<tr><td><b>1</b><br>Monolítico<br>4 arquivos<br>~780 linhas<br><br>→ extração completa<br>37 arquivos<br>~1.030 linhas</td>
<td>

```
app.py          rotas + config + admin SQL
controllers.py  validação + prints
models.py       SQL + regras + JSON (3 domínios)
database.py     conexão global + schema + seed
```
</td>
<td>

```
app.py                      entry point
src/app.py                  create_app (composition root)
src/config/settings.py
src/database.py             conexão por request (flask.g)
src/models/        produto, usuario, pedido
src/services/      pedido, relatorio, notification, admin
src/validators/    produto, usuario, pedido
src/controllers/   6 controllers
src/views/         6 blueprints
src/middlewares/   error_handler, auth
src/logger.py
```
</td></tr>
<tr><td><b>2</b><br>God Class<br>3 arquivos<br>~180 linhas<br><br>→ extração completa<br>25 arquivos<br>~510 linhas</td>
<td>

```
src/app.js
src/AppManager.js  banco + seed + rotas + regras
src/utils.js       config com segredos + cache global
```
</td>
<td>

```
src/app.js               entry point
src/createApp.js         composition root
src/config/index.js
src/database/            connection (promises + transaction), schema
src/models/              user, course, enrollment, payment, auditLog
src/services/            checkout, report, paymentGateway
src/controllers/         checkout, report, user
src/routes/              checkout, admin, user
src/middlewares/         asyncHandler, requireAdmin, errorHandler
src/utils/               logger, passwordHasher
```
</td></tr>
<tr><td><b>3</b><br>Parcialmente em camadas<br>15 arquivos<br>~1.160 linhas<br><br>→ reorganização no lugar<br>27 arquivos<br>~1.150 linhas</td>
<td>

```
app.py        config inline + rotas soltas
database.py
models/       task, user (MD5), category
routes/       task, user, report (+ CRUD categorias)
services/     notification_service (sem uso)
utils/        helpers (código morto)
seed.py
```
</td>
<td>

```
app.py             entry point
app_factory.py     create_app (composition root)
config.py          settings via env/.env
database.py        init_db
models/            task, user, category, common (regras + constantes)
controllers/       task, user, report, category, validators
routes/            task, user, report, category, system (finas)
middlewares/       errors, auth
services/          auth_service (token assinado)
seed.py            atualizado
```
</td></tr>
</table>

### Validação após a refatoração

Validação independente da skill, feita com [scripts/smoke_test.py](scripts/smoke_test.py) a partir de um banco limpo e comparada ao baseline com [scripts/compare_results.py](scripts/compare_results.py) (status HTTP + chaves das respostas):

| Projeto | Requisições | Respostas 5xx | Idênticas ao baseline (com `X-Admin-Token`) | Diferenças restantes (todas intencionais) |
|---|:-:|:-:|:-:|---|
| 1 | 26 | 0 | 24/26 | `GET /health` não devolve mais `secret_key`, `db_path`, `debug`; `POST /admin/query` **removido** (404 em JSON) |
| 2 | 7 | 0 | **7/7** (relatório financeiro com conteúdo idêntico) | — |
| 3 | 29 | 0 | 26/29 | campo `password` removido de `GET /users/1`, `POST /users`, `PUT /users/2` |

Sem o token, os endpoints administrativos/destrutivos respondem 403 (P1: `/admin/reset-db`; P2: `financial-report` e `DELETE /api/users`; P3: os 3 `DELETE`). Verificações extras:

- **P1:** `POST /login` com `' OR 1=1 --` → 401 (antes autenticava); `POST /admin/query` → 404 `{"erro": ...}` (rota removida); rota inexistente → 404 e método não permitido → 405, ambos em JSON; `GET /usuarios` sem o campo `senha`.
- **P2:** checkout com `"card": 4111` → 400 e o servidor continua de pé (antes o processo caía); log mostra `**** 4444` em vez do cartão.
- **P3:** seed e servidor executados com `-W error::DeprecationWarning` sem nenhuma falha (nenhuma API deprecated no caminho executado).

### Checklists de validação

| Item | P1 | P2 | P3 |
|---|:-:|:-:|:-:|
| **Fase 1 — Análise** | | | |
| Linguagem detectada corretamente | ✅ Python 3.12.10 | ✅ JavaScript / Node 24 | ✅ Python 3.12.10 |
| Framework detectado corretamente | ✅ Flask 3.1.1 | ✅ Express 4.22.1 | ✅ Flask 3.0.0 + SQLAlchemy |
| Domínio da aplicação descrito corretamente | ✅ E-commerce | ✅ LMS com checkout | ✅ Task manager |
| Número de arquivos analisados condiz com a realidade | ✅ 4 / ~780 | ✅ 3 / ~180 | ✅ 15 / ~1.158 |
| **Fase 2 — Auditoria** | | | |
| Relatório segue o template definido | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ ¹ | ✅ |
| Findings ordenados por severidade (CRITICAL → LOW) | ✅ | ✅ | ✅ |
| Mínimo de 5 findings identificados | ✅ 21 | ✅ 18 | ✅ 18 |
| Detecção de APIs deprecated incluída (se aplicável) | ✅ seção presente: "None detected" (correto) | ✅ dependências do `sqlite3` | ✅ `utcnow()`, `query.get()` |
| Skill pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3 — Refatoração** | | | |
| Estrutura de diretórios segue padrão MVC | ✅ | ✅ | ✅ |
| Configuração extraída para módulo de config (sem hardcoded) | ✅ `src/config/settings.py` | ✅ `src/config/index.js` | ✅ `config.py` |
| Models criados para abstrair dados | ✅ | ✅ | ✅ |
| Views/Routes separadas para visualização ou roteamento | ✅ `src/views/` | ✅ `src/routes/` | ✅ `routes/` |
| Controllers concentram o fluxo da aplicação | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ `error_handler.py` | ✅ `errorHandler.js` | ✅ `middlewares/errors.py` |
| Entry point claro | ✅ `app.py` | ✅ `src/app.js` | ✅ `app.py` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem corretamente | ✅ 18/18 rotas mantidas (`/admin/query` removido por recomendação → 404) | ✅ 7/7 | ✅ 29/29 |

¹ O finding F14 (dependências transitivas deprecated) aponta `package-lock.json` sem linha, porque o problema está nos pacotes instalados.

### Evidências

| Projeto | Sessão completa da skill (Fases 1→3) | Boot após a refatoração | Baseline / validação |
|---|---|---|---|
| 1 | [session.txt](reports/logs/project-1/session.txt) | [boot.log](reports/logs/project-1/boot.log) | [baseline](reports/logs/project-1/baseline.txt) · [após, sem token](reports/logs/project-1/after-sem-token.json) · [após, com token](reports/logs/project-1/after-com-token.json) |
| 2 | [session.txt](reports/logs/project-2/session.txt) | [boot.log](reports/logs/project-2/boot.log) | [baseline](reports/logs/project-2/baseline.txt) · [após, sem token](reports/logs/project-2/after-sem-token.json) · [após, com token](reports/logs/project-2/after-com-token.json) |
| 3 | [session.txt](reports/logs/project-3/session.txt) | [boot.log](reports/logs/project-3/boot.log) | [baseline](reports/logs/project-3/baseline.txt) · [após, sem token](reports/logs/project-3/after-sem-token.json) · [após, com token](reports/logs/project-3/after-com-token.json) |

Trecho do boot do projeto 1 refatorado ([boot.log](reports/logs/project-1/boot.log)):

```
WARNING [src.app] SECRET_KEY não definida; usando chave efêmera gerada no startup
INFO [src.database] Banco populado com dados de exemplo
INFO [__main__] Servidor iniciado em http://127.0.0.1:5000
 * Serving Flask app 'src.app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

Comparação do projeto 2 com token (`compare_results.py`):

```
= POST   /api/checkout                 200 -> 200
= POST   /api/checkout                 400 -> 400
= POST   /api/checkout                 200 -> 200
= POST   /api/checkout                 404 -> 404
= POST   /api/checkout                 400 -> 400
= GET    /api/admin/financial-report   200 -> 200
= DELETE /api/users/1                  200 -> 200

7 requisições comparadas | 7 iguais | 0 diferentes
```

### Observações sobre o comportamento em stacks diferentes

- **Mesma skill, estratégias diferentes.** Nos projetos 1 e 2 (monolito e God Class) a skill fez extração completa e apagou os arquivos antigos; no projeto 3 manteve `models/` e `routes/`, adicionou as camadas que faltavam e só moveu o CRUD de categorias para um arquivo próprio.
- **Idioma de cada stack respeitado.** Em Python: app factory, Blueprints, `flask.g`, `werkzeug.security`. Em Node: factories com injeção de dependência, wrapper de `sqlite3` com Promises, `async/await`, transação enfileirada, `crypto.scrypt`, middleware de erro com 4 parâmetros.
- **Contrato preservado com o formato de cada projeto.** Chave de erro `erro` (P1) vs `error` (P3); respostas em texto puro no P2 foram mantidas em texto.
- **Mesma regra de segurança nos 3:** operações administrativas legítimas protegidas por `X-Admin-Token` vindo da config (403 quando o token não está configurado); o único endpoint de execução arbitrária (`POST /admin/query`, P1) foi removido.
- **Limitação conhecida:** no P2, o F14 (dependências deprecated trazidas pelo driver `sqlite3`) ficou sem correção — a própria skill o marcou como "NÃO RESOLVIDO", porque exigiria trocar o driver (ex.: `node:sqlite`).
- **Imprecisão corrigida pela própria skill:** no P3, durante a Fase 3, ela verificou que o F12 (tasks órfãs ao apagar categoria) era parcialmente impreciso — o ORM já zerava `category_id` — e registrou isso, mantendo a desassociação explícita.

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado
- Python 3.12+ (projetos 1 e 3)
- Node.js 20+ e npm (projeto 2; testado com Node 24.20 / npm 11)

### Preparar os projetos

```bash
# Projeto 1
cd code-smells-project
python -m venv venv && venv/Scripts/pip install -r requirements.txt   # Linux/macOS: venv/bin/pip

# Projeto 2
cd ../ecommerce-api-legacy
npm install

# Projeto 3
cd ../task-manager-api
python -m venv venv && venv/Scripts/pip install -r requirements.txt
venv/Scripts/python seed.py
```

### Executar a skill

A skill fica em `.claude/skills/refactor-arch/` dentro de cada projeto. Abra o Claude Code **na pasta do projeto** e passe o caminho do relatório como argumento:

```bash
cd code-smells-project
claude "/refactor-arch ../reports/audit-project-1.md"

cd ../ecommerce-api-legacy
claude "/refactor-arch ../reports/audit-project-2.md"

cd ../task-manager-api
claude "/refactor-arch ../reports/audit-project-3.md"
```

Fluxo: a skill imprime a Fase 1, a auditoria (Fase 2), salva o relatório e **pausa** com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`. Responda `y` para refatorar; ela faz o baseline, refatora, valida e imprime o resumo da Fase 3. A skill nunca faz commit.

> Os projetos neste repositório já estão refatorados. Para rodar a skill sobre o código original, use um worktree no commit em que a skill foi copiada e os projetos 2 e 3 ainda estavam originais: `git worktree add ../original 7a6b358` (para o projeto 1 original, use o commit `1d79889`).

### Rodar as aplicações refatoradas

Nenhuma variável é obrigatória — todas têm default seguro (veja o `.env.example` de cada projeto). Para habilitar os endpoints administrativos, defina `ADMIN_TOKEN`:

```bash
# PowerShell
$env:ADMIN_TOKEN = "um-token-qualquer"
# bash
export ADMIN_TOKEN=um-token-qualquer

cd code-smells-project && venv/Scripts/python app.py      # http://127.0.0.1:5000
cd ecommerce-api-legacy && npm start                      # http://127.0.0.1:3000
cd task-manager-api && venv/Scripts/python app.py         # http://127.0.0.1:5000
```

### Validar que a refatoração funcionou

Com a aplicação rodando (banco recém-criado/seed recém-executado), na raiz do repositório:

```bash
# chama todos os endpoints do projeto e grava as respostas
python scripts/smoke_test.py code-smells-project --header "X-Admin-Token: um-token-qualquer" --out after.json

# compara status e formato das respostas com o comportamento original
python scripts/compare_results.py reports/logs/project-1/baseline.json after.json
```

Projetos: `code-smells-project`, `ecommerce-api-legacy`, `task-manager-api`. O `smoke_test.py` retorna código 1 se algum endpoint não responder ou devolver 5xx; o `compare_results.py` lista com `≠` cada requisição cujo status ou formato mudou — as diferenças esperadas são apenas as mudanças intencionais descritas na seção C.
