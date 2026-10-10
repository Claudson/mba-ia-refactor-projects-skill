"""Validacao de payloads de produto — fonte unica para criar e atualizar (P-12)."""

from src.middlewares.error_handler import ValidationError
from src.models import produto_model

_OBRIGATORIOS = (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque"))


def _numero(valor, mensagem):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValidationError(mensagem)
    return valor


def validar_payload(dados):
    """Valida o corpo de criacao/atualizacao e devolve os campos normalizados."""
    if not dados:
        raise ValidationError("Dados inválidos")

    for campo, rotulo in _OBRIGATORIOS:
        if campo not in dados:
            raise ValidationError("%s é obrigatório" % rotulo)

    nome = dados["nome"]
    if not isinstance(nome, str):
        raise ValidationError("Nome inválido")

    preco = _numero(dados["preco"], "Preço inválido")
    estoque = _numero(dados["estoque"], "Estoque inválido")

    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < produto_model.NOME_MIN_TAMANHO:
        raise ValidationError("Nome muito curto")
    if len(nome) > produto_model.NOME_MAX_TAMANHO:
        raise ValidationError("Nome muito longo")

    categoria = dados.get("categoria", produto_model.CATEGORIA_PADRAO)
    if categoria not in produto_model.CATEGORIAS_VALIDAS:
        raise ValidationError(
            "Categoria inválida. Válidas: %s" % str(list(produto_model.CATEGORIAS_VALIDAS))
        )

    return {
        "nome": nome,
        "descricao": dados.get("descricao", ""),
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }


def validar_filtros(termo, categoria, preco_min, preco_max):
    """Converte e valida os filtros da busca vindos da querystring."""

    def _para_float(valor, campo):
        if valor is None or valor == "":
            return None
        try:
            return float(valor)
        except (TypeError, ValueError):
            raise ValidationError("%s inválido" % campo) from None

    return {
        "termo": termo or None,
        "categoria": categoria or None,
        "preco_min": _para_float(preco_min, "preco_min"),
        "preco_max": _para_float(preco_max, "preco_max"),
    }
