# Anti-Patterns Catalog (Phase 2)

Each entry has: **ID**, **severity**, **what it is**, **detection signals** (concrete things to
search for — regexes are starting points, always confirm by reading the code), **false
positives** to avoid, and the **playbook pattern** that fixes it (`refactoring-playbook.md`).

## Severity scale (from MVC / SOLID impact)

| Level | Meaning | Typical examples |
|---|---|---|
| **CRITICAL** | Security hole or complete absence of separation of concerns; exposes data or lets an attacker act | Hardcoded secrets, SQL injection, plaintext/weak password hashing, sensitive data in responses/logs, unauthenticated destructive endpoints, God Class |
| **HIGH** | Strong MVC/SOLID violation that makes maintenance and testing very hard | Business logic in routes/controllers, no DI / tight coupling, global mutable state, non-atomic multi-step writes, callback hell, debug mode on |
| **MEDIUM** | Standardization, duplication, moderate performance, missing validation | N+1 queries, duplicated logic, missing validation, swallowed errors, deprecated APIs, orphaned data on delete |
| **LOW** | Readability | Magic numbers, poor names, `print` logging, unused imports, verbose conditionals |

### Severity rules
- Rate by **actual impact in this code**, not by the name of the pattern. A hardcoded *dev
  default* that is overridable by env var is LOW; a hardcoded *production* key is CRITICAL.
- A security issue reachable from a public endpoint is never below HIGH.
- The same anti-pattern in many places is **one** finding with all locations, at the severity of
  its worst occurrence.
- When unsure between two levels, pick the higher one and say why in *Impact*.

---

## CRITICAL

### AP-01 — Hardcoded Credentials / Secrets
Secrets (secret keys, DB passwords, API/payment keys, SMTP passwords, tokens) as literals in code.
- **Signals:** `SECRET_KEY\s*=\s*['"]`, `config\[['"]SECRET_KEY['"]\]\s*=\s*['"]`,
  `(password|passwd|pwd|pass|secret|token|api[_-]?key|apikey)\w*\s*[:=]\s*['"][^'"]+['"]`,
  `pk_live_|sk_live_|AKIA[0-9A-Z]{16}`, connection strings with `user:pass@`,
  `server.login(` with literal args; config objects (`const config = { dbPass: "..." }`).
- **Also:** secrets echoed back by an endpoint (e.g. `/health` returning `secret_key`).
- **False positives:** placeholders in `.env.example`, test fixtures, seed data for demo users
  (those are AP-03 if stored in plaintext).
- **Fix:** Playbook **P-01** (externalize config).

### AP-02 — SQL Injection
User-controlled values concatenated/interpolated into SQL.
- **Signals:** `execute\(\s*["'].*["']\s*\+`, `"... WHERE ... = '" + var`, `+ str(id)` inside SQL,
  f-strings / `%` / `.format(` building SQL (`f"SELECT ... {x}"`), JS template literals in
  `db.run/get/all/query(\`...${x}...\`)`, dynamic `LIKE '%" + term + "%'`.
- **False positives:** placeholders (`?`, `%s`, `:name`, `$1`) with a params tuple/array; ORM
  query builders (`filter(Model.col == x)`, `.like(f'%{q}%')` passes a bound parameter).
- **Fix:** **P-02** (parameterized queries).

### AP-03 — Insecure Password Storage
Passwords stored in plaintext or hashed with fast/broken/home-made algorithms.
- **Signals:** columns `senha`/`password`/`pass` written straight from the request; comparisons
  `WHERE senha = ?` / `password == input`; `hashlib.md5|sha1|sha256(` on passwords;
  `crypto.createHash('md5'|'sha1')`; custom functions (`base64` loops, `badCrypto`, reversible
  encodings); default passwords like `"123456"` assigned when missing.
- **Fix:** **P-07** (strong password hashing: `werkzeug.security`, `bcrypt`, `argon2`, Node
  `crypto.scrypt`).

### AP-04 — Sensitive Data Exposure
Secrets or personal/financial data leaving the system through responses or logs.
- **Signals:** serializers/`to_dict()`/`SELECT *` mapped to JSON including `password`/`senha`/
  `pass`; responses with `secret_key`, `db_path`, `debug`; logs printing card numbers, passwords,
  tokens, gateway keys (`console.log(\`...${card}...\`)`); `str(e)` / stack traces returned to
  the client on 500.
- **Fix:** **P-08** (safe serialization / redaction) + **P-10** (central error handler).

### AP-05 — Unprotected Dangerous Endpoints / Broken Authentication
Endpoints that execute arbitrary code/SQL, wipe data or perform admin actions with no auth; fake
authentication.
- **Signals:** routes like `/admin/*`, `/reset`, `/query`, `/exec`, `/debug` with no auth
  check; `cursor.execute(request...['sql'])`; `eval(`/`exec(` on input; tokens like
  `'fake-jwt-token-' + id`; destructive `DELETE` routes with no ownership/role check.
