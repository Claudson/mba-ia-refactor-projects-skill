# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas gravadas com hash).

## Configuração

Toda a configuração vem de variáveis de ambiente (veja `.env.example`); todas têm default seguro:

| Variável | Default | Uso |
|---|---|---|
| `SECRET_KEY` | gerada a cada boot | chave de assinatura do Flask |
| `ADMIN_TOKEN` | — (admin desabilitado) | valor exigido no header `X-Admin-Token` de `POST /admin/reset-db` |
| `DEBUG` | `false` | debugger do Werkzeug |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | endereço do servidor |
| `DATABASE_PATH` | `loja.db` | arquivo SQLite |
| `CORS_ORIGINS` | `http://localhost:5000,http://127.0.0.1:5000` | origens liberadas para CORS |
| `LOG_LEVEL` | `INFO` | nível do log |

Exemplo (bash): `ADMIN_TOKEN=meu-token python app.py` e depois
`curl -X POST -H "X-Admin-Token: meu-token" http://localhost:5000/admin/reset-db`.

## Estrutura

```
app.py              entry point
src/app.py          create_app() — composition root
src/config/         configuração via variáveis de ambiente
src/database.py     conexão por requisição, transações, schema e seed
src/models/         acesso a dados por entidade (produto, usuario, pedido)
src/validators/     validação dos payloads
src/services/       fluxos de pedido, relatório, notificação e admin
src/controllers/    casos de uso por recurso
src/views/          Blueprints (rotas HTTP)
src/middlewares/    tratamento de erros centralizado e guard de admin
```
