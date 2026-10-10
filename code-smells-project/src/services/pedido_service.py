"""Regras de negocio de pedidos e relatorio de vendas (P-04, P-09, P-12)."""

import logging

from src.middlewares.error_handler import BusinessRuleError, NotFoundError
from src.models import pedido_model, usuario_model
from src.validators.pedido_validator import PAYLOAD_PEDIDO

logger = logging.getLogger(__name__)


def create_pedido_service(notification_service):
    def criar(conn, usuario_id, itens):
        """Valida estoque, calcula o total e grava tudo em uma transacao."""
        if not usuario_model.existe(conn, usuario_id):
            raise BusinessRuleError("Usuário não encontrado", payload=PAYLOAD_PEDIDO)

        produtos = pedido_model.buscar_produtos_para_pedido(
            conn, {item["produto_id"] for item in itens}
        )

        total = 0
        itens_para_gravar = []
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise BusinessRuleError(
                    "Produto %s não encontrado" % item["produto_id"], payload=PAYLOAD_PEDIDO
                )
            if produto["estoque"] < item["quantidade"]:
                raise BusinessRuleError(
                    "Estoque insuficiente para %s" % produto["nome"], payload=PAYLOAD_PEDIDO
                )
            total += produto["preco"] * item["quantidade"]
            itens_para_gravar.append(
                {
                    "produto_id": produto["id"],
                    "produto_nome": produto["nome"],
                    "quantidade": item["quantidade"],
                    "preco_unitario": produto["preco"],
                }
            )

        try:
            pedido_id = pedido_model.criar(conn, usuario_id, total, itens_para_gravar)
        except pedido_model.EstoqueIndisponivel as err:
            # Perda de corrida com outra requisicao: a transacao foi revertida.
            raise BusinessRuleError(str(err), payload=PAYLOAD_PEDIDO) from err

        logger.info("Pedido criado pedido_id=%s itens=%s", pedido_id, len(itens_para_gravar))
        notification_service["pedido_criado"](pedido_id)
        return {"pedido_id": pedido_id, "total": total}

    def atualizar_status(conn, pedido_id, novo_status):
        if not pedido_model.atualizar_status(conn, pedido_id, novo_status):
            raise NotFoundError("Pedido não encontrado")
        logger.info("Status alterado pedido_id=%s status=%s", pedido_id, novo_status)
        notification_service["status_alterado"](pedido_id, novo_status)

    def relatorio_vendas(conn):
        resumo = pedido_model.resumo_vendas(conn)
        total_pedidos = resumo["total_pedidos"]
        faturamento = resumo["faturamento"]
        desconto = pedido_model.desconto_para(faturamento)
        por_status = resumo["por_status"]
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": por_status.get(pedido_model.STATUS_PENDENTE, 0),
            "pedidos_aprovados": por_status.get(pedido_model.STATUS_APROVADO, 0),
            "pedidos_cancelados": por_status.get(pedido_model.STATUS_CANCELADO, 0),
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos else 0,
        }

    return {
        "criar": criar,
        "atualizar_status": atualizar_status,
        "relatorio_vendas": relatorio_vendas,
    }
