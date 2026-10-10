"""Guard de autorizacao para endpoints administrativos (P-13)."""

import hmac
import logging
from functools import wraps

from flask import current_app, request

from src.middlewares.error_handler import ForbiddenError, UnauthorizedError

logger = logging.getLogger(__name__)

HEADER_TOKEN = "X-Admin-Token"


def require_admin(view):
    """Exige o header X-Admin-Token igual ao ADMIN_TOKEN da configuracao.

    Sem ADMIN_TOKEN configurado os endpoints administrativos ficam desabilitados
    (403) em vez de abertos, como no projeto original.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        token = current_app.config.get("ADMIN_TOKEN")
        if not token:
            logger.warning("Acesso administrativo recusado: ADMIN_TOKEN nao configurado")
            raise ForbiddenError("Endpoint administrativo desabilitado")
        enviado = request.headers.get(HEADER_TOKEN, "")
        if not hmac.compare_digest(enviado, token):
            logger.warning("Acesso administrativo recusado: token invalido")
            raise UnauthorizedError("Nao autorizado")
        return view(*args, **kwargs)

    return wrapper
