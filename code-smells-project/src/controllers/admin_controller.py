"""Casos de uso administrativos (P-13).

O console de SQL deixa de executar comandos arbitrarios: aceita um unico
SELECT, executado pelo model em conexao somente leitura.
"""

import logging
import sqlite3

from src.middlewares.error_handler import ForbiddenError, ValidationError
from src.models import manutencao_model

logger = logging.getLogger(__name__)


def create_admin_controller(db, database_path):
    def reset_db():
        manutencao_model.limpar_tabelas(db())
        logger.warning("Banco de dados resetado via endpoint administrativo")
        return {"mensagem": "Banco de dados resetado", "sucesso": True}

    def executar_consulta(dados):
        sql = ((dados or {}).get("sql") or "").strip()
        if not sql:
            raise ValidationError("Query não informada")

        comando = sql.rstrip(";").strip()
        if ";" in comando:
            raise ValidationError("Apenas uma consulta por requisição")
        if not comando.upper().startswith("SELECT"):
            raise ForbiddenError("Apenas consultas SELECT são permitidas")

        try:
            linhas = manutencao_model.consultar_somente_leitura(database_path, comando)
        except sqlite3.Error as err:
            logger.warning("Consulta administrativa rejeitada pelo banco")
            raise ValidationError("Consulta inválida") from err

        logger.info("Consulta administrativa executada linhas=%s", len(linhas))
        return {"dados": linhas, "sucesso": True}

    return {"reset_db": reset_db, "executar_consulta": executar_consulta}
