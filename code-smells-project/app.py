from src.app import create_app
from src.config.settings import Settings
from src.logger import get_logger

settings = Settings()
app = create_app(settings)

if __name__ == "__main__":
    get_logger(__name__).info("Servidor iniciado em http://%s:%s", settings.HOST, settings.PORT)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
