import hmac
from functools import wraps

from flask import current_app, request

from src.middlewares.error_handler import AppError

ADMIN_HEADER = "X-Admin-Token"


def require_admin(view):
    """Exige o header X-Admin-Token igual ao ADMIN_TOKEN da config."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = current_app.config.get("ADMIN_TOKEN")
        if not token:
            raise AppError("Endpoint administrativo desabilitado", 403)
        enviado = request.headers.get(ADMIN_HEADER, "").encode()
        if not hmac.compare_digest(enviado, token.encode()):
            raise AppError("Não autorizado", 401)
        return view(*args, **kwargs)
    return wrapper
