"""Validacao de payloads de usuario e login (P-12)."""

import re

from src.middlewares.error_handler import ValidationError

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_cadastro(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not isinstance(email, str) or not _EMAIL.match(email):
        raise ValidationError("Email inválido")
    if not isinstance(senha, str):
        raise ValidationError("Senha inválida")

    return {"nome": nome, "email": email, "senha": senha}


def validar_login(dados):
    dados = dados or {}
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")

    return {"email": email, "senha": senha}
