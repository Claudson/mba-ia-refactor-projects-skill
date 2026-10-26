from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.logger import get_logger

logger = get_logger(__name__)

ERROR_KEY = "erro"
MENSAGEM_ERRO_INTERNO = "Erro interno do servidor"
MENSAGENS_HTTP = {
    404: "Recurso não encontrado",
    405: "Método não permitido",
}


class AppError(Exception):
    def __init__(self, message, status=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.payload = payload or {}


class ValidationError(AppError):
    def __init__(self, message, payload=None):
        super().__init__(message, 400, payload)


class NotFoundError(AppError):
    def __init__(self, message, payload=None):
        super().__init__(message, 404, payload)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({ERROR_KEY: err.message, **err.payload}), err.status

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        return jsonify({ERROR_KEY: MENSAGENS_HTTP.get(err.code, err.description)}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro não tratado")
        return jsonify({ERROR_KEY: MENSAGEM_ERRO_INTERNO}), 500
