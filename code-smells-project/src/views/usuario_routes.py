"""Rotas HTTP de usuario e login."""

from flask import Blueprint, jsonify, request


def create_usuario_blueprint(usuario_controller):
    bp = Blueprint("usuarios", __name__)

    @bp.get("/usuarios")
    def listar_usuarios():
        return jsonify(usuario_controller["listar"]()), 200

    @bp.get("/usuarios/<int:usuario_id>")
    def buscar_usuario(usuario_id):
        return jsonify(usuario_controller["buscar"](usuario_id)), 200

    @bp.post("/usuarios")
    def criar_usuario():
        return jsonify(usuario_controller["criar"](request.get_json(silent=True))), 201

    @bp.post("/login")
    def login():
        return jsonify(usuario_controller["login"](request.get_json(silent=True))), 200

    return bp
