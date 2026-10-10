"""Rotas HTTP de indice e health check."""

from flask import Blueprint, jsonify


def create_sistema_blueprint(sistema_controller):
    bp = Blueprint("sistema", __name__)

    @bp.get("/")
    def index():
        return jsonify(sistema_controller["index"]()), 200

    @bp.get("/health")
    def health_check():
        resultado = sistema_controller["health"]()
        status = 200 if resultado["status"] == "ok" else 500
        return jsonify(resultado), status

    return bp
