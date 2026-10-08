# Refactoring Playbook (Phase 3)

Concrete transformations, one per anti-pattern family. Each has **before/after** code. Examples
are in Python/Flask and Node/Express; translate them to the detected stack. Apply them in the
order of the *Execution order* section at the end.

| Pattern | Fixes |
|---|---|
| P-01 Externalize configuration | AP-01, AP-07 |
| P-02 Parameterized queries | AP-02 |
| P-03 Split God Class into MVC layers | AP-06, AP-09, AP-19 |
| P-04 Extract controller (thin routes) | AP-08 |
| P-05 Remove N+1 queries | AP-12 |
| P-06 Replace global state with injected dependencies | AP-09, AP-10 |
| P-07 Strong password hashing | AP-03 |
| P-08 Safe serialization & log redaction | AP-04 |
| P-09 Async/await + transactions | AP-11, AP-16 |
| P-10 Centralized error handling | AP-15, AP-04 |
| P-11 Replace deprecated APIs | AP-DEP |
| P-12 Single source of truth (validators, constants, model rules) | AP-13, AP-14, AP-18, AP-21 |
| P-13 Guard dangerous endpoints | AP-05 |
| P-14 Logger instead of print | AP-17 |

---

## P-01 — Externalize configuration

**Before (Python)**
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
...
app.run(host="0.0.0.0", port=5000, debug=True)
```
**After**
```python
# src/config/settings.py
import os, secrets, logging

def _bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)   # never a literal
    DEBUG = _bool("FLASK_DEBUG", False)
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")                          # None → admin disabled

    def __init__(self):
        if not os.environ.get("SECRET_KEY"):
            logging.getLogger(__name__).warning("SECRET_KEY not set; using an ephemeral key")

# app.py (entry point)
settings = Settings()
app = create_app(settings)
app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
```
**Before (Node)**
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_123", port: 3000 };
```
**After**
```js
// src/config/index.js
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  db: { user: process.env.DB_USER || '', password: process.env.DB_PASSWORD || '' },
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',   // empty → gateway in sandbox/disabled mode
});
```
Plus `.env.example` listing every variable with placeholder values (no real secrets).

---

## P-02 — Parameterized queries

**Before**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%')"
```
**After**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))

clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    clauses.append("categoria = ?")
    params.append(categoria)
cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)  # only fixed SQL fragments are joined
```
**Node**
```js
// before: db.get(`SELECT * FROM users WHERE id = ${req.params.id}`)
await db.get('SELECT * FROM users WHERE id = ?', [id]);
```

---

## P-03 — Split a God Class / God Module into MVC layers

