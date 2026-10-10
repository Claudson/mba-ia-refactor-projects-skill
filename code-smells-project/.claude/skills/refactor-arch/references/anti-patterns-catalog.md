# Catálogo de Anti-Patterns (Fase 2)

Cada entrada tem: **ID**, **severidade**, **o que é**, **sinais de detecção** (o que buscar
concretamente — as regex são ponto de partida, sempre confirme lendo o código), **falsos
positivos** a evitar e o **padrão do playbook** que corrige (`refactoring-playbook.md`).

## Escala de severidade (baseada em impacto MVC / SOLID)

| Nível | Significado | Exemplos típicos |
|---|---|---|
| **CRITICAL** | Falha de segurança ou ausência completa de separação de responsabilidades; expõe dados ou permite ação de atacante | Segredos hardcoded, SQL injection, senha em texto puro/hash fraco, dados sensíveis em respostas/logs, endpoints destrutivos sem autenticação, God Class |
| **HIGH** | Forte violação de MVC/SOLID que dificulta muito manutenção e testes | Regra de negócio em rotas/controllers, sem DI / alto acoplamento, estado global mutável, escritas multi-etapa não atômicas, callback hell, modo debug ligado |
| **MEDIUM** | Padronização, duplicação, performance moderada, validação ausente | Queries N+1, lógica duplicada, validação ausente, erros engolidos, APIs deprecated, dados órfãos ao apagar |
| **LOW** | Legibilidade | Magic numbers, nomes ruins, log com `print`, imports não usados, condicionais verbosas |

### Regras de severidade
- Classifique pelo **impacto real neste código**, não pelo nome do padrão. Um *default de
  desenvolvimento* hardcoded que pode ser sobrescrito por variável de ambiente é LOW; uma chave
  *de produção* hardcoded é CRITICAL.
- Um problema de segurança acessível por endpoint público nunca fica abaixo de HIGH.
- O mesmo anti-pattern em vários lugares é **um** finding com todas as localizações, na
  severidade da pior ocorrência.
- Na dúvida entre dois níveis, escolha o mais alto e justifique em *Impact*.

---

## CRITICAL

### AP-01 — Credenciais / Segredos Hardcoded
Segredos (secret keys, senhas de banco, chaves de API/pagamento, senhas SMTP, tokens) como literais no código.
- **Sinais:** `SECRET_KEY\s*=\s*['"]`, `config\[['"]SECRET_KEY['"]\]\s*=\s*['"]`,
  `(password|passwd|pwd|pass|secret|token|api[_-]?key|apikey)\w*\s*[:=]\s*['"][^'"]+['"]`,
  `pk_live_|sk_live_|AKIA[0-9A-Z]{16}`, connection strings com `user:pass@`,
  `server.login(` com argumentos literais; objetos de config (`const config = { dbPass: "..." }`).
- **Também:** segredos devolvidos por um endpoint (ex.: `/health` retornando `secret_key`).
- **Falsos positivos:** placeholders em `.env.example`, fixtures de teste, dados de seed de
  usuários de demonstração (esses são AP-03 se armazenados em texto puro).
- **Correção:** Playbook **P-01** (externalizar configuração).

### AP-02 — SQL Injection
Valores controlados pelo usuário concatenados/interpolados em SQL.
- **Sinais:** `execute\(\s*["'].*["']\s*\+`, `"... WHERE ... = '" + var`, `+ str(id)` dentro de
  SQL, f-strings / `%` / `.format(` montando SQL (`f"SELECT ... {x}"`), template literals JS em
  `db.run/get/all/query(\`...${x}...\`)`, `LIKE '%" + termo + "%'` dinâmico.
- **Falsos positivos:** placeholders (`?`, `%s`, `:nome`, `$1`) com tupla/array de parâmetros;
  query builders de ORM (`filter(Model.col == x)`, `.like(f'%{q}%')` passa parâmetro vinculado).
- **Correção:** **P-02** (queries parametrizadas).

