# Guidelines de Arquitetura MVC (alvo da Fase 3)

O alvo é um **MVC em camadas** para APIs HTTP. Numa API, a *View* é a representação HTTP:
rotas + serialização das respostas. As dependências apontam **apenas para dentro**:

```
Requisição HTTP
   │
   ▼
Views / Routes  ──►  Controllers  ──►  (Services)  ──►  Models  ──►  Banco de dados
   ▲                     │                                 │
   └── Middlewares (tratamento de erros, auth) ◄── lançam AppError ┘
Config ──► injetada pelo Composition Root (app factory) em toda camada que precisar
```

## Responsabilidades das camadas

| Camada | DEVE | NÃO DEVE |
|---|---|---|
| **Config** (`config/`) | Ler toda configuração de variáveis de ambiente com defaults seguros *não secretos*; expor um único objeto de settings; definir comportamento por ambiente (debug desligado por padrão) | Conter segredos como literais; importar outras camadas |
| **Models** (`models/`) | Cuidar do acesso a dados de **uma** entidade/agregado (SQL parametrizado ou ORM); conter as regras de domínio da própria entidade (ex.: `is_overdue()`, `calculate_total()`), constantes/enums (status válidos) e serialização segura (`to_dict()` sem segredos) | Conhecer HTTP (`request`, `jsonify`, `res`); montar SQL por concatenação; imprimir/logar segredos de usuário |
| **Services** (`services/`, opcional) | Conter fluxos que envolvem vários models ou sistemas externos (checkout, notificações, relatórios); ser chamados pelos controllers | Conhecer HTTP; ser instanciados com credenciais hardcoded |
| **Controllers** (`controllers/`) | Orquestrar o caso de uso: validar entrada, chamar models/services, decidir o resultado; receber dados simples (dict/params) e devolver dados simples ou lançar `AppError(status, mensagem)` | Ler a requisição HTTP crua ou montar respostas HTTP; conter SQL; duplicar regras que pertencem a um model |
| **Views / Routes** (`views/` ou `routes/`) | Mapear `MÉTODO PATH` → controller; extrair params/body/query; transformar o resultado do controller em resposta HTTP (status + JSON); ser finas (≈ 5–15 linhas por handler) | Conter regras de negócio, queries ou try/except em cada handler |
| **Middlewares** (`middlewares/`) | Handler de erros centralizado (AppError → JSON com seu status; inesperado → 500 com mensagem genérica + log no servidor); guards de auth/admin; log de requisições | Esconder erros silenciosamente |
| **Composition root** (factory em `app.py` / `app.js`) | Criar a aplicação, carregar config, inicializar o banco, registrar rotas e middlewares, conectar as dependências | Conter rotas ou regra de negócio |
| **Entry point** | Subir o servidor usando a config (host/porta/debug) | Qualquer outra coisa |

### Regras
1. **Uma entidade por arquivo de model/controller/routes** (`product_model`, `product_controller`, `product_routes`).
2. **Sem pular camadas:** rotas nunca chamam models diretamente; models nunca importam controllers.
3. **Fonte única** para cada regra, constante e serializer (sem validação duplicada).
4. **Erros fluem como exceções** (`AppError`/`NotFoundError`/`ValidationError`) até o handler
   central — sem `try/except` em cada rota.
5. **Dependências injetadas** pelo composition root (handle do banco, config, services) —
   permitindo testes isolados. Estado mutável em nível de módulo é proibido (constantes podem).
6. **Logs** pelo logger da linguagem, nunca `print`/`console.log` para eventos/erros.
7. **A config sobe sem `.env`:** toda variável tem default seguro, exceto segredos; um
   `SECRET_KEY` ausente é gerado aleatoriamente no startup (com warning); chaves de integração
   ausentes (pagamento, SMTP) desativam a integração em vez de derrubar a aplicação. Crie `.env.example`.

## Layouts de referência

### Python / Flask
```
<projeto>/
├── app.py                      # entry point (mantém o comando de execução original funcionando)
├── src/                        # (ou um pacote com o nome do projeto)
│   ├── __init__.py
│   ├── app.py                  # create_app(config) — composition root
│   ├── config/settings.py      # settings baseadas em variáveis de ambiente
│   ├── database.py             # ciclo de vida da conexão (por requisição/app context), schema, seed
│   ├── models/<entidade>_model.py
│   ├── services/<fluxo>_service.py         # opcional
│   ├── controllers/<entidade>_controller.py
│   ├── views/<entidade>_routes.py          # Blueprints (só HTTP)
│   ├── middlewares/error_handler.py        # AppError + @app.errorhandler
│   └── middlewares/auth.py                 # guard de admin, se necessário
├── .env.example
└── requirements.txt
```
Específico de Flask: use **app factory** (`create_app`), registre Blueprints, mantenha conexões
sqlite em `flask.g` (abre por requisição, fecha em `teardown_appcontext`) ou use a sessão do ORM;
`app.run(debug=settings.DEBUG)`.

