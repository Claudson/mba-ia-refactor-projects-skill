"""Rotas HTTP administrativas, protegidas pelo guard de admin (P-13)."""

from flask import Blueprint, jsonify, request

from src.middlewares.auth import require_admin


def create_admin_blueprint(admin_controller):
    bp = Blueprint("admin", __name__)

    @bp.post("/admin/reset-db")
    @require_admin
    def reset_database():
        return jsonify(admin_controller["reset_db"]()), 200

    @bp.post("/admin/query")
    @require_admin
    def executar_query():
        resultado = admin_controller["executar_consulta"](request.get_json(silent=True))
        return jsonify(resultado), 200

    return bp