### AP-03 — Armazenamento Inseguro de Senhas
Senhas armazenadas em texto puro ou com hash rápido/quebrado/caseiro.
- **Sinais:** colunas `senha`/`password`/`pass` gravadas direto da requisição; comparações
  `WHERE senha = ?` / `password == input`; `hashlib.md5|sha1|sha256(` em senhas;
  `crypto.createHash('md5'|'sha1')`; funções caseiras (loops de `base64`, `badCrypto`,
  codificações reversíveis); senhas padrão como `"123456"` atribuídas quando ausentes.
- **Correção:** **P-07** (hash forte: `werkzeug.security`, `bcrypt`, `argon2`, `crypto.scrypt` do Node).

### AP-04 — Exposição de Dados Sensíveis
Segredos ou dados pessoais/financeiros saindo do sistema por respostas ou logs.
- **Sinais:** serializers/`to_dict()`/`SELECT *` mapeados para JSON incluindo
  `password`/`senha`/`pass`; respostas com `secret_key`, `db_path`, `debug`; logs imprimindo
  números de cartão, senhas, tokens, chaves de gateway (`console.log(\`...${card}...\`)`);
  `str(e)` / stack traces devolvidos ao cliente em erros 500.
- **Correção:** **P-08** (serialização segura / mascaramento) + **P-10** (tratamento de erros centralizado).

### AP-05 — Endpoints Perigosos sem Proteção / Autenticação Quebrada
Endpoints que executam código/SQL arbitrário, apagam dados ou fazem ações administrativas sem
autenticação; autenticação falsa.
- **Sinais:** rotas como `/admin/*`, `/reset`, `/query`, `/exec`, `/debug` sem verificação de
  auth; `cursor.execute(request...['sql'])`; `eval(`/`exec(` sobre entrada; tokens como
  `'fake-jwt-token-' + id`; rotas `DELETE` destrutivas sem checagem de dono/perfil.
- **Correção:** **P-13** (proteger endpoints perigosos).

### AP-06 — God Class / God Module
Uma única classe ou módulo com várias responsabilidades: conexão + schema + seed + roteamento +
regras de negócio + formatação, para vários domínios.
- **Sinais:** um arquivo com mais de ~250 LOC tocando ≥ 3 domínios; uma classe com métodos como
  `initDb()` **e** `setupRoutes(app)`; um `models.py` com SQL, regras de negócio (estoque, totais,
  descontos) e formatação JSON; handlers de rota definidos dentro da classe de dados.
- **Correção:** **P-03** (separar em Model / Controller / Routes) + **P-04**.

---

## HIGH

### AP-07 — Modo Debug / Configuração de Runtime Insegura
- **Sinais:** `debug=True`, `app.config["DEBUG"] = True`, `app.run(host="0.0.0.0", debug=True)`,
  `NODE_ENV` ignorado, `CORS(app)` / `cors()` permissivo com `*` numa API com credenciais.
- **Nota de severidade:** CRITICAL se o console de debug/stack traces forem acessíveis
  publicamente *e* combinados com segredos; senão HIGH.
- **Correção:** **P-01** (config por ambiente).

### AP-08 — Regra de Negócio nas Rotas / Fat Controllers
Handlers de rota (views) contêm regras de validação, cálculos, fluxos multi-etapa, queries e
serialização em vez de delegar.
- **Sinais:** handlers com mais de ~30 linhas; `Model.query...`/`db.execute` dentro de rota;
  aritmética de preços/totais/estatísticas nos handlers; etapas de notificação/e-mail/pagamento
  dentro do handler; uma pasta `services/` que existe mas não é importada pelas rotas.
- **Correção:** **P-04** (extrair controller/service).

### AP-09 — Alto Acoplamento / Sem Injeção de Dependência
Camadas instanciam ou importam infraestrutura concreta diretamente, impedindo testes isolados.
- **Sinais:** `new sqlite3.Database(` no construtor de uma classe de domínio; toda função de
  model chamando um `get_db()` de módulo que também cria o schema; controllers importando o
  módulo de banco; services instanciando clientes SMTP no `__init__`.
- **Correção:** **P-03** / **P-06** (composition root injeta as dependências).

### AP-10 — Estado Global Mutável
- **Sinais:** variáveis mutáveis de módulo alteradas em runtime (`global x`, `let cache = {}`,
  `let total = 0`, listas acumuladas num service singleton), conexão de banco compartilhada com
  `check_same_thread=False`.
