"""Composition root: cria a aplicacao e conecta as dependencias (P-03, P-06)."""

import logging

from flask import Flask
from flask_cors import CORS

from src import database, logger as app_logger
from src.controllers.admin_controller import create_admin_controller
from src.controllers.pedido_controller import create_pedido_controller
from src.controllers.produto_controller import create_produto_controller
from src.controllers.relatorio_controller import create_relatorio_controller
from src.controllers.sistema_controller import create_sistema_controller
from src.controllers.usuario_controller import create_usuario_controller
from src.middlewares.error_handler import register_error_handlers
from src.services.notification_service import create_notification_service
from src.services.pedido_service import create_pedido_service
from src.views.admin_routes import create_admin_blueprint
from src.views.pedido_routes import create_pedido_blueprint
from src.views.produto_routes import create_produto_blueprint
from src.views.relatorio_routes import create_relatorio_blueprint
from src.views.sistema_routes import create_sistema_blueprint
from src.views.usuario_routes import create_usuario_blueprint

logger = logging.getLogger(__name__)


def create_app(settings):
    app_logger.configure(settings.LOG_LEVEL)

    app = Flask(__name__)
    app.config.update(settings.as_flask_config())

    if settings.CORS_ORIGINS:
        CORS(app, origins=settings.CORS_ORIGINS)
    else:
        logger.info("CORS desabilitado (CORS_ORIGINS vazio)")

    database.init_app(app)
    db = database.get_connection

    notification_service = create_notification_service()
    pedido_service = create_pedido_service(notification_service)

    blueprints = (
        create_sistema_blueprint(create_sistema_controller(db, settings.APP_VERSION)),
        create_produto_blueprint(create_produto_controller(db)),
        create_usuario_blueprint(create_usuario_controller(db)),
        create_pedido_blueprint(create_pedido_controller(db, pedido_service)),
        create_relatorio_blueprint(create_relatorio_controller(db, pedido_service)),
        create_admin_blueprint(create_admin_controller(db, settings.DATABASE_PATH)),
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    register_error_handlers(app)
    logger.info("Aplicacao criada com %s blueprints", len(blueprints))
    return app
