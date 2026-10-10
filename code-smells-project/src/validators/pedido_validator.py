"""Validacao de payloads de pedido (P-12)."""

from src.middlewares.error_handler import ValidationError
from src.models import pedido_model

# Erros de regra de pedido preservam a chave "sucesso" do contrato original.
PAYLOAD_PEDIDO = {"sucesso": False}


def validar_criacao(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not isinstance(itens, list):
        raise ValidationError("Itens deve ser uma lista")

    normalizados = []
    for item in itens:
        if not isinstance(item, dict) or "produto_id" not in item or "quantidade" not in item:
            raise ValidationError("Cada item precisa de produto_id e quantidade")
        quantidade = item["quantidade"]
        if not isinstance(quantidade, int) or isinstance(quantidade, bool) or quantidade <= 0:
            raise ValidationError("Quantidade deve ser um inteiro maior que zero")
        normalizados.append({"produto_id": item["produto_id"], "quantidade": quantidade})

    return {"usuario_id": usuario_id, "itens": normalizados}


def validar_status(dados):
    novo_status = (dados or {}).get("status", "")
    if novo_status not in pedido_model.STATUS_VALIDOS:
        raise ValidationError("Status inválido")
    return novo_status
