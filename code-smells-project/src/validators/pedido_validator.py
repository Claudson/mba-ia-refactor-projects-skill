from src.middlewares.error_handler import ValidationError
from src.models.pedido_model import STATUS_VALIDOS


def _inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def validar_novo_pedido(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not _inteiro(usuario_id):
        raise ValidationError("Usuario ID inválido")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not isinstance(itens, list):
        raise ValidationError("Itens inválidos")
    for item in itens:
        if not isinstance(item, dict) or not _inteiro(item.get("produto_id")):
            raise ValidationError("Item inválido: produto_id é obrigatório")
        if not _inteiro(item.get("quantidade")) or item["quantidade"] <= 0:
            raise ValidationError("Item inválido: quantidade deve ser um inteiro maior que zero")

    return usuario_id, [{"produto_id": i["produto_id"], "quantidade": i["quantidade"]} for i in itens]


def validar_status(dados):
    status = dados.get("status", "") if isinstance(dados, dict) else ""
    if status not in STATUS_VALIDOS:
        raise ValidationError("Status inválido")
    return status