**Before (Node)** — one class does everything
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE ... INSERT seed ... */ }
  setupRoutes(app) {
    app.post('/api/checkout', (req, res) => { /* validation + SQL + payment + audit */ });
    app.get('/api/admin/financial-report', (req, res) => { /* nested queries */ });
  }
}
```
**After**
```js
// src/database/connection.js   → open DB, promisified run/get/all, schema + seed
// src/models/courseModel.js
module.exports = (db) => ({
  findActiveById: (id) => db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]),
});
// src/controllers/checkoutController.js
module.exports = ({ courseModel, userModel, checkoutService }) => ({
  async checkout(input) { /* validate → orchestrate → return { msg, enrollment_id } */ },
});
// src/routes/checkoutRoutes.js
router.post('/api/checkout', asyncHandler(async (req, res) => {
  res.status(200).json(await checkoutController.checkout(req.body));
}));
// src/app.js (composition root)
const db = await openDatabase(config);
const models = createModels(db);
app.use(createCheckoutRoutes(createCheckoutController({ ...models, checkoutService })));
app.use(errorHandler);
```
**Python** — `models.py` with every domain → `models/product_model.py`, `models/user_model.py`,
`models/order_model.py`; business rules (stock check, totals, discount tiers) move to the
entity model or an `order_service.py`; HTTP stays in `views/*_routes.py`.

---

## P-04 — Extract controller (thin routes)

**Before**
```python
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data: return jsonify({'error': 'Dados inválidos'}), 400
    title = data.get('title')
    if not title: return jsonify({'error': 'Título é obrigatório'}), 400
    ... 60 lines: validation, lookups, model building, commit, try/except ...
    return jsonify(task.to_dict()), 201
```
**After**
```python
# views/task_routes.py
@task_bp.post('/tasks')
def create_task():
    task = task_controller.create_task(request.get_json(silent=True))
    return jsonify(task), 201

# controllers/task_controller.py
def create_task(data):
    payload = validate_task_payload(data, required=("title",))   # raises ValidationError(400, msg)
    ensure_exists(User, payload.get("user_id"), "Usuário não encontrado")   # raises NotFoundError
    task = Task(**payload)
    db.session.add(task); db.session.commit()
    return task.to_dict()
```

---

## P-05 — Remove N+1 queries

**Before**
```python
for row in cursor.execute("SELECT * FROM pedidos").fetchall():
    itens = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"])).fetchall()
    for item in itens:
        prod = db.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"])).fetchone()
```
**After (single JOIN, grouped in memory)**
```python
rows = db.execute("""
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr   ON pr.id = i.produto_id
    ORDER BY p.id
""").fetchall()
orders = {}
for r in rows:
    order = orders.setdefault(r["id"], {**order_fields(r), "itens": []})
    if r["produto_id"] is not None:
        order["itens"].append(item_fields(r))
return list(orders.values())
```
**ORM (SQLAlchemy)** — `Task.query.all()` + `User.query.get(t.user_id)` per task →
`db.session.execute(db.select(Task).options(joinedload(Task.user), joinedload(Task.category))).scalars()`;
per-row counts → one `GROUP BY`:
```python
counts = dict(db.session.execute(db.select(Task.status, func.count()).group_by(Task.status)).all())
```
**Node** — nested `forEach` + `db.get` → one `JOIN` query, then group rows by course.

---

## P-06 — Replace global mutable state with injected dependencies

**Before**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("loja.db", check_same_thread=False)
```
```js
let globalCache = {}; let totalRevenue = 0;
```
**After**
```python
# src/database.py — connection per request, stored in flask.g
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_schema(get_db())
```
```js
// cache becomes an object owned by the composition root and injected where needed
function createCache() { const store = new Map(); return { set: (k, v) => store.set(k, v), get: (k) => store.get(k) }; }
const cache = createCache();
const checkoutService = createCheckoutService({ db, cache, config });
```

---

## P-07 — Strong password hashing

**Before**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()           # or plaintext: VALUES ('" + senha + "')
```
```js
function badCrypto(pwd) { /* base64 loop */ }
```
**After (Python — werkzeug ships with Flask, no new dependency)**
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, raw): self.password = generate_password_hash(raw)
def check_password(self, raw): return check_password_hash(self.password, raw)
# raw SQL: store generate_password_hash(senha); login = fetch by email, then check_password_hash
```
**After (Node — built-in crypto)**
```js
const crypto = require('crypto');
function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}
function verifyPassword(password, stored) {
  const [salt, hash] = stored.split(':');
  return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), crypto.scryptSync(password, salt, 64));
}
```
Seed data must be hashed the same way so existing logins keep working.

---

## P-08 — Safe serialization & log redaction

**Before**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}
```
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**After**
```python
PUBLIC_FIELDS = ("id", "nome", "email", "tipo", "criado_em")
def to_public_dict(row): return {k: row[k] for k in PUBLIC_FIELDS}
```
```js
const maskCard = (n) => `**** **** **** ${String(n).slice(-4)}`;
logger.info(`Processing payment for card ${maskCard(cardNumber)}`);   // never log keys
```
Health/info endpoints: return status and counts only — never config values.

---

## P-09 — Async/await + transactions (and referential integrity)

**Before (callback pyramid, no transaction)**
```js
db.run("INSERT INTO enrollments ...", [u, c], function (err) {
  db.run("INSERT INTO payments ...", [this.lastID, price], function (err) {
    db.run("INSERT INTO audit_logs ...", [...], () => res.json({ ok: true }));
  });
});
```
**After**
```js
// database/connection.js
const run = (sql, p = []) => new Promise((ok, ko) => db.run(sql, p, function (e) { e ? ko(e) : ok(this); }));
async function transaction(work) {
  await run('BEGIN');
  try { const r = await work(); await run('COMMIT'); return r; }
  catch (e) { await run('ROLLBACK'); throw e; }
}
// services/checkoutService.js
return transaction(async () => {
  const { lastID: enrollmentId } = await enrollmentModel.create(userId, courseId);
  await paymentModel.create(enrollmentId, course.price, status);
  await auditModel.log(`Checkout curso ${courseId} por ${userId}`);
  return enrollmentId;
});
```
**Python (sqlite3)** — validate everything first, then write inside `with conn:` (commits or
rolls back atomically):
```python
with db:   # transaction
    cur = db.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)", (uid, total))
    db.executemany("INSERT INTO itens_pedido (...) VALUES (?, ?, ?, ?)", rows)
    db.executemany("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", stock_updates)
```
**Delete with dependents** — inside one transaction delete/handle children first
(payments → enrollments → user) or enable FK `ON DELETE CASCADE`.

---

## P-10 — Centralized error handling

**Before**
```python
def buscar_produto(id):
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500        # repeated in every handler, leaks internals
```
**After (Flask)**
```python
# middlewares/error_handler.py
class AppError(Exception):
    def __init__(self, message, status=400, payload=None):
        super().__init__(message); self.message, self.status, self.payload = message, status, payload or {}

