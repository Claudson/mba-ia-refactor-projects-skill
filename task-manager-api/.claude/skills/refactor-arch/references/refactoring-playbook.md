# Playbook de Refatoração (Fase 3)

Transformações concretas, uma por família de anti-pattern. Cada uma tem código **antes/depois**.
Os exemplos estão em Python/Flask e Node/Express; traduza-os para a stack detectada. Aplique-os
na ordem da seção *Ordem de execução* no final.

| Padrão | Corrige |
|---|---|
| P-01 Externalizar configuração | AP-01, AP-07 |
| P-02 Queries parametrizadas | AP-02 |
| P-03 Separar God Class em camadas MVC | AP-06, AP-09, AP-19 |
| P-04 Extrair controller (rotas finas) | AP-08 |
| P-05 Eliminar queries N+1 | AP-12 |
| P-06 Trocar estado global por dependências injetadas | AP-09, AP-10 |
| P-07 Hash forte de senhas | AP-03 |
| P-08 Serialização segura e mascaramento em logs | AP-04 |
| P-09 Async/await + transações | AP-11, AP-16 |
| P-10 Tratamento de erros centralizado | AP-15, AP-04 |
| P-11 Substituir APIs deprecated | AP-DEP |
| P-12 Fonte única (validadores, constantes, regras no model) | AP-13, AP-14, AP-18, AP-21 |
| P-13 Proteger endpoints perigosos | AP-05 |
| P-14 Logger em vez de print | AP-17 |

---

## P-01 — Externalizar configuração

**Antes (Python)**
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
...
app.run(host="0.0.0.0", port=5000, debug=True)
```
**Depois**
```python
# src/config/settings.py
import os, secrets, logging

def _bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)   # nunca um literal
    DEBUG = _bool("FLASK_DEBUG", False)
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")                          # None → admin desabilitado

    def __init__(self):
        if not os.environ.get("SECRET_KEY"):
            logging.getLogger(__name__).warning("SECRET_KEY não definida; usando chave efêmera")

# app.py (entry point)
settings = Settings()
app = create_app(settings)
app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
```
**Antes (Node)**
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_123", port: 3000 };
```
**Depois**
```js
// src/config/index.js
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  db: { user: process.env.DB_USER || '', password: process.env.DB_PASSWORD || '' },
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',   // vazio → gateway em modo sandbox/desabilitado
});
```
Mais um `.env.example` listando todas as variáveis com valores de exemplo (sem segredos reais).

---

## P-02 — Queries parametrizadas

**Antes**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%')"
```
**Depois**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))

clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    clauses.append("categoria = ?")
    params.append(categoria)
cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)  # só fragmentos fixos de SQL são concatenados
```
**Node**
```js
// antes: db.get(`SELECT * FROM users WHERE id = ${req.params.id}`)
await db.get('SELECT * FROM users WHERE id = ?', [id]);
```

---

## P-03 — Separar God Class / God Module em camadas MVC

