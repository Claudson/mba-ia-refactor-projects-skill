from app_factory import create_app
from config import Settings

settings = Settings()
app = create_app(settings)

if __name__ == '__main__':
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
