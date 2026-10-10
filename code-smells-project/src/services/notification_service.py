"""Notificacoes de pedido, isoladas do controller (P-04, P-14).

No projeto original estes efeitos colaterais eram `print` dentro do handler
HTTP. Aqui ficam em um servico injetado, sem dados pessoais nas mensagens.
"""

import logging

from src.models import pedido_model

logger = logging.getLogger(__name__)


def create_notification_service():
    """Implementacao de log. Um gateway real entraria aqui sem tocar o controller."""

    def pedido_criado(pedido_id):
        logger.info("Notificacao de pedido criado enviada pedido_id=%s", pedido_id)

    def status_alterado(pedido_id, novo_status):
        if novo_status == pedido_model.STATUS_APROVADO:
            logger.info("Pedido aprovado, preparar envio pedido_id=%s", pedido_id)
        elif novo_status == pedido_model.STATUS_CANCELADO:
            logger.info("Pedido cancelado, devolver estoque pedido_id=%s", pedido_id)

    return {"pedido_criado": pedido_criado, "status_alterado": status_alterado}