- **Falsos positivos:** constantes imutáveis (tuplas/config congelada em `UPPER_CASE`).
- **Correção:** **P-06**.

### AP-11 — Escritas Multi-etapa Não Atômicas / Callback Hell
Um fluxo grava em várias tabelas sem transação, ou aninha ≥ 3 níveis de callbacks.
- **Sinais:** `INSERT`/`UPDATE` sequenciais num loop seguidos de um único `commit()` com
  `return` antecipado no meio; pirâmides `db.run(... function(err){ db.run(... function(err){ ...`;
  contadores manuais para saber quando loops assíncronos terminaram (`pending--; if (pending === 0)`).
- **Correção:** **P-09** (async/await + transação).

---

## MEDIUM

### AP-12 — Queries N+1
- **Sinais:** uma query dentro de `for`/`forEach` sobre linhas de outra query;
  `Model.query.get(x.fk)` do ORM ou acesso a relacionamento lazy (`len(user.tasks)`) dentro de
  loop; `COUNT(*)` por linha em loop; vários `filter_by(status=...).count()` que poderiam ser um `GROUP BY`.
- **Correção:** **P-05** (JOIN / eager loading / query agregada).

### AP-13 — Código / Lógica Duplicada
- **Sinais:** mesmo mapeamento linha→dict repetido; o mesmo bloco de validação em criar e
  atualizar; a mesma regra de negócio (ex.: "está atrasada") reimplementada em vários handlers
  enquanto já existe um método no model; funções auxiliares/constantes definidas e não usadas
  enquanto a lógica está duplicada em outro lugar.
- **Correção:** **P-12** (fonte única: método de model / validador / serializer).

### AP-14 — Validação de Entrada Ausente ou Fraca
- **Sinais:** campos de `request.get_json()` / `req.body` usados sem checagem de tipo/faixa;
  body `None` não tratado antes de `data['x']`; comparações numéricas sobre entrada não validada
  (`priority < 1` com string → 500); IDs vindos do cliente usados sem checar existência.
- **Correção:** **P-12** (validadores na borda do controller).

### AP-15 — Tratamento de Erros Engolido / Inconsistente
- **Sinais:** `except:` genérico / `except Exception: pass`; `try/except` devolvendo `str(e)` em
  todo handler; callbacks Node ignorando `err`; formatos de erro misturados (texto puro vs JSON);
  sem handler central (`@app.errorhandler`, middleware de erro do Express).
- **Correção:** **P-10** (exceções customizadas + middleware de erro centralizado).

### AP-16 — Dados Órfãos / Integridade Referencial Ausente
- **Sinais:** apagar uma linha pai sem tratar as filhas (sem FK `ON DELETE`, sem cascade, sem
  checagem); respostas que admitem dados sujos; FKs declaradas sem constraints.
- **Correção:** **P-09** (transação + cascade ou bloqueio) — mantendo status/formato do endpoint.

### AP-DEP — APIs Deprecated / Obsoletas
Uso de APIs deprecated na versão **detectada** da linguagem/framework/biblioteca. Sempre
recomende o equivalente moderno. Confirme as versões da Fase 1 antes de apontar.

