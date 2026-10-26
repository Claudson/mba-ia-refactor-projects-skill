from src.database import transaction
from src.logger import get_logger
from src.models import pedido_model, produto_model, usuario_model

logger = get_logger(__name__)


def resetar_banco():
    with transaction():
        pedido_model.apagar_todos()
        produto_model.apagar_todos()
        usuario_model.apagar_todos()
    logger.warning("Banco de dados resetado via endpoint administrativo")