class NotFoundError(AppError):
    def __init__(self, message): super().__init__(message, 404)

def register_error_handlers(app, error_key="erro"):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({error_key: err.message, **err.payload}), err.status

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        if isinstance(err, HTTPException):          # keep Flask's 404/405
            return err
        app.logger.exception("Unhandled error")
        return jsonify({error_key: "Erro interno do servidor"}), 500
```
**After (Express)**
```js
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
class AppError extends Error { constructor(message, status = 400) { super(message); this.status = status; } }
function errorHandler(err, req, res, next) {        // registered last
  if (err instanceof AppError) return res.status(err.status).send(err.message);   // keep original format
  logger.error(err); res.status(500).send('Erro interno');
}
```
Keep the project's original error key (`erro`/`error`) and body format (JSON vs text).

---

## P-11 — Replace deprecated APIs

```python
# before                                   # after
datetime.utcnow()                          datetime.now(timezone.utc)
Task.query.get(task_id)                    db.session.get(Task, task_id)
db.Column(db.DateTime, default=datetime.utcnow)
                                           db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
```
Careful with naive vs aware datetimes: if the DB stores naive UTC values, compare with
`datetime.now(timezone.utc).replace(tzinfo=None)` (centralize it in one `utcnow()` helper) so
existing data and serialized formats (`str(dt)`) stay identical.
```js
new Buffer(str)              → Buffer.from(str)
url.parse(u)                 → new URL(u)
res.send(404)                → res.sendStatus(404)
app.use(bodyParser.json())   → app.use(express.json())
var x = 1                    → const x = 1
```

---

## P-12 — Single source of truth (validators, constants, model rules)

**Before** — rule copied in 6 handlers; magic numbers inline
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            data['overdue'] = True
...
if faturamento > 10000: desconto = faturamento * 0.1
```
**After**
```python
# models/task.py
VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")
CLOSED_STATUSES = {"done", "cancelled"}
MIN_PRIORITY, MAX_PRIORITY = 1, 5

def is_overdue(self):
    return bool(self.due_date and self.due_date < utcnow() and self.status not in CLOSED_STATUSES)

# models/order_model.py
DISCOUNT_TIERS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))   # (minimum revenue, rate)
def discount_for(revenue):
    return next((revenue * rate for minimum, rate in DISCOUNT_TIERS if revenue > minimum), 0)
```
Validators shared by create/update:
```python
def validate_product(data):
    if not data: raise ValidationError("Dados inválidos")
    for field, label in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if field not in data: raise ValidationError(f"{label} é obrigatório")
    ...
```
Also: `if x: return True else: return False` → `return x`; `type(t) == list` → `isinstance(t, list)`;
delete unused imports and dead helpers.

---

## P-13 — Guard dangerous endpoints

**Before**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json()["sql"])          # arbitrary SQL, no auth
```
**After**
```python
# middlewares/auth.py
def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = current_app.config.get("ADMIN_TOKEN")
        if not token:
            raise AppError("Endpoint administrativo desabilitado", 403)
        if not hmac.compare_digest(request.headers.get("X-Admin-Token", ""), token):
            raise AppError("Não autorizado", 401)
        return view(*args, **kwargs)
    return wrapper

# views/admin_routes.py
@admin_bp.post("/admin/query")
@require_admin
def executar_query():
    return jsonify(admin_controller.run_read_only_query(request.get_json(silent=True))), 200
# controller: only a single SELECT statement is accepted, executed on a read-only connection
```
Fake tokens (`'fake-jwt-token-' + id`) → signed token (`itsdangerous` ships with Flask; Node
`crypto.createHmac`) keeping the same response key.

---

## P-14 — Logger instead of print

```python
print("ERRO: " + str(e))                  →  logger.exception("Erro ao listar produtos")
print("Produto criado com ID: " + str(id)) →  logger.info("Produto criado id=%s", product_id)
```
```js
console.log(`[LOG] ...`)                  →  const logger = require('../utils/logger'); logger.info('...')
```
Configure the logger once in the composition root (level from config).

---

## Execution order

1. **P-01** config module + `.env.example`
2. Database/connection module (**P-06**) and models per entity (**P-03**, **P-02**, **P-05**, **P-07**, **P-08**, **P-11**, **P-12**)
3. Services for multi-entity workflows (**P-09**)
4. Controllers (**P-04**, **P-12** validators)
5. Views/routes (thin) + guards (**P-13**)
6. Error handler + logger (**P-10**, **P-14**)
7. Composition root + entry point; update seed scripts/README; delete old files
8. Validate (SKILL.md § 3.4)
