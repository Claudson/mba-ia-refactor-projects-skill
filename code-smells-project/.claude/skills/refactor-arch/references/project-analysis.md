# Análise de Projeto — Heurísticas (Fase 1)

Objetivo: montar uma visão precisa e baseada em evidências do projeto **antes** de julgá-lo. Todo
valor impresso no bloco da Fase 1 deve vir de um arquivo que você leu, nunca de suposições.

---

## 1. Inventário de arquivos

Conte e leia apenas **arquivos-fonte escritos pelos autores do projeto**.

| Sempre excluir | Motivo |
|---|---|
| `node_modules/`, `venv/`, `.venv/`, `env/`, `vendor/`, `site-packages/` | dependências |
| `.git/`, `.claude/`, `.idea/`, `.vscode/` | ferramentas |
| `__pycache__/`, `dist/`, `build/`, `target/`, `bin/`, `obj/`, `coverage/` | artefatos de build |
| `*.db`, `*.sqlite*`, `*.log`, lockfiles (`package-lock.json`, `poetry.lock`, `yarn.lock`) | dados / gerados (leia lockfiles só para obter versões exatas) |

Fonte = arquivos de código (`.py .js .ts .mjs .cjs .java .kt .go .rb .php .cs .rs`) **mais**
scripts de seed / migração. Conte manifestos e documentação separadamente (não somam em
"Source files"). Informe `N files analyzed (~LOC lines)` — conte LOC com `wc -l` (ou equivalente)
sobre o conjunto de fontes.

---

## 2. Linguagem e versão

