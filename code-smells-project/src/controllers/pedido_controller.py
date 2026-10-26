from src.models import pedido_model
from src.services import pedido_service
from src.validators.pedido_validator import validar_novo_pedido, validar_status


def criar_pedido(dados):
    usuario_id, itens = validar_novo_pedido(dados)
    return pedido_service.criar_pedido(usuario_id, itens)


def listar_todos_pedidos():
    return pedido_model.listar()


def listar_pedidos_usuario(usuario_id):
    return pedido_model.listar(usuario_id)


def atualizar_status_pedido(pedido_id, dados):
    pedido_service.atualizar_status(pedido_id, validar_status(dados))
