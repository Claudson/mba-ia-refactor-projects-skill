from src.logger import get_logger
from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO

logger = get_logger(__name__)


def pedido_criado(pedido_id, usuario_id):
    logger.info("Notificação EMAIL: pedido %s criado para usuário %s", pedido_id, usuario_id)
    logger.info("Notificação SMS: pedido %s recebido", pedido_id)
    logger.info("Notificação PUSH: novo pedido %s recebido pelo sistema", pedido_id)


def status_alterado(pedido_id, status):
    if status == STATUS_APROVADO:
        logger.info("Notificação: pedido %s aprovado, preparar envio", pedido_id)
    elif status == STATUS_CANCELADO:
        logger.info("Notificação: pedido %s cancelado, devolver estoque", pedido_id)