**Antes (Node)** — uma classe faz tudo
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE ... INSERT seed ... */ }
  setupRoutes(app) {
    app.post('/api/checkout', (req, res) => { /* validação + SQL + pagamento + auditoria */ });
    app.get('/api/admin/financial-report', (req, res) => { /* queries aninhadas */ });
  }
}
```
**Depois**
```js
// src/database/connection.js   → abre o banco, run/get/all com promise, schema + seed
// src/models/courseModel.js
module.exports = (db) => ({
  findActiveById: (id) => db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]),
});
// src/controllers/checkoutController.js
module.exports = ({ courseModel, userModel, checkoutService }) => ({
  async checkout(input) { /* valida → orquestra → retorna { msg, enrollment_id } */ },
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
**Python** — `models.py` com todos os domínios → `models/product_model.py`,
`models/user_model.py`, `models/order_model.py`; regras de negócio (checagem de estoque, totais,
faixas de desconto) vão para o model da entidade ou para um `order_service.py`; o HTTP fica em `views/*_routes.py`.

---

## P-04 — Extrair controller (rotas finas)

**Antes**
```python
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data: return jsonify({'error': 'Dados inválidos'}), 400
    title = data.get('title')
    if not title: return jsonify({'error': 'Título é obrigatório'}), 400
    ... 60 linhas: validação, buscas, montagem do model, commit, try/except ...
    return jsonify(task.to_dict()), 201
```
**Depois**
```python
# views/task_routes.py
@task_bp.post('/tasks')
def create_task():
    task = task_controller.create_task(request.get_json(silent=True))
    return jsonify(task), 201

# controllers/task_controller.py
def create_task(data):
    payload = validate_task_payload(data, required=("title",))   # lança ValidationError(400, msg)
    ensure_exists(User, payload.get("user_id"), "Usuário não encontrado")   # lança NotFoundError
    task = Task(**payload)
    db.session.add(task); db.session.commit()
    return task.to_dict()
```

---

## P-05 — Eliminar queries N+1

**Antes**
```python
for row in cursor.execute("SELECT * FROM pedidos").fetchall():
    itens = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"])).fetchall()
    for item in itens:
        prod = db.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"])).fetchone()
```
**Depois (um único JOIN, agrupado em memória)**
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
**ORM (SQLAlchemy)** — `Task.query.all()` + `User.query.get(t.user_id)` por task →
`db.session.execute(db.select(Task).options(joinedload(Task.user), joinedload(Task.category))).scalars()`;
contagens por linha → um único `GROUP BY`:
```python
counts = dict(db.session.execute(db.select(Task.status, func.count()).group_by(Task.status)).all())
```
**Node** — `forEach` aninhado + `db.get` → uma query com `JOIN`, depois agrupar as linhas por curso.

---

## P-06 — Trocar estado global mutável por dependências injetadas

**Antes**
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
**Depois**
```python
# src/database.py — conexão por requisição, guardada em flask.g
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
// o cache vira um objeto criado pelo composition root e injetado onde for necessário
function createCache() { const store = new Map(); return { set: (k, v) => store.set(k, v), get: (k) => store.get(k) }; }
const cache = createCache();
const checkoutService = createCheckoutService({ db, cache, config });
```

---

## P-07 — Hash forte de senhas

**Antes**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()           # ou texto puro: VALUES ('" + senha + "')
```
```js
function badCrypto(pwd) { /* loop de base64 */ }
```
**Depois (Python — o werkzeug já vem com o Flask, sem nova dependência)**
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, raw): self.password = generate_password_hash(raw)
def check_password(self, raw): return check_password_hash(self.password, raw)
# SQL puro: gravar generate_password_hash(senha); login = buscar por email e depois check_password_hash
```
**Depois (Node — crypto nativo)**
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
Os dados de seed devem receber o mesmo hash para que os logins existentes continuem funcionando.

---

## P-08 — Serialização segura e mascaramento em logs

**Antes**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}
```
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**Depois**
```python
PUBLIC_FIELDS = ("id", "nome", "email", "tipo", "criado_em")
def to_public_dict(row): return {k: row[k] for k in PUBLIC_FIELDS}
```
```js
const maskCard = (n) => `**** **** **** ${String(n).slice(-4)}`;
logger.info(`Processando pagamento do cartão ${maskCard(cardNumber)}`);   // nunca logar chaves
```
Endpoints de health/info: devolver apenas status e contagens — nunca valores de configuração.

---

## P-09 — Async/await + transações (e integridade referencial)

**Antes (pirâmide de callbacks, sem transação)**
```js
db.run("INSERT INTO enrollments ...", [u, c], function (err) {
  db.run("INSERT INTO payments ...", [this.lastID, price], function (err) {
    db.run("INSERT INTO audit_logs ...", [...], () => res.json({ ok: true }));
  });
});
```
**Depois**
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
**Python (sqlite3)** — valide tudo primeiro e depois grave dentro de `with conn:` (faz commit ou
rollback de forma atômica):
```python
with db:   # transação
    cur = db.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)", (uid, total))
    db.executemany("INSERT INTO itens_pedido (...) VALUES (?, ?, ?, ?)", rows)
    db.executemany("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", stock_updates)
