"""Caso de uso de relatorio de vendas (P-04)."""


def create_relatorio_controller(db, pedido_service):
    def vendas():
        return {"dados": pedido_service["relatorio_vendas"](db()), "sucesso": True}

    return {"vendas": vendas}
