"""Excecoes de dominio e tratamento de erros centralizado (P-10).

Substitui o `try/except Exception -> jsonify({"erro": str(e)})` repetido em
todos os handlers do projeto original: o detalhe interno vai para o log e o
cliente recebe uma mensagem generica.
"""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

CHAVE_ERRO = "erro"


class AppError(Exception):
    """Erro de aplicacao traduzido para resposta HTTP pelo handler central."""

    status = 400

    def __init__(self, message, status=None, payload=None):
        super().__init__(message)
        self.message = message
        if status is not None:
            self.status = status
        # `payload` preserva chaves extras do contrato original (ex.: "sucesso": False).
        self.payload = payload or {}


class ValidationError(AppError):
    status = 400


class NotFoundError(AppError):
    status = 404


class BusinessRuleError(AppError):
    status = 400


class ConflictError(AppError):
    status = 409


class UnauthorizedError(AppError):
    status = 401


class ForbiddenError(AppError):
    status = 403


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def _handle_app_error(err):
        logger.info("Erro de aplicacao %s: %s", err.status, err.message)
        return jsonify({CHAVE_ERRO: err.message, **err.payload}), err.status

    @app.errorhandler(HTTPException)
    def _handle_http_exception(err):
        # Mantem os 404/405 do Flask, mas em JSON (a API nunca devolve HTML).
        return jsonify({CHAVE_ERRO: err.description}), err.code

    @app.errorhandler(Exception)
    def _handle_unexpected(err):
        logger.exception("Erro nao tratado: %s", err)
        return jsonify({CHAVE_ERRO: "Erro interno do servidor"}), 500
