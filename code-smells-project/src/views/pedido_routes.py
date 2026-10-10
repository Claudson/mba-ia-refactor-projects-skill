"""Rotas HTTP de pedido."""

from flask import Blueprint, jsonify, request


def create_pedido_blueprint(pedido_controller):
    bp = Blueprint("pedidos", __name__)

    @bp.post("/pedidos")
    def criar_pedido():
        return jsonify(pedido_controller["criar"](request.get_json(silent=True))), 201

    @bp.get("/pedidos")
    def listar_todos_pedidos():
        return jsonify(pedido_controller["listar"]()), 200

    @bp.get("/pedidos/usuario/<int:usuario_id>")
    def listar_pedidos_usuario(usuario_id):
        return jsonify(pedido_controller["listar_por_usuario"](usuario_id)), 200

    @bp.put("/pedidos/<int:pedido_id>/status")
    def atualizar_status_pedido(pedido_id):
        resultado = pedido_controller["atualizar_status"](
            pedido_id, request.get_json(silent=True)
        )
        return jsonify(resultado), 200

    return bp
