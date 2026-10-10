"""Validadores de entrada compartilhados pelos controllers (lançam ValidationError)."""
from datetime import datetime

from middlewares.errors import ValidationError


def require_payload(data):
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')
    return data


def parse_int(value, message):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(message)


def parse_date(value, fmt, message):
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, fmt)
    except ValueError:
        raise ValidationError(message)


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)
