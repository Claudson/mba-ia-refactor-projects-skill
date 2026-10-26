from src.services import admin_service


def reset_db():
    admin_service.resetar_banco()
    return {"mensagem": "Banco de dados resetado", "sucesso": True}
