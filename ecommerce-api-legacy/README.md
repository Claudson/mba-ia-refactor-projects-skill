# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
cp .env.example .env   # opcional: ajuste ADMIN_TOKEN e as demais variáveis
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória (`DATABASE_PATH=:memory:`)
e já carrega seeds automaticamente no boot.

A configuração vem de variáveis de ambiente (ou do arquivo `.env`, carregado automaticamente em
Node ≥ 21.7). Veja `.env.example`.

## Endpoints administrativos

`GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header
`X-Admin-Token: <ADMIN_TOKEN>`. Sem token configurado eles respondem `403`; com token inválido, `401`.

## Estrutura

```
src/
├── app.js            # entry point (npm start)
├── createApp.js      # composition root: monta banco, models, services, controllers e rotas
├── config/           # configuração por variáveis de ambiente
├── database/         # conexão SQLite com promises/transações, schema e seed
├── models/           # acesso a dados por entidade (SQL parametrizado)
├── services/         # checkout, relatório financeiro, gateway de pagamento
├── controllers/      # validação de entrada e orquestração dos casos de uso
├── routes/           # mapeamento HTTP (express.Router)
├── middlewares/      # asyncHandler, requireAdmin, tratamento de erros central
├── errors.js         # AppError e subclasses
└── utils/            # logger e hash de senhas (scrypt)
```

Exemplos de requisições estão em `api.http`.
