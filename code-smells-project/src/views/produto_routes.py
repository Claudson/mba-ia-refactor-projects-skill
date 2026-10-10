"""Rotas HTTP de produto. Apenas traducao HTTP <-> controller."""

from flask import Blueprint, jsonify, request


def create_produto_blueprint(produto_controller):
    bp = Blueprint("produtos", __name__)

    @bp.get("/produtos")
    def listar_produtos():
        return jsonify(produto_controller["listar"]()), 200

    @bp.get("/produtos/busca")
    def buscar_produtos():
        resultado = produto_controller["buscar_com_filtros"](
            request.args.get("q", ""),
            request.args.get("categoria"),
            request.args.get("preco_min"),
            request.args.get("preco_max"),
        )
        return jsonify(resultado), 200

    @bp.get("/produtos/<int:produto_id>")
    def buscar_produto(produto_id):
        return jsonify(produto_controller["buscar"](produto_id)), 200

    @bp.post("/produtos")
    def criar_produto():
        return jsonify(produto_controller["criar"](request.get_json(silent=True))), 201

    @bp.put("/produtos/<int:produto_id>")
    def atualizar_produto(produto_id):
        resultado = produto_controller["atualizar"](produto_id, request.get_json(silent=True))
        return jsonify(resultado), 200

    @bp.delete("/produtos/<int:produto_id>")
    def deletar_produto(produto_id):
        return jsonify(produto_controller["remover"](produto_id)), 200

    return bp
