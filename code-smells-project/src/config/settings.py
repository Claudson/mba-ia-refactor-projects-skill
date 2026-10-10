"""Configuracao da aplicacao lida de variaveis de ambiente (P-01).

Nenhum segredo aparece como literal neste arquivo. Toda variavel tem default
seguro, exceto os segredos: SECRET_KEY ausente gera uma chave efemera com
warning, e ADMIN_TOKEN ausente desabilita os endpoints administrativos.
"""

import logging
import os
import secrets

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"


def _bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _int(name, default):
    valor = os.environ.get(name, "").strip()
    try:
        return int(valor) if valor else default
    except ValueError:
        logger.warning("%s invalido (%r); usando %s", name, valor, default)
        return default


def _lista(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


class Settings:
    """Objeto unico de settings, construido a partir do ambiente."""

    def __init__(self, env=None):
        env = env if env is not None else os.environ

        self.SECRET_KEY = env.get("SECRET_KEY") or secrets.token_hex(32)
        if not env.get("SECRET_KEY"):
            logger.warning("SECRET_KEY nao definida; usando chave efemera desta execucao")

        self.DEBUG = _bool("FLASK_DEBUG", False)
        self.HOST = env.get("HOST", "127.0.0.1")
        self.PORT = _int("PORT", 5000)
        self.DATABASE_PATH = env.get("DATABASE_PATH", "loja.db")
        self.LOG_LEVEL = env.get("LOG_LEVEL", "INFO").upper()
        self.APP_VERSION = APP_VERSION

        # Ausente -> endpoints /admin/* respondem 403 (desabilitados).
        self.ADMIN_TOKEN = env.get("ADMIN_TOKEN") or None
        if not self.ADMIN_TOKEN:
            logger.warning("ADMIN_TOKEN nao definida; endpoints administrativos desabilitados")

        # Vazio -> CORS desligado (default seguro, em vez do antigo CORS(app) aberto).
        self.CORS_ORIGINS = _lista("CORS_ORIGINS")

    def as_flask_config(self):
        return {
            "SECRET_KEY": self.SECRET_KEY,
            "DEBUG": self.DEBUG,
            "DATABASE_PATH": self.DATABASE_PATH,
            "ADMIN_TOKEN": self.ADMIN_TOKEN,
            "APP_VERSION": self.APP_VERSION,
        }