| Arquivo de evidência | Linguagem | Origem da versão |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` | Python | `python_requires`, `.python-version`, `runtime.txt`, `FROM python:X` no Dockerfile — senão `python --version` |
| `package.json` | JavaScript / TypeScript (`tsconfig.json` ou arquivos `.ts` → TS) | `engines.node`, `.nvmrc` — senão `node --version` |
| `pom.xml`, `build.gradle(.kts)` | Java / Kotlin | `maven.compiler.source`, `sourceCompatibility` |
| `go.mod` | Go | diretiva `go` |
| `Gemfile` | Ruby | diretiva `ruby` |
| `composer.json` | PHP | `require.php` |
| `*.csproj` | C# | `TargetFramework` |
| `Cargo.toml` | Rust | `edition` / `rust-version` |

Se houver vários manifestos, vale a linguagem do entry point; mencione os demais.

---

## 3. Detecção de framework

Procure no manifesto **e** confirme com um import/uso no código.

| Linguagem | Dependência no manifesto | Sinal no código | Framework |
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

**Versão:** versão exata do lockfile/pacote instalado, se disponível; senão a restrição do
manifesto como escrita (ex.: `Express ^4.18.2`). Nunca invente um número de patch.

Liste também as bibliotecas relevantes (CORS, ORM, validação, auth, clientes HTTP, e-mail) em *Dependencies*.

---

## 4. Banco de dados e acesso a dados

| Sinal | Engine | Estilo de acesso |
|---|---|---|
| `import sqlite3`, `sqlite3.connect(`, npm `sqlite3`/`better-sqlite3`, `:memory:` | SQLite (arquivo ou memória) | SQL puro |
| `psycopg2`, `pg`, `postgres://` | PostgreSQL | SQL puro ou ORM |
| `pymysql`, `mysql2`, `mysql://` | MySQL | SQL puro ou ORM |
| `pymongo`, `mongoose`, `mongodb://` | MongoDB | driver / ODM |
| `flask_sqlalchemy`, `sqlalchemy`, `db.Model` | conforme URI do SQLAlchemy | ORM |
| `sequelize`, `typeorm`, `prisma`, `knex` | conforme config | ORM / query builder |

Tabelas/models: colete de `CREATE TABLE`, `__tablename__`, subclasses de `db.Model`, definições
de models do ORM ou arquivos de migração. Anote onde o schema é criado (ex.: "criado dentro de
`get_db()` na primeira chamada", "`db.create_all()` no import").

---

## 5. Entry point e runtime

- Entry point: `if __name__ == "__main__"` / `app.run(`, `main`/`scripts.start` do `package.json`,
  `app.listen(`, `main()` em Go/Java. Registre porta e host.
- Como executar: primeiro o README do projeto, depois os scripts do manifesto.
- **Interpretador / dependências:** se existir um virtualenv local (`venv/`, `.venv/`), execute
  com o interpretador dele (`venv/Scripts/python` no Windows, `venv/bin/python` nos demais); em
  Node, rode `npm install` apenas se `node_modules/` não existir. Se faltarem dependências,
  instale-as a partir do manifesto antes do baseline — nunca no interpretador global sem perguntar.
- **Estado de runtime** (necessário para o baseline da Fase 3): identifique arquivos de banco e
  scripts de seed.
  - Um arquivo de banco **ignorado pelo git** e **recriado automaticamente** (schema + seed no
    boot, ou por um script de seed documentado) é estado descartável: pode ser apagado antes de
    cada rodada de validação para que baseline e pós-refatoração partam dos mesmos dados.
  - Nunca apague um arquivo de banco versionado ou não reproduzível — copie-o para o diretório
    temporário e restaure-o depois.
  - Bancos em memória resetam a cada boot — nada a fazer.
- Atenção a reloaders de debug (Flask `debug=True`, nodemon): eles criam um processo filho — ao
  parar a aplicação, encerre a árvore de processos inteira / tudo que escuta na porta.

---

## 6. Inventário de endpoints

Encontre todo registro de rota e anote `MÉTODO PATH → handler arquivo:linha`:

| Stack | Padrões a buscar |
|---|---|
| Flask | `@app.route(`, `@<bp>.route(`, `app.add_url_rule(`, `methods=[...]` (padrão GET), `url_prefix` de blueprint |
| FastAPI | `@app.get/post/put/delete/patch(`, `APIRouter(prefix=` |
| Express | `app.get/post/put/delete/patch(`, `router.<verbo>(`, `app.use('/prefixo', router)` |
| Django | `path(` / `re_path(` em `urls.py` |
| Spring | `@GetMapping`, `@PostMapping`, `@RequestMapping` |

Anote também requisições de exemplo que o projeto fornece (`api.http`, coleções Postman, curl no
README) — reutilize esses payloads no baseline.

---

## 7. Inferência de domínio

Derive o domínio a partir dos **nomes das entidades** (tabelas/models), substantivos das rotas e
dados de seed. Escreva uma linha: `<domínio> (<entidades principais>)` — ex.: "API de E-commerce
(produtos, usuários, pedidos)", "LMS com checkout (courses, enrollments, payments)", "Task manager
(tasks, users, categories)". Mantenha os nomes das entidades no idioma do código.

---

## 8. Classificação da arquitetura

Classifique a arquitetura **atual** com um destes rótulos + justificativa em uma linha:

| Rótulo | Sinais |
|---|---|
| **Monolítica / sem camadas** | Poucos arquivos; rotas, SQL e regras de negócio no mesmo arquivo ou nas mesmas funções; separação só no nome (ex.: um `models.py` que também contém regras de negócio de todos os domínios) |
| **God Class** | Uma classe/módulo cuida de conexão, schema, rotas e regra de negócio (ex.: uma classe `Manager` com `initDb()` + `setupRoutes(app)`) |
| **Parcialmente em camadas** | Existem pastas como `models/`, `routes/`, `services/`, `utils/` **mas** as rotas ainda têm regra de negócio/queries, os services não são usados ou a config está inline |
| **MVC em camadas** | Config, models, controllers, routes/views, tratamento de erros e composition root separados — e respeitados |

Registre para a Fase 3 quais camadas **existem** e quais **faltam** — isso define a estratégia
(ver `mvc-guidelines.md` § Estratégia).

---

## 9. Checklist de saída (Fase 1)

- [ ] Linguagem + versão
- [ ] Framework + versão
- [ ] Dependências principais
- [ ] Engine de banco + estilo de acesso
- [ ] Domínio (entidades)
- [ ] Rótulo da arquitetura + justificativa
- [ ] Entry point + porta
- [ ] Quantidade de arquivos-fonte + LOC (condizente com a realidade)
- [ ] Tabelas/models
- [ ] Inventário de endpoints (quantidade + tabela)
