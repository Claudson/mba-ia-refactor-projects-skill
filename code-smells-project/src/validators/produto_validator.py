from src.middlewares.error_handler import ValidationError
from src.models.produto_model import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_MAX, NOME_MIN

CAMPOS_OBRIGATORIOS = (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque"))


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def validar_produto(dados):
    """Valida o payload de criação/atualização e devolve os campos normalizados."""
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    for campo, rotulo in CAMPOS_OBRIGATORIOS:
        if campo not in dados:
            raise ValidationError(f"{rotulo} é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome deve ser texto")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser texto")
    if not _numero(preco):
        raise ValidationError("Preço deve ser numérico")
    if not isinstance(estoque, int) or isinstance(estoque, bool):
        raise ValidationError("Estoque deve ser um número inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def validar_filtro_preco(valor, nome_parametro):
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        raise ValidationError(f"Parâmetro {nome_parametro} inválido") from None
