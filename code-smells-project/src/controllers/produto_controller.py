"""Casos de uso de produto (P-04). Nao conhece `request` nem `jsonify`."""

import logging

from src.middlewares.error_handler import ConflictError, NotFoundError
from src.models import produto_model
from src.validators import produto_validator

logger = logging.getLogger(__name__)

# O 404 de consulta por id preserva a chave "sucesso" do contrato original.
_PAYLOAD_CONSULTA = {"sucesso": False}


def create_produto_controller(db):
    def listar():
        return {"dados": produto_model.listar(db()), "sucesso": True}

    def buscar(produto_id):
        produto = produto_model.buscar_por_id(db(), produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado", payload=_PAYLOAD_CONSULTA)
        return {"dados": produto, "sucesso": True}

    def buscar_com_filtros(termo, categoria, preco_min, preco_max):
        filtros = produto_validator.validar_filtros(termo, categoria, preco_min, preco_max)
        resultados = produto_model.buscar(db(), **filtros)
        return {"dados": resultados, "total": len(resultados), "sucesso": True}

    def criar(dados):
        payload = produto_validator.validar_payload(dados)
        produto_id = produto_model.criar(db(), **payload)
        logger.info("Produto criado produto_id=%s", produto_id)
        return {"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}

    def atualizar(produto_id, dados):
        conn = db()
        if produto_model.buscar_por_id(conn, produto_id) is None:
            raise NotFoundError("Produto não encontrado")
        payload = produto_validator.validar_payload(dados)
        produto_model.atualizar(conn, produto_id, **payload)
        logger.info("Produto atualizado produto_id=%s", produto_id)
        return {"sucesso": True, "mensagem": "Produto atualizado"}

    def remover(produto_id):
        conn = db()
        if produto_model.buscar_por_id(conn, produto_id) is None:
            raise NotFoundError("Produto não encontrado")
        if produto_model.tem_pedidos_vinculados(conn, produto_id):
            raise ConflictError("Produto possui pedidos vinculados e não pode ser removido")
        produto_model.remover(conn, produto_id)
        logger.info("Produto removido produto_id=%s", produto_id)
        return {"sucesso": True, "mensagem": "Produto deletado"}

    return {
        "listar": listar,
        "buscar": buscar,
        "buscar_com_filtros": buscar_com_filtros,
        "criar": criar,
        "atualizar": atualizar,
        "remover": remover,
    }
