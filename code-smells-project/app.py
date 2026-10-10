"""Entry point: carrega a configuracao e sobe o servidor.

Toda a composicao da aplicacao fica em src/app.py (create_app).
"""

import logging

from src import logger as app_logger
from src.app import create_app
from src.config.settings import Settings

app_logger.configure()
logger = logging.getLogger(__name__)

settings = Settings()
app = create_app(settings)

if __name__ == "__main__":
    logger.info("Servidor iniciado em http://%s:%s", settings.HOST, settings.PORT)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
