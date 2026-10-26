from src.logger import get_logger
from src.middlewares.error_handler import NotFoundError
from src.models import produto_model
from src.validators.produto_validator import validar_filtro_preco, validar_produto

logger = get_logger(__name__)

NAO_ENCONTRADO = "Produto não encontrado"


def listar_produtos():
    produtos = produto_model.listar()
    logger.info("Listando %d produtos", len(produtos))
    return produtos


def buscar_produto(produto_id):
    produto = produto_model.buscar_por_id(produto_id)
    if not produto:
        raise NotFoundError(NAO_ENCONTRADO, {"sucesso": False})
    return produto


def buscar_produtos(filtros):
    return produto_model.buscar(
        filtros.get("q", ""),
        filtros.get("categoria"),
        validar_filtro_preco(filtros.get("preco_min"), "preco_min"),
        validar_filtro_preco(filtros.get("preco_max"), "preco_max"),
    )


def criar_produto(dados):
    produto = validar_produto(dados)
    produto_id = produto_model.criar(**produto)
    logger.info("Produto criado id=%s", produto_id)
    return {"id": produto_id}


def _garantir_existe(produto_id):
    if not produto_model.buscar_por_id(produto_id):
        raise NotFoundError(NAO_ENCONTRADO)


def atualizar_produto(produto_id, dados):
    _garantir_existe(produto_id)
    produto = validar_produto(dados)
    produto_model.atualizar(produto_id, **produto)


def deletar_produto(produto_id):
    _garantir_existe(produto_id)
    produto_model.desativar(produto_id)
    logger.info("Produto %s desativado", produto_id)
