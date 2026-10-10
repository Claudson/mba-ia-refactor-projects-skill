"""Casos de uso de usuario e autenticacao (P-04, P-07)."""

import logging

from src.middlewares.error_handler import NotFoundError, UnauthorizedError, ValidationError
from src.models import usuario_model
from src.validators import usuario_validator

logger = logging.getLogger(__name__)

# O 401 de login preserva a chave "sucesso" do contrato original.
_PAYLOAD_LOGIN = {"sucesso": False}


def create_usuario_controller(db):
    def listar():
        return {"dados": usuario_model.listar(db()), "sucesso": True}

    def buscar(usuario_id):
        usuario = usuario_model.buscar_por_id(db(), usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return {"dados": usuario, "sucesso": True}

    def criar(dados):
        payload = usuario_validator.validar_cadastro(dados)
        usuario_id = usuario_model.criar(db(), **payload)
        if usuario_id is None:
            raise ValidationError("Email já cadastrado")
        logger.info("Usuario criado usuario_id=%s", usuario_id)
        return {"dados": {"id": usuario_id}, "sucesso": True}

    def login(dados):
        credenciais = usuario_validator.validar_login(dados)
        usuario = usuario_model.autenticar(db(), **credenciais)
        if usuario is None:
            logger.info("Tentativa de login recusada")
            raise UnauthorizedError("Email ou senha inválidos", payload=_PAYLOAD_LOGIN)
        logger.info("Login efetuado usuario_id=%s", usuario["id"])
        return {"dados": usuario, "sucesso": True, "mensagem": "Login OK"}

    return {"listar": listar, "buscar": buscar, "criar": criar, "login": login}