- **Fix:** **P-13** (guard dangerous endpoints).

### AP-06 — God Class / God Module
A single class or module owns several responsibilities: DB connection + schema + seed + routing +
business rules + formatting, for several domains.
- **Signals:** one file > ~250 LOC touching ≥ 3 domains; a class with methods like `initDb()`
  **and** `setupRoutes(app)`; `models.py` that contains SQL, business rules (stock, totals,
  discounts) and JSON formatting; route handlers defined inside the data class.
- **Fix:** **P-03** (split into Model / Controller / Routes) + **P-04**.

---

## HIGH

### AP-07 — Debug Mode / Insecure Runtime Config
- **Signals:** `debug=True`, `app.config["DEBUG"] = True`, `app.run(host="0.0.0.0", debug=True)`,
  `NODE_ENV` ignored, permissive `CORS(app)` / `cors()` with `*` on an API with credentials.
- **Severity note:** CRITICAL if the debug console/stack traces are reachable publicly *and*
  combined with secrets; otherwise HIGH.
- **Fix:** **P-01** (config per environment).

### AP-08 — Business Logic in Routes / Fat Controllers
Route handlers (views) contain validation rules, calculations, multi-step workflows, queries and
serialization instead of delegating.
- **Signals:** handler functions > ~30 lines; `Model.query...`/`db.execute` inside a route;
  arithmetic on prices/totals/stats inside handlers; notification/email/payment steps inside the
  handler; a `services/` folder that exists but is not imported by routes.
- **Fix:** **P-04** (extract controller/service).

### AP-09 — Tight Coupling / No Dependency Injection
Layers instantiate or import concrete infrastructure directly, so they cannot be tested in
isolation.
- **Signals:** `new sqlite3.Database(` inside a domain class constructor; every model function
  calling a module-level `get_db()` that creates the schema; controllers importing the DB module;
  services instantiating SMTP clients in `__init__`.
- **Fix:** **P-03** / **P-06** (composition root wires dependencies).

### AP-10 — Global Mutable State
- **Signals:** module-level mutable variables mutated at runtime (`global x`, `let cache = {}`,
  `let total = 0`, lists appended in a singleton service), shared DB connection with
  `check_same_thread=False`.
- **False positives:** immutable constants (`UPPER_CASE` tuples/frozen config).
- **Fix:** **P-06**.

### AP-11 — Non-atomic Multi-step Writes / Callback Hell
A workflow writes to several tables without a transaction, or nests ≥ 3 levels of callbacks.
- **Signals:** sequential `INSERT`/`UPDATE` in a loop followed by a single `commit()` with early
  `return` paths in between; `db.run(... function(err){ db.run(... function(err){ ...` pyramids;
  manual counters to know when async loops finished (`pending--; if (pending === 0)`).
- **Fix:** **P-09** (async/await + transaction).

---

## MEDIUM

### AP-12 — N+1 Queries
- **Signals:** a query inside a `for`/`forEach` over rows of another query; ORM `Model.query.get(x.fk)`
  or lazy relationship access (`len(user.tasks)`) inside a loop; `COUNT(*)` per row in a loop;
  several `filter_by(status=...).count()` that could be one `GROUP BY`.
- **Fix:** **P-05** (JOIN / eager loading / aggregate query).

### AP-13 — Duplicated Code / Logic
- **Signals:** same row→dict mapping repeated; the same validation block in create and update;
  the same business rule (e.g. "is overdue") re-implemented in several handlers while a model
  method already exists; helper functions/constants defined but not used while the logic is
  duplicated elsewhere.
- **Fix:** **P-12** (single source of truth: model method / validator / serializer).

### AP-14 — Missing or Weak Input Validation
- **Signals:** `request.get_json()` / `req.body` fields used without type/range checks; `None`
  body not handled before `data['x']`; numeric comparisons on unvalidated input (`priority < 1`
  with a string → 500); IDs from the client trusted without existence checks.
- **Fix:** **P-12** (validators at the controller boundary).

### AP-15 — Swallowed / Inconsistent Error Handling
- **Signals:** bare `except:` / `except Exception: pass`; `try/except` returning `str(e)` in every
  handler; Node callbacks ignoring `err`; mixed response formats for errors (plain text vs JSON);
  no central error handler (`@app.errorhandler`, Express error middleware).
- **Fix:** **P-10** (custom exceptions + centralized error middleware).

### AP-16 — Orphaned Data / Missing Referential Integrity
- **Signals:** deleting a parent row without handling children (no FK `ON DELETE`, no cascade,
  no check); responses that admit dirty data; FKs declared without constraints.
- **Fix:** **P-09** (transaction + cascade or guard) — keep the endpoint's status/shape.

### AP-DEP — Deprecated / Obsolete APIs
Use of APIs deprecated in the **detected** version of the language/framework/library. Always
recommend the modern equivalent. Confirm versions from Phase 1 before flagging.

