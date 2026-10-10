"""Smoke test sem dependências: chama todos os endpoints de um projeto e registra status + corpo.

Uso:
    python scripts/smoke_test.py <projeto> [--base-url URL] [--out arquivo.json] [--header 'Nome: valor']

Projetos: code-smells-project | ecommerce-api-legacy | task-manager-api
A saída JSON permite comparar o comportamento antes/depois da refatoração (ver compare).
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

SUITES = {
    "code-smells-project": {
        "base_url": "http://127.0.0.1:5000",
        "requests": [
            ("GET", "/", None),
            ("GET", "/health", None),
            ("GET", "/produtos", None),
            ("GET", "/produtos/1", None),
            ("GET", "/produtos/9999", None),
            ("GET", "/produtos/busca?q=mouse", None),
            ("GET", "/produtos/busca?categoria=informatica&preco_min=100&preco_max=500", None),
            ("POST", "/produtos", {"nome": "Produto Teste", "descricao": "desc", "preco": 10.5, "estoque": 5, "categoria": "geral"}),
            ("POST", "/produtos", {"nome": "X"}),
            ("PUT", "/produtos/1", {"nome": "Notebook Gamer", "descricao": "Notebook potente para jogos", "preco": 5999.99, "estoque": 10, "categoria": "informatica"}),
            ("DELETE", "/produtos/11", None),
            ("GET", "/usuarios", None),
            ("GET", "/usuarios/1", None),
            ("GET", "/usuarios/9999", None),
            ("POST", "/usuarios", {"nome": "Teste", "email": "teste@email.com", "senha": "senha123"}),
            ("POST", "/login", {"email": "joao@email.com", "senha": "123456"}),
            ("POST", "/login", {"email": "joao@email.com", "senha": "errada"}),
            ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 1}, {"produto_id": 3, "quantidade": 2}]}),
            ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 9999, "quantidade": 1}]}),
            ("GET", "/pedidos", None),
            ("GET", "/pedidos/usuario/2", None),
            ("PUT", "/pedidos/1/status", {"status": "aprovado"}),
            ("PUT", "/pedidos/1/status", {"status": "invalido"}),
            ("GET", "/relatorios/vendas", None),
            ("POST", "/admin/query", {"sql": "SELECT COUNT(*) AS total FROM produtos"}),
            ("POST", "/admin/reset-db", None),
        ],
    },
    "ecommerce-api-legacy": {
        "base_url": "http://127.0.0.1:3000",
        "requests": [
            ("POST", "/api/checkout", {"usr": "Guilherme", "eml": "gui@fullcycle.com.br", "pwd": "senhaforte", "c_id": 2, "card": "4111222233334444"}),
            ("POST", "/api/checkout", {"usr": "João", "eml": "joao@teste.com", "pwd": "123", "c_id": 1, "card": "5111222233334444"}),
            ("POST", "/api/checkout", {"usr": "Leonan", "eml": "leonan@fullcycle.com.br", "c_id": 2, "card": "4111000011112222"}),
            ("POST", "/api/checkout", {"usr": "Sem curso", "eml": "x@x.com", "c_id": 999, "card": "4111"}),
            ("POST", "/api/checkout", {"usr": "Incompleto"}),
            ("GET", "/api/admin/financial-report", None),
            ("DELETE", "/api/users/1", None),
        ],
    },
    "task-manager-api": {
        "base_url": "http://127.0.0.1:5000",
        "requests": [
            ("GET", "/", None),
            ("GET", "/health", None),
            ("GET", "/tasks", None),
            ("GET", "/tasks/1", None),
            ("GET", "/tasks/9999", None),
            ("GET", "/tasks/search?q=login", None),
            ("GET", "/tasks/search?status=pending&priority=1", None),
            ("GET", "/tasks/stats", None),
            ("POST", "/tasks", {"title": "Nova task", "description": "desc", "priority": 2, "user_id": 1, "category_id": 1, "due_date": "2030-01-01", "tags": ["a", "b"]}),
            ("POST", "/tasks", {"title": "x"}),
            ("PUT", "/tasks/1", {"status": "in_progress", "priority": 2}),
            ("PUT", "/tasks/1", {"status": "invalido"}),
            ("DELETE", "/tasks/11", None),
            ("GET", "/users", None),
            ("GET", "/users/1", None),
            ("GET", "/users/9999", None),
            ("POST", "/users", {"name": "Novo", "email": "novo@email.com", "password": "1234", "role": "user"}),
            ("POST", "/users", {"name": "Novo", "email": "novo@email.com", "password": "1234"}),
            ("PUT", "/users/2", {"name": "Maria Santos Silva"}),
            ("GET", "/users/1/tasks", None),
            ("POST", "/login", {"email": "joao@email.com", "password": "1234"}),
            ("POST", "/login", {"email": "joao@email.com", "password": "errada"}),
            ("GET", "/reports/summary", None),
            ("GET", "/reports/user/1", None),
            ("GET", "/categories", None),
            ("POST", "/categories", {"name": "Docs", "description": "Documentação", "color": "#123456"}),
            ("PUT", "/categories/5", {"name": "Documentação"}),
            ("DELETE", "/categories/5", None),
            ("DELETE", "/users/4", None),
        ],
    },
}


def call(base_url, method, path, body, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base_url + path, data=data, method=method, headers=headers or {})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception as e:  # conexão recusada, timeout etc.
        return None, f"<{type(e).__name__}: {e}>"
    text = raw.decode("utf-8", errors="replace")
    try:
        return status, json.loads(text)
    except ValueError:
        return status, text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", choices=SUITES)
    parser.add_argument("--base-url")
    parser.add_argument("--out")
    parser.add_argument("--header", action="append", default=[], metavar="'Nome: valor'",
                        help="header extra em todas as requisições (ex.: 'X-Admin-Token: abc')")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    suite = SUITES[args.project]
    base_url = args.base_url or suite["base_url"]
    headers = dict(h.split(":", 1) for h in args.header)
    headers = {k.strip(): v.strip() for k, v in headers.items()}
    results, failures = [], 0
    for method, path, body in suite["requests"]:
        status, payload = call(base_url, method, path, body, headers)
        if status is None or status >= 500:
            failures += 1
        preview = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
        print(f"{method:6} {path:70} -> {status}  {preview[:90]}")
        results.append({"method": method, "path": path, "body": body, "status": status, "response": payload})

    print(f"\n{len(results)} requests | {failures} falhas (sem resposta ou 5xx)")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
