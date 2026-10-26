from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings
from src.database import init_db
from src.logger import configure_logging, get_logger
from src.middlewares.error_handler import register_error_handlers
from src.views.admin_routes import admin_bp
from src.views.pedido_routes import pedido_bp
from src.views.produto_routes import produto_bp
from src.views.relatorio_routes import relatorio_bp
from src.views.sistema_routes import sistema_bp
from src.views.usuario_routes import usuario_bp

BLUEPRINTS = (sistema_bp, produto_bp, usuario_bp, pedido_bp, relatorio_bp, admin_bp)


def create_app(settings=None):
    """Composition root: config, logging, banco, CORS, rotas e tratamento de erros."""
    settings = settings or Settings()
    configure_logging(settings.LOG_LEVEL)
    logger = get_logger(__name__)
    if settings.secret_key_generated:
        logger.warning("SECRET_KEY não definida; usando chave efêmera gerada no startup")
    if not settings.ADMIN_TOKEN:
        logger.warning("ADMIN_TOKEN não definido; endpoints administrativos desabilitados")

    app = Flask(__name__)
    app.config.update(settings.as_flask_config())
    CORS(app, origins=settings.CORS_ORIGINS)

    init_db(app)
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
    register_error_handlers(app)
    return app
