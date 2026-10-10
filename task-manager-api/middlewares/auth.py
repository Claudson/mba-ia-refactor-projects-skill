"""Guard de administração: exige o header X-Admin-Token igual a ADMIN_TOKEN da config."""
import hmac
from functools import wraps

from flask import current_app, request

from middlewares.errors import ForbiddenError, UnauthorizedError

ADMIN_HEADER = 'X-Admin-Token'


def is_admin_request():
    token = current_app.config.get('ADMIN_TOKEN')
    return bool(token) and hmac.compare_digest(request.headers.get(ADMIN_HEADER, ''), token)


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_app.config.get('ADMIN_TOKEN'):
            raise ForbiddenError('Operação administrativa desabilitada')
        if not is_admin_request():
            raise UnauthorizedError('Não autorizado')
        return view(*args, **kwargs)
    return wrapper
