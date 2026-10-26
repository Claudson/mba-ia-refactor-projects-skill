from src.database import transaction
from src.middlewares.error_handler import ValidationError
from src.models import pedido_model, produto_model, usuario_model
from src.services import notification_service

FALHA = {"sucesso": False}


class EstoqueInsuficiente(Exception):
    pass


def criar_pedido(usuario_id, itens):
    """Cria pedido, itens e baixa de estoque numa única transação."""
    if not usuario_model.existe(usuario_id):
        raise ValidationError("Usuário não encontrado", FALHA)

    total = 0
    linhas = []
    for item in itens:
        produto = produto_model.buscar_por_id(item["produto_id"])
        if produto is None:
            raise ValidationError("Produto " + str(item["produto_id"]) + " não encontrado", FALHA)
        if produto["estoque"] < item["quantidade"]:
            raise ValidationError("Estoque insuficiente para " + produto["nome"], FALHA)
        total = total + (produto["preco"] * item["quantidade"])
        linhas.append((produto, item["quantidade"]))

    try:
        with transaction():
            pedido_id = pedido_model.criar(usuario_id, total)
            for produto, quantidade in linhas:
                pedido_model.adicionar_item(pedido_id, produto["id"], quantidade, produto["preco"])
                if not produto_model.baixar_estoque(produto["id"], quantidade):
                    raise EstoqueInsuficiente(produto["nome"])
    except EstoqueInsuficiente as err:
        raise ValidationError("Estoque insuficiente para " + str(err), FALHA) from None

    notification_service.pedido_criado(pedido_id, usuario_id)
    return {"pedido_id": pedido_id, "total": total}


def atualizar_status(pedido_id, status):
    pedido_model.atualizar_status(pedido_id, status)
    notification_service.status_alterado(pedido_id, status)
