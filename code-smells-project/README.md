# code-smells-project

API de E-commerce em Python/Flask, refatorada para MVC em camadas pela skill `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

O comando de execução é o mesmo de antes. A aplicação sobe em `http://127.0.0.1:5000` (o bind
deixou de ser `0.0.0.0` por padrão) e o banco SQLite (`loja.db`) é criado automaticamente no
primeiro boot, já com produtos e usuários de exemplo.

## Configuração

Toda a configuração vem de variáveis de ambiente — veja `.env.example` para a lista completa.
Nenhuma variável é obrigatória para subir a aplicação:

| Variável | Default | Observação |
|---|---|---|
| `SECRET_KEY` | chave efêmera | gerada no boot com warning se ausente |
| `FLASK_DEBUG` | `false` | nunca ligar em produção |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | |
| `DATABASE_PATH` | `loja.db` | |
| `LOG_LEVEL` | `INFO` | |
| `ADMIN_TOKEN` | *(vazio)* | sem ele, `/admin/*` responde 403 |
| `CORS_ORIGINS` | *(vazio)* | sem ele, CORS fica desabilitado |

Exemplo habilitando os endpoints administrativos (PowerShell):

```powershell
$env:ADMIN_TOKEN = "um-token-qualquer"; python app.py
```

As rotas `/admin/reset-db` e `/admin/query` exigem o header `X-Admin-Token` com esse valor, e
`/admin/query` aceita apenas um único `SELECT`, executado em conexão somente leitura.

## Usuários de exemplo

As senhas do seed são gravadas com hash (`werkzeug.security`). Credenciais para teste:

| Email | Senha | Tipo |
|---|---|---|
| `admin@loja.com` | `admin123` | admin |
| `joao@email.com` | `123456` | cliente |
| `maria@email.com` | `senha123` | cliente |

Um `loja.db` criado pela versão anterior guarda senhas em texto puro e não funciona com o login
atual — apague o arquivo para que o seed seja recriado com hash.

## Estrutura

```
app.py                      entry point (lê settings e sobe o servidor)
src/app.py                  composition root (create_app)
src/config/settings.py      configuração por variável de ambiente
src/database.py             conexão por requisição, schema (com FKs) e seed
src/models/                 acesso a dados por entidade (SQL parametrizado) + regras da entidade
src/services/               fluxos com várias entidades (pedido transacional, relatório, notificações)
src/validators/             validação de payloads (fonte única para criar/atualizar)
src/controllers/            casos de uso, sem conhecer HTTP
src/views/                  blueprints Flask (apenas HTTP)
src/middlewares/            handler de erros central e guard de admin
```