| Stack | Deprecated usage (signal) | Modern equivalent |
|---|---|---|
| Python ≥ 3.12 | `datetime.utcnow()`, `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)`, `datetime.fromtimestamp(ts, timezone.utc)` |
| SQLAlchemy ≥ 2.0 / Flask-SQLAlchemy ≥ 3.0 | `Model.query.get(id)` (legacy Query API) | `db.session.get(Model, id)` / `db.get_or_404(Model, id)` |
| SQLAlchemy ≥ 2.0 | `Model.query.filter(...).all()` (legacy, still works) | `db.session.execute(db.select(Model).where(...)).scalars().all()` — flag as LOW unless mixed with `.get()` |
| Flask ≥ 2.3 | `@app.before_first_request`, `flask.json.JSONEncoder`, `app.json_encoder` | app factory / `with app.app_context()`, `app.json` provider |
| Flask / Werkzeug | `from werkzeug import secure_filename` (old paths), `flask.escape`, `flask.Markup` | `werkzeug.utils.secure_filename`, `markupsafe.escape`, `markupsafe.Markup` |
| Python | `imp`, `distutils`, `asyncore`, `smtpd` modules; `typing.List` style in ≥ 3.9 (LOW) | `importlib`, `setuptools`, `asyncio`, builtin generics |
| Node.js | `new Buffer(x)` | `Buffer.from(x)` / `Buffer.alloc(n)` |
| Node.js | `url.parse()`, `querystring` | `new URL()`, `URLSearchParams` |
| Node.js | `crypto.createCipher()`, `fs.exists()` | `crypto.createCipheriv()`, `fs.existsSync()` / `fs.promises.access()` |
| Node.js | callback-style APIs where promise versions exist (`fs.readFile` cb, `util.promisify` not used) | `fs/promises`, `async/await` (LOW unless it causes callback hell → AP-11) |
| Express 4 | `req.param()`, `res.send(status)`, `res.json(status, obj)`, `app.del()`, `bodyParser()` | `req.params`/`req.query`/`req.body`, `res.sendStatus()`, `res.status(s).json(obj)`, `app.delete()`, `express.json()` |
| JS | `var` declarations, `arguments` object | `const`/`let`, rest params (LOW) |
| npm packages | packages marked deprecated by npm at install (e.g. `request`) or unmaintained native modules | maintained alternative |

- **Severity:** MEDIUM when the API emits deprecation warnings or is removed in the next major;
  LOW for style-only obsolescence.
- **Fix:** **P-11**.
- If none apply, the report must still say *"Deprecated APIs: none detected for <stack+versions>"*.

---

## LOW

### AP-17 — `print` / `console.log` as Logging
- **Signals:** `print(` / `console.log(` in request paths for errors/events; banners on startup.
- **Fix:** **P-14** (logger module).

### AP-18 — Magic Numbers / Strings
- **Signals:** unexplained numeric thresholds (`> 10000`, `* 0.1`, `len(x) < 4`, `range 1..5`),
  status lists inline (`['pending', 'done', ...]`) repeated, string rules (`startsWith("4")`),
  constants defined in a module but not used.
- **Fix:** **P-12** (named constants / enums in the model or config).

### AP-19 — Poor Naming
- **Signals:** one-letter or cryptic names (`u`, `e`, `p`, `cc`, `cid`, `d`), shadowing built-ins
  (`id`, `type`, `list`), misleading names (`badCrypto`, `AppManager`, `utils` holding config).
- **Fix:** rename while moving code (P-03/P-04).

### AP-20 — Dead Code / Unused Imports
- **Signals:** imports never referenced (`import os, sys, json`), functions/classes never called,
  exported-but-unused variables, commented-out code.
- **Fix:** delete.

### AP-21 — Verbose / Redundant Conditionals
- **Signals:** `if cond: return True else: return False`; nested `if` pyramids that are a single
  boolean expression; `type(x) == list`.
- **Fix:** return the expression; `isinstance`.

---

## Quick scan commands (adapt to the stack)

```bash
# secrets
grep -rnEi "(secret|password|passwd|pwd|pass|token|api_?key)\w*\s*[:=]\s*['\"][^'\"]{3,}" --include=*.{py,js,ts} .
# SQL concatenation
grep -rnE "(execute|run|get|all|query)\(\s*[\"'\`].*(SELECT|INSERT|UPDATE|DELETE).*([\"']\s*\+|\\$\{|\{)" --include=*.{py,js,ts} .
# weak hashing
grep -rnE "md5|sha1|createHash\(|base64" --include=*.{py,js,ts} .
# debug / bare except / deprecated
grep -rnE "debug\s*=\s*True|except:\s*$|utcnow\(|\.query\.get\(|new Buffer\(" --include=*.{py,js,ts} .
```
Always exclude dependency dirs (`node_modules`, `venv`, `.venv`).
