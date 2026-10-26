import logging
import os
import secrets

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"


def _bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _list(name, default):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """Configuração lida de variáveis de ambiente, com defaults seguros e não secretos."""

    def __init__(self):
        self.SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
        self.DEBUG = _bool("DEBUG", False)
        self.HOST = os.environ.get("HOST", "127.0.0.1")
        self.PORT = int(os.environ.get("PORT", "5000"))
        self.DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
        self.ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") or None
        self.CORS_ORIGINS = _list("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000")
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.VERSION = APP_VERSION
        self.secret_key_generated = not os.environ.get("SECRET_KEY")

    def as_flask_config(self):
        return {
            "SECRET_KEY": self.SECRET_KEY,
            "DEBUG": self.DEBUG,
            "DATABASE_PATH": self.DATABASE_PATH,
            "ADMIN_TOKEN": self.ADMIN_TOKEN,
            "VERSION": self.VERSION,
        }