```
**Exclusão com dependentes** — numa única transação, apague/trate os filhos primeiro
(payments → enrollments → user) ou habilite FK `ON DELETE CASCADE`.

---

## P-10 — Tratamento de erros centralizado

**Antes**
```python
def buscar_produto(id):
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500        # repetido em todo handler, vaza detalhes internos
```
**Depois (Flask)**
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
        if isinstance(err, HTTPException):          # mantém os 404/405 do Flask
            return err
        app.logger.exception("Erro não tratado")
        return jsonify({error_key: "Erro interno do servidor"}), 500
```
**Depois (Express)**
```js
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
class AppError extends Error { constructor(message, status = 400) { super(message); this.status = status; } }
function errorHandler(err, req, res, next) {        // registrado por último
  if (err instanceof AppError) return res.status(err.status).send(err.message);   // mantém o formato original
  logger.error(err); res.status(500).send('Erro interno');
}
```
Mantenha a chave de erro original do projeto (`erro`/`error`) e o formato do corpo (JSON vs texto).

---

## P-11 — Substituir APIs deprecated

```python
# antes                                    # depois
datetime.utcnow()                          datetime.now(timezone.utc)
Task.query.get(task_id)                    db.session.get(Task, task_id)
db.Column(db.DateTime, default=datetime.utcnow)
                                           db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
```
Cuidado com datetimes naive vs aware: se o banco guarda valores UTC naive, compare com
`datetime.now(timezone.utc).replace(tzinfo=None)` (centralize num helper `utcnow()`) para que os
dados existentes e os formatos serializados (`str(dt)`) continuem idênticos.
```js
new Buffer(str)              → Buffer.from(str)
url.parse(u)                 → new URL(u)
res.send(404)                → res.sendStatus(404)
app.use(bodyParser.json())   → app.use(express.json())
var x = 1                    → const x = 1
```

---

## P-12 — Fonte única (validadores, constantes, regras no model)

**Antes** — regra copiada em 6 handlers; magic numbers inline
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            data['overdue'] = True
...
if faturamento > 10000: desconto = faturamento * 0.1
```
**Depois**
```python
# models/task.py
VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")
CLOSED_STATUSES = {"done", "cancelled"}
MIN_PRIORITY, MAX_PRIORITY = 1, 5

def is_overdue(self):
    return bool(self.due_date and self.due_date < utcnow() and self.status not in CLOSED_STATUSES)

# models/order_model.py
DISCOUNT_TIERS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))   # (faturamento mínimo, taxa)
def discount_for(revenue):
    return next((revenue * rate for minimum, rate in DISCOUNT_TIERS if revenue > minimum), 0)
```
Validadores compartilhados entre criar/atualizar:
```python
def validate_product(data):
    if not data: raise ValidationError("Dados inválidos")
    for field, label in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if field not in data: raise ValidationError(f"{label} é obrigatório")
    ...
```
Também: `if x: return True else: return False` → `return x`; `type(t) == list` → `isinstance(t, list)`;
apague imports não usados e helpers mortos.

---

## P-13 — Proteger endpoints perigosos

**Antes**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json()["sql"])          # SQL arbitrário, sem autenticação
```
**Depois**
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
# controller: aceita apenas um único SELECT, executado numa conexão somente leitura
```
Tokens falsos (`'fake-jwt-token-' + id`) → token assinado (`itsdangerous` já vem com o Flask;
`crypto.createHmac` no Node), mantendo a mesma chave na resposta.

---

## P-14 — Logger em vez de print

```python
print("ERRO: " + str(e))                  →  logger.exception("Erro ao listar produtos")
print("Produto criado com ID: " + str(id)) →  logger.info("Produto criado id=%s", product_id)
```
```js
console.log(`[LOG] ...`)                  →  const logger = require('../utils/logger'); logger.info('...')
```
Configure o logger uma única vez no composition root (nível vindo da config).

---

## Ordem de execução

1. **P-01** módulo de config + `.env.example`
2. Módulo de banco/conexão (**P-06**) e models por entidade (**P-03**, **P-02**, **P-05**, **P-07**, **P-08**, **P-11**, **P-12**)
3. Services para fluxos com várias entidades (**P-09**)
4. Controllers (**P-04**, validadores **P-12**)
5. Views/routes (finas) + guards (**P-13**)
6. Handler de erros + logger (**P-10**, **P-14**)
7. Composition root + entry point; atualizar scripts de seed/README; apagar arquivos antigos
8. Validar (SKILL.md § 3.4)
