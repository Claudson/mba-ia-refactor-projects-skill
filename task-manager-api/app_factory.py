"""Composition root: monta a aplicação a partir da config."""
import logging

from flask import Flask
from flask_cors import CORS

from database import init_db
from middlewares.errors import register_error_handlers
from routes.category_routes import category_bp
from routes.report_routes import report_bp
from routes.system_routes import system_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp


def create_app(settings):
    logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    app = Flask(__name__)
    app.config.update(settings.flask_config())
    if settings.CORS_ORIGINS:
        CORS(app, origins=settings.CORS_ORIGINS)

    init_db(app)
    for blueprint in (system_bp, task_bp, user_bp, report_bp, category_bp):
        app.register_blueprint(blueprint)
    register_error_handlers(app)
    return app