| Stack | Uso deprecated (sinal) | Equivalente moderno |
|---|---|---|
| Python ≥ 3.12 | `datetime.utcnow()`, `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)`, `datetime.fromtimestamp(ts, timezone.utc)` |
| SQLAlchemy ≥ 2.0 / Flask-SQLAlchemy ≥ 3.0 | `Model.query.get(id)` (API Query legada) | `db.session.get(Model, id)` / `db.get_or_404(Model, id)` |
| SQLAlchemy ≥ 2.0 | `Model.query.filter(...).all()` (legado, ainda funciona) | `db.session.execute(db.select(Model).where(...)).scalars().all()` — LOW, salvo se misturado com `.get()` |
| Flask ≥ 2.3 | `@app.before_first_request`, `flask.json.JSONEncoder`, `app.json_encoder` | app factory / `with app.app_context()`, provider `app.json` |
| Flask / Werkzeug | `from werkzeug import secure_filename` (caminhos antigos), `flask.escape`, `flask.Markup` | `werkzeug.utils.secure_filename`, `markupsafe.escape`, `markupsafe.Markup` |
| Python | módulos `imp`, `distutils`, `asyncore`, `smtpd`; `typing.List` em ≥ 3.9 (LOW) | `importlib`, `setuptools`, `asyncio`, genéricos nativos |
| Node.js | `new Buffer(x)` | `Buffer.from(x)` / `Buffer.alloc(n)` |
| Node.js | `url.parse()`, `querystring` | `new URL()`, `URLSearchParams` |
| Node.js | `crypto.createCipher()`, `fs.exists()` | `crypto.createCipheriv()`, `fs.existsSync()` / `fs.promises.access()` |
| Node.js | APIs no estilo callback onde há versão com promise (`fs.readFile` com cb, sem `util.promisify`) | `fs/promises`, `async/await` (LOW, salvo se causar callback hell → AP-11) |
| Express 4 | `req.param()`, `res.send(status)`, `res.json(status, obj)`, `app.del()`, `bodyParser()` | `req.params`/`req.query`/`req.body`, `res.sendStatus()`, `res.status(s).json(obj)`, `app.delete()`, `express.json()` |
| JS | declarações `var`, objeto `arguments` | `const`/`let`, rest params (LOW) |
| pacotes npm | pacotes marcados como deprecated pelo npm na instalação (ex.: `request`) ou módulos nativos sem manutenção | alternativa mantida |

- **Severidade:** MEDIUM quando a API emite warnings de deprecação ou será removida na próxima
  major; LOW para obsolescência apenas de estilo.
- **Correção:** **P-11**.
- Se nada se aplicar, o relatório ainda deve dizer *"None detected for <stack + versões>."*

---

## LOW

### AP-17 — `print` / `console.log` como Log
- **Sinais:** `print(` / `console.log(` em fluxos de requisição para erros/eventos; banners no startup.
- **Correção:** **P-14** (módulo de logger).

### AP-18 — Magic Numbers / Strings
- **Sinais:** limites numéricos sem explicação (`> 10000`, `* 0.1`, `len(x) < 4`, faixa 1..5),
  listas de status inline (`['pending', 'done', ...]`) repetidas, regras em string
  (`startsWith("4")`), constantes definidas num módulo mas não usadas.
- **Correção:** **P-12** (constantes nomeadas / enums no model ou config).

### AP-19 — Nomenclatura Ruim
- **Sinais:** nomes de uma letra ou crípticos (`u`, `e`, `p`, `cc`, `cid`, `d`), sombreando
  built-ins (`id`, `type`, `list`), nomes enganosos (`badCrypto`, `AppManager`, `utils` guardando config).
- **Correção:** renomear ao mover o código (P-03/P-04).

### AP-20 — Código Morto / Imports Não Usados
- **Sinais:** imports nunca referenciados (`import os, sys, json`), funções/classes nunca
  chamadas, variáveis exportadas e não usadas, código comentado.
- **Correção:** apagar.

### AP-21 — Condicionais Verbosas / Redundantes
- **Sinais:** `if cond: return True else: return False`; pirâmides de `if` aninhados que são uma
  única expressão booleana; `type(x) == list`.
- **Correção:** retornar a expressão; `isinstance`.

---

## Comandos de varredura rápida (adapte à stack)

```bash
# segredos
grep -rnEi "(secret|password|passwd|pwd|pass|token|api_?key)\w*\s*[:=]\s*['\"][^'\"]{3,}" --include=*.{py,js,ts} .
# concatenação de SQL
grep -rnE "(execute|run|get|all|query)\(\s*[\"'\`].*(SELECT|INSERT|UPDATE|DELETE).*([\"']\s*\+|\\$\{|\{)" --include=*.{py,js,ts} .
# hash fraco
grep -rnE "md5|sha1|createHash\(|base64" --include=*.{py,js,ts} .
# debug / except genérico / deprecated
grep -rnE "debug\s*=\s*True|except:\s*$|utcnow\(|\.query\.get\(|new Buffer\(" --include=*.{py,js,ts} .
```
Sempre exclua diretórios de dependências (`node_modules`, `venv`, `.venv`).
