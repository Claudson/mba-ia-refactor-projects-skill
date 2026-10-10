"""Rotas HTTP de relatorios."""

from flask import Blueprint, jsonify


def create_relatorio_blueprint(relatorio_controller):
    bp = Blueprint("relatorios", __name__)

    @bp.get("/relatorios/vendas")
    def relatorio_vendas():
        return jsonify(relatorio_controller["vendas"]()), 200

    return bp
