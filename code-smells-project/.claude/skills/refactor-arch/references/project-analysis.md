# Project Analysis — Heuristics (Phase 1)

Goal: build an accurate, evidence-based picture of the project **before** judging it. Every value
printed in the Phase 1 block must come from a file you read, not from assumptions.

---

## 1. File inventory

Count and read only **source files written by the project authors**.

| Exclude always | Why |
|---|---|
| `node_modules/`, `venv/`, `.venv/`, `env/`, `vendor/`, `site-packages/` | dependencies |
| `.git/`, `.claude/`, `.idea/`, `.vscode/` | tooling |
| `__pycache__/`, `dist/`, `build/`, `target/`, `bin/`, `obj/`, `coverage/` | build artifacts |
| `*.db`, `*.sqlite*`, `*.log`, lockfiles (`package-lock.json`, `poetry.lock`, `yarn.lock`) | data / generated (read lockfiles only to get exact versions) |

Source = code files (`.py .js .ts .mjs .cjs .java .kt .go .rb .php .cs .rs`) **plus** seed /
migration scripts. Count manifests and docs separately (do not add them to "Source files").
Report `N files analyzed (~LOC lines)` — count LOC with `wc -l` (or equivalent) on the source set.

---

## 2. Language & version

| Evidence file | Language | Version source |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` | Python | `python_requires`, `.python-version`, `runtime.txt`, Dockerfile `FROM python:X` — else `python --version` |
| `package.json` | JavaScript / TypeScript (`tsconfig.json` or `.ts` files → TS) | `engines.node`, `.nvmrc` — else `node --version` |
| `pom.xml`, `build.gradle(.kts)` | Java / Kotlin | `maven.compiler.source`, `sourceCompatibility` |
| `go.mod` | Go | `go` directive |
| `Gemfile` | Ruby | `ruby` directive |
| `composer.json` | PHP | `require.php` |
| `*.csproj` | C# | `TargetFramework` |
| `Cargo.toml` | Rust | `edition` / `rust-version` |

If several manifests exist, the language of the entry point wins; mention the others.

---

## 3. Framework detection

Look in the manifest **and** confirm with an import/usage in code.

| Language | Manifest dependency | Code signal | Framework |
|---|---|---|---|
| Python | `flask` | `Flask(__name__)`, `@app.route`, `Blueprint(` | Flask |
| Python | `fastapi` | `FastAPI()`, `@app.get` / `APIRouter` | FastAPI |
| Python | `django` | `settings.py`, `urls.py`, `INSTALLED_APPS` | Django |
| JS/TS | `express` | `express()`, `app.get/post(`, `express.Router()` | Express |
| JS/TS | `fastify` / `koa` / `@nestjs/core` / `@hapi/hapi` | `fastify()`, `new Koa()`, `@Controller()` | Fastify / Koa / NestJS / Hapi |
| Java | `spring-boot-starter-web` | `@RestController` | Spring Boot |
| Go | `gin-gonic/gin`, `labstack/echo`, `go-chi/chi` | `gin.Default()`, `echo.New()` | Gin / Echo / Chi |
| Ruby | `rails`, `sinatra` | `config/routes.rb`, `get '/' do` | Rails / Sinatra |
| PHP | `laravel/framework` | `routes/web.php` | Laravel |

**Version:** exact version from the lockfile/installed package if available, else the manifest
constraint as written (e.g. `Express ^4.18.2`). Never invent a patch number.

Also list notable libraries (CORS, ORM, validation, auth, HTTP clients, mailers) under *Dependencies*.

---

## 4. Database & data access

| Signal | Engine | Access style |
|---|---|---|
| `import sqlite3`, `sqlite3.connect(`, npm `sqlite3`/`better-sqlite3`, `:memory:` | SQLite (file or in-memory) | raw SQL |
| `psycopg2`, `pg`, `postgres://` | PostgreSQL | raw SQL or ORM |
| `pymysql`, `mysql2`, `mysql://` | MySQL | raw SQL or ORM |
| `pymongo`, `mongoose`, `mongodb://` | MongoDB | driver / ODM |
| `flask_sqlalchemy`, `sqlalchemy`, `db.Model` | via SQLAlchemy URI | ORM |
| `sequelize`, `typeorm`, `prisma`, `knex` | via config | ORM / query builder |

Tables/models: collect from `CREATE TABLE` statements, `__tablename__`, `db.Model`
subclasses, ORM model definitions, or migration files. Note where the schema is created
(e.g. "created inside `get_db()` on first call", "`db.create_all()` at import time").

---

## 5. Entry point & runtime

- Entry point: `if __name__ == "__main__"` / `app.run(`, `package.json` `main`/`scripts.start`,
  `app.listen(`, `main()` in Go/Java. Record port and host.
- How to run: project README first, then manifest scripts.
- **Interpreter / dependencies:** if a local virtualenv exists (`venv/`, `.venv/`), run with its
  interpreter (`venv/Scripts/python` on Windows, `venv/bin/python` elsewhere); for Node, run
  `npm install` only if `node_modules/` is missing. If dependencies are missing, install them from
  the manifest before the baseline — never into the global interpreter without asking.
- **Runtime state** (needed for Phase 3 baseline): identify DB files and seed scripts.
  - A DB file that is **git-ignored** and **recreated automatically** (schema + seed on boot, or
    by a documented seed script) is throwaway dev state: it may be deleted before each validation
    run so baseline and post-refactor runs start from identical data.
  - Never delete a DB file that is versioned or not reproducible — copy it to the temp dir and
    restore it instead.
  - In-memory DBs reset on every boot — nothing to do.
- Note debug reloaders (Flask `debug=True`, nodemon): they spawn a child process — when stopping
  the app, kill the whole process tree / everything listening on the port.

---

## 6. Endpoint inventory

Find every route registration and record `METHOD PATH → handler file:line`:

| Stack | Patterns to search |
|---|---|
| Flask | `@app.route(`, `@<bp>.route(`, `app.add_url_rule(`, `methods=[...]` (default GET), blueprint `url_prefix` |
| FastAPI | `@app.get/post/put/delete/patch(`, `APIRouter(prefix=` |
| Express | `app.get/post/put/delete/patch(`, `router.<verb>(`, `app.use('/prefix', router)` |
| Django | `path(` / `re_path(` in `urls.py` |
| Spring | `@GetMapping`, `@PostMapping`, `@RequestMapping` |

Also note sample requests the project ships (`api.http`, Postman collections, README curl
examples) — reuse their payloads for the baseline.

---

## 7. Domain inference

Derive the domain from **entity names** (tables/models), route nouns and seed data. Write one
line: `<domain> (<main entities>)` — e.g. "E-commerce API (produtos, usuários, pedidos)",
"LMS with checkout (courses, enrollments, payments)", "Task manager (tasks, users, categories)".
Keep entity names in the language used in the code.

---

## 8. Architecture classification

Classify the **current** architecture with one of these labels + a one-line justification:

| Label | Signals |
|---|---|
| **Monolithic / no layers** | ≤ a handful of files; routes, SQL and business rules in the same file or the same functions; one module per *technical* concern only by name (e.g. `models.py` that also holds business rules for every domain) |
| **God Class** | One class/module wires DB connection, schema, routes and business logic (e.g. a `Manager` class with `initDb()` + `setupRoutes(app)`) |
| **Partially layered** | Folders like `models/`, `routes/`, `services/`, `utils/` exist **but** routes still hold business logic/queries, services are unused, or config is inline |
| **Layered MVC** | Separate config, models, controllers, routes/views, error handling, composition root — and they are respected |

Record for Phase 3 which layers **exist** and which are **missing** — this drives the strategy
(see `mvc-guidelines.md` § Strategy).

---

## 9. Output checklist (Phase 1)

- [ ] Language + version
- [ ] Framework + version
- [ ] Main dependencies
- [ ] Database engine + access style
- [ ] Domain (entities)
- [ ] Architecture label + justification
- [ ] Entry point + port
- [ ] Source file count + LOC (matches reality)
- [ ] Tables/models
- [ ] Endpoint inventory (count + table)
