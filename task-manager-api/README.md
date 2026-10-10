# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`, reorganizada em MVC (config, models, controllers, rotas, middlewares e composition root).

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # opcional: ajuste SECRET_KEY, ADMIN_TOKEN etc.
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (host, porta e debug vêm de `HOST`, `PORT` e `FLASK_DEBUG`). O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo. **Rode-o antes do primeiro boot**, senão os endpoints retornam listas vazias.

## Configuração

Todas as variáveis estão em `.env.example`:

- `SECRET_KEY`: assina os tokens de login. Sem ela, uma chave efêmera é gerada a cada boot.
- `ADMIN_TOKEN`: exigido no header `X-Admin-Token` para os endpoints `DELETE` (tasks, users e categories) e para atribuir ou alterar os roles `admin` e `manager`. Sem ele, essas operações retornam 403.
- `CORS_ORIGINS`: lista de origens permitidas, separadas por vírgula. Vazio desabilita o CORS.

## Estrutura

```
app.py              entry point (create_app + app.run)
app_factory.py      composition root
config.py           settings via variáveis de ambiente
database.py         instância do SQLAlchemy + criação do schema
models/             entidades, regras de domínio, serialização e consultas
controllers/        casos de uso + validação de entrada
routes/             blueprints (somente HTTP)
middlewares/        erros centralizados (JSON) e guard de admin
services/           emissão de token de login
```
