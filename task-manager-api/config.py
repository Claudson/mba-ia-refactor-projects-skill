"""Configuração da aplicação lida de variáveis de ambiente (e de um .env opcional)."""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


class Settings:
    def __init__(self):
        self.SECRET_KEY = os.environ.get("SECRET_KEY")
        if not self.SECRET_KEY:
            logger.warning("SECRET_KEY não definida; usando chave efêmera (tokens expiram a cada restart)")
            self.SECRET_KEY = secrets.token_hex(32)
        self.SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") or None
        self.CORS_ORIGINS = _list("CORS_ORIGINS")
        self.DEBUG = _bool("FLASK_DEBUG", False)
        self.HOST = os.environ.get("HOST", "127.0.0.1")
        self.PORT = int(os.environ.get("PORT", "5000"))
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    def flask_config(self):
        return {key: getattr(self, key) for key in (
            "SECRET_KEY", "SQLALCHEMY_DATABASE_URI", "SQLALCHEMY_TRACK_MODIFICATIONS", "ADMIN_TOKEN",
        )}
