"""Casos de uso de pedido (P-04). A regra de negocio vive no pedido_service."""

from src.models import pedido_model
from src.validators import pedido_validator


def create_pedido_controller(db, pedido_service):
    def criar(dados):
        payload = pedido_validator.validar_criacao(dados)
        resultado = pedido_service["criar"](db(), payload["usuario_id"], payload["itens"])
        return {
            "dados": resultado,
            "sucesso": True,
            "mensagem": "Pedido criado com sucesso",
        }

    def listar():
        return {"dados": pedido_model.listar(db()), "sucesso": True}

    def listar_por_usuario(usuario_id):
        return {"dados": pedido_model.listar_por_usuario(db(), usuario_id), "sucesso": True}

    def atualizar_status(pedido_id, dados):
        novo_status = pedido_validator.validar_status(dados)
        pedido_service["atualizar_status"](db(), pedido_id, novo_status)
        return {"sucesso": True, "mensagem": "Status atualizado"}

    return {
        "criar": criar,
        "listar": listar,
        "listar_por_usuario": listar_por_usuario,
        "atualizar_status": atualizar_status,
    }
