"""Casos de uso de informacao da API: indice e health check (P-04, P-08)."""

import logging
import sqlite3

from src.models import pedido_model, produto_model, usuario_model

logger = logging.getLogger(__name__)

_ENDPOINTS = {
    "produtos": "/produtos",
    "usuarios": "/usuarios",
    "pedidos": "/pedidos",
    "login": "/login",
    "relatorios": "/relatorios/vendas",
    "health": "/health",
}


def create_sistema_controller(db, versao):
    def index():
        return {
            "mensagem": "Bem-vindo à API da Loja",
            "versao": versao,
            "endpoints": _ENDPOINTS,
        }

    def health():
        """Somente status e contagens — nunca valores de configuracao."""
        try:
            conn = db()
            counts = {
                "produtos": produto_model.contar(conn),
                "usuarios": usuario_model.contar(conn),
                "pedidos": pedido_model.contar(conn),
            }
        except sqlite3.Error:
            logger.exception("Health check falhou ao consultar o banco")
            return {"status": "erro", "detalhes": "Banco de dados indisponível"}
        return {
            "status": "ok",
            "database": "connected",
            "counts": counts,
            "versao": versao,
        }

    return {"index": index, "health": health}
