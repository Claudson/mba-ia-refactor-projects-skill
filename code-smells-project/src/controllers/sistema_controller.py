from src.models import pedido_model, produto_model, usuario_model

ENDPOINTS = {
    "produtos": "/produtos",
    "usuarios": "/usuarios",
    "pedidos": "/pedidos",
    "login": "/login",
    "relatorios": "/relatorios/vendas",
    "health": "/health",
}


def index(versao):
    return {"mensagem": "Bem-vindo à API da Loja", "versao": versao, "endpoints": ENDPOINTS}


def health(versao):
    return {
        "status": "ok",
        "database": "connected",
        "counts": {
            "produtos": produto_model.contar_ativos(),
            "usuarios": usuario_model.contar(),
            "pedidos": pedido_model.contar(),
        },
        "versao": versao,
    }
