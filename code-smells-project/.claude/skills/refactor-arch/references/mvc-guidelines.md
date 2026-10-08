# MVC Architecture Guidelines (Phase 3 target)

The target is a **layered MVC** for HTTP APIs. In an API the *View* is the HTTP representation:
routes + serialization of responses. Dependencies point **inward only**:

```
HTTP request
   │
   ▼
Views / Routes  ──►  Controllers  ──►  (Services)  ──►  Models  ──►  Database
   ▲                     │                                 │
   └── Middlewares (error handling, auth) ◄── raise AppError ┘
Config ──► injected by the Composition Root (app factory) into every layer that needs it
```

## Layer responsibilities

| Layer | MUST | MUST NOT |
|---|---|---|
| **Config** (`config/`) | Read every setting from environment variables with safe *non-secret* defaults; expose one settings object; define per-env behaviour (debug off by default) | Contain secrets as literals; import other layers |
| **Models** (`models/`) | Own data access for **one** entity/aggregate (parameterized SQL or ORM); hold the entity's own domain rules (e.g. `is_overdue()`, `calculate_total()`), constants/enums (valid statuses) and safe serialization (`to_dict()` without secrets) | Know about HTTP (`request`, `jsonify`, `res`); build SQL by concatenation; print/log user secrets |
| **Services** (`services/`, optional) | Hold workflows that span several models or external systems (checkout, notifications, reports); be called by controllers | Know about HTTP; be instantiated with hardcoded credentials |
| **Controllers** (`controllers/`) | Orchestrate the use case: validate input, call models/services, decide the outcome; receive plain data (dict/params), return plain data or raise `AppError(status, message)` | Parse the raw HTTP request or build HTTP responses; contain SQL; duplicate rules that belong to a model |
| **Views / Routes** (`views/` or `routes/`) | Map `METHOD PATH` → controller; extract params/body/query; turn controller results into HTTP responses (status + JSON); be thin (≈ 5–15 lines per handler) | Contain business rules, queries or try/except per handler |
| **Middlewares** (`middlewares/`) | Centralized error handler (AppError → JSON with its status; unexpected → 500 with generic message + server-side log); auth/admin guards; request logging | Hide errors silently |
| **Composition root** (`app.py` / `app.js` factory) | Create the app, load config, init DB, register routes and middlewares, wire dependencies | Contain routes or business logic |
| **Entry point** | Start the server using config (host/port/debug) | Anything else |

### Rules
1. **One entity per model/controller/routes file** (`product_model`, `product_controller`, `product_routes`).
2. **No layer skipping:** routes never call models directly; models never import controllers.
3. **Single source of truth** for each rule, constant and serializer (no duplicated validation).
4. **Errors flow as exceptions** (`AppError`/`NotFoundError`/`ValidationError`) to the central
   handler — no `try/except` in every route.
5. **Dependencies injected** by the composition root (DB handle, config, services) — enable
   testing in isolation. Module-level mutable state is forbidden (constants are fine).
6. **Logging** through the language's logger, never `print`/`console.log` for events/errors.
7. **Config boots without `.env`:** every variable has a safe default except secrets; a missing
   `SECRET_KEY` is generated randomly at startup (with a warning); missing integration keys
   (payment, SMTP) disable that integration instead of crashing. Add `.env.example`.

## Reference layouts

### Python / Flask
```
<project>/
├── app.py                      # entry point (keeps the original run command working)
├── src/                        # (or a package named after the project)
│   ├── __init__.py
│   ├── app.py                  # create_app(config) — composition root
│   ├── config/settings.py      # env-based settings
│   ├── database.py             # connection lifecycle (per-request/app context), schema, seed
│   ├── models/<entity>_model.py
│   ├── services/<workflow>_service.py      # optional
│   ├── controllers/<entity>_controller.py
│   ├── views/<entity>_routes.py            # Blueprints (HTTP only)
│   ├── middlewares/error_handler.py        # AppError + @app.errorhandler
│   └── middlewares/auth.py                 # admin guard, if needed
├── .env.example
└── requirements.txt
```
Flask specifics: use an **app factory** (`create_app`), register Blueprints, keep sqlite
connections in `flask.g` (open per request, close in `teardown_appcontext`) or use the ORM session;
`app.run(debug=settings.DEBUG)`.

### Node.js / Express
```
<project>/
├── src/
│   ├── app.js                  # entry point: createApp() + listen (keeps `npm start`)
│   ├── server.js / createApp.js# composition root (optional split)
│   ├── config/index.js         # env-based settings
│   ├── database/connection.js  # open DB, promisified helpers (run/get/all), schema + seed
│   ├── models/<entity>Model.js # data access with parameterized queries
│   ├── services/<workflow>Service.js        # optional
│   ├── controllers/<entity>Controller.js    # async functions
│   ├── routes/<entity>Routes.js             # express.Router (HTTP only)
│   └── middlewares/errorHandler.js, asyncHandler.js
├── .env.example
└── package.json
```
Express specifics: wrap callback DB APIs into promises once (in `database/`), use `async/await`
everywhere, `asyncHandler` to forward rejections to the error middleware
(`app.use((err, req, res, next) => ...)` registered **last**).

### Other stacks
Map the same layers to the idiom of the framework (FastAPI routers + dependencies, NestJS
modules/controllers/providers, Spring `@RestController`/`@Service`/`@Repository`, Gin handlers +
services + repositories). The responsibilities table above is the contract.

## Strategy (choose in Phase 3.2)

| Current state (Phase 1) | Strategy |
|---|---|
| **Monolithic / God Class** | *Full extraction*: create the target tree, move each function to its layer (model → controller → route), split per entity, then delete the old files. |
| **Partially layered** (folders exist but routes are fat, services unused, config inline) | *In-place reorganization*: keep what is sound (e.g. ORM models), add the missing layers (config, controllers, error handler, app factory), move logic out of routes into controllers/models, fix security/quality findings in place. Moving everything under `src/` is optional — prefer the smaller diff if the structure is already MVC-compatible. |
| **Layered MVC** | Fix findings in place; no structural move. |

Keep auxiliary scripts (seed, migrations) working: update their imports to the new structure.

## API contract

Preserve: paths, methods, request field names, success/error status codes, top-level response
keys and error message texts.

Allowed **intentional** changes (must be listed in the Phase 3 summary):
1. Removing secret/sensitive fields from responses (`password`, `senha`, `secret_key`, hashes).
2. Guarding dangerous endpoints (admin/reset/raw-SQL) with an admin token from config
   (`X-Admin-Token` header) → `401/403` without it. Raw SQL consoles additionally restricted to
   read-only `SELECT`. Never silently delete an original endpoint.
3. Turning crashes (500 on bad input) into proper `400`/`404` responses.
4. Replacing fake/insecure behaviour (fake tokens, weak hashing) with a secure equivalent that
   keeps the same response keys.
5. Fixing data-integrity bugs (e.g. cascading deletes) without changing the response.