### Node.js / Express
```
<projeto>/
├── src/
│   ├── app.js                  # entry point: createApp() + listen (mantém o `npm start`)
│   ├── server.js / createApp.js# composition root (separação opcional)
│   ├── config/index.js         # settings baseadas em variáveis de ambiente
│   ├── database/connection.js  # abre o banco, helpers com promise (run/get/all), schema + seed
│   ├── models/<entidade>Model.js # acesso a dados com queries parametrizadas
│   ├── services/<fluxo>Service.js           # opcional
│   ├── controllers/<entidade>Controller.js  # funções async
│   ├── routes/<entidade>Routes.js           # express.Router (só HTTP)
│   └── middlewares/errorHandler.js, asyncHandler.js
├── .env.example
└── package.json
```
Específico de Express: encapsule uma vez as APIs de banco com callback em promises (em
`database/`), use `async/await` em tudo, `asyncHandler` para encaminhar rejeições ao middleware
de erro (`app.use((err, req, res, next) => ...)` registrado **por último**).

### Outras stacks
Mapeie as mesmas camadas para o idioma do framework (routers + dependencies no FastAPI,
modules/controllers/providers no NestJS, `@RestController`/`@Service`/`@Repository` no Spring,
handlers + services + repositories no Gin). A tabela de responsabilidades acima é o contrato.

## Estratégia (escolher na Fase 3.2)

| Estado atual (Fase 1) | Estratégia |
|---|---|
| **Monolítica / God Class** | *Extração completa*: criar a árvore alvo, mover cada função para sua camada (model → controller → route), separar por entidade e apagar os arquivos antigos. |
| **Parcialmente em camadas** (pastas existem, mas rotas gordas, services sem uso, config inline) | *Reorganização no lugar*: manter o que está correto (ex.: models do ORM), adicionar as camadas que faltam (config, controllers, handler de erros, app factory), tirar a lógica das rotas para controllers/models e corrigir os findings de segurança/qualidade no lugar. Mover tudo para `src/` é opcional — prefira o menor diff se a estrutura já for compatível com MVC. |
| **MVC em camadas** | Corrigir os findings no lugar; sem mudança estrutural. |

Mantenha scripts auxiliares (seed, migrações) funcionando: atualize seus imports para a nova estrutura.

## Contrato da API

Preserve: paths, métodos, nomes dos campos de requisição, status codes de sucesso/erro, chaves
de primeiro nível das respostas e textos das mensagens de erro.

**O relatório da Fase 2 é a especificação da Fase 3.** Quando um finding recomenda uma mudança
de contrato (remover uma rota, exigir credencial, tirar um campo), ela é aplicada exatamente como
recomendada — a preservação do contrato vale para todo o resto. Nenhuma regra desta seção
autoriza manter, "suavizar" ou trocar por outra solução algo que a auditoria mandou remover.

Mudanças **intencionais** permitidas (devem ser listadas no resumo da Fase 3):
1. Remover campos secretos/sensíveis das respostas (`password`, `senha`, `secret_key`, hashes).
2. **Remover endpoints de execução arbitrária** (SQL, código ou comando vindos da requisição),
   quando o finding recomendar (catálogo AP-05, playbook P-13a). A rota deixa de ser registrada
   (`404`/`405`), sem versão "restrita". Nenhum outro endpoint pode ser removido, e nenhuma
   remoção pode acontecer sem um finding que a recomende.
3. Proteger operações administrativas legítimas (reset, relatórios internos, exclusões) com um
   token de admin vindo da config (header `X-Admin-Token`) → `401/403` sem ele (playbook P-13b).
4. Transformar crashes (500 em entrada inválida) em respostas `400`/`404` adequadas.
5. Substituir comportamento falso/inseguro (tokens falsos, hash fraco) por um equivalente seguro
   que mantenha as mesmas chaves de resposta.
6. Corrigir bugs de integridade de dados (ex.: exclusão em cascata) sem mudar a resposta.
