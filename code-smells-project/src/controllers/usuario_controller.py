from src.logger import get_logger
from src.middlewares.error_handler import AppError, NotFoundError
from src.models import usuario_model
from src.validators.usuario_validator import validar_login, validar_novo_usuario

logger = get_logger(__name__)


def listar_usuarios():
    return usuario_model.listar()


def buscar_usuario(usuario_id):
    usuario = usuario_model.buscar_por_id(usuario_id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar_usuario(dados):
    usuario = validar_novo_usuario(dados)
    usuario_id = usuario_model.criar(**usuario)
    logger.info("Usuário criado id=%s", usuario_id)
    return {"id": usuario_id}


def login(dados):
    email, senha = validar_login(dados)
    usuario = usuario_model.autenticar(email, senha)
    if not usuario:
        logger.info("Tentativa de login inválida")
        raise AppError("Email ou senha inválidos", 401, {"sucesso": False})
    logger.info("Login bem-sucedido id=%s", usuario["id"])
    return usuario
