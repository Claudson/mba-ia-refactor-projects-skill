"""Emissão de tokens de login assinados (itsdangerous, já dependência do Flask)."""
from itsdangerous import URLSafeTimedSerializer

TOKEN_SALT = 'auth-token'


def issue_token(user, secret_key):
    return URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT).dumps({'user_id': user.id})
