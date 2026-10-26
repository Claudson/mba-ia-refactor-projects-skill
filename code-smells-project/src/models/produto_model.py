from src.database import get_db, transaction

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"
NOME_MIN = 2
NOME_MAX = 200

CAMPOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def to_dict(row):
    return {campo: row[campo] for campo in CAMPOS}


def listar():
    rows = get_db().execute("SELECT * FROM produtos WHERE ativo = 1").fetchall()
    return [to_dict(row) for row in rows]


def buscar_por_id(produto_id):
    row = get_db().execute("SELECT * FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)).fetchone()
    return to_dict(row) if row else None


def buscar(termo, categoria=None, preco_min=None, preco_max=None):
    clauses, params = ["ativo = 1"], []
    if termo:
        clauses.append("(nome LIKE ? OR descricao LIKE ?)")
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        clauses.append("categoria = ?")
        params.append(categoria)
    if preco_min:
        clauses.append("preco >= ?")
        params.append(preco_min)
    if preco_max:
        clauses.append("preco <= ?")
        params.append(preco_max)
    rows = get_db().execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params).fetchall()
    return [to_dict(row) for row in rows]


def criar(nome, descricao, preco, estoque, categoria):
    with transaction() as db:
        cursor = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(produto_id, nome, descricao, preco, estoque, categoria):
    with transaction() as db:
        db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? "
            "WHERE id = ? AND ativo = 1",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )


def desativar(produto_id):
    """Exclusão lógica: mantém o produto para o histórico de pedidos."""
    with transaction() as db:
        db.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))


def baixar_estoque(produto_id, quantidade):
    """Decrementa o estoque só se houver saldo; devolve False quando não há."""
    with transaction() as db:
        cursor = db.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND ativo = 1 AND estoque >= ?",
            (quantidade, produto_id, quantidade),
        )
    return cursor.rowcount == 1


def contar_ativos():
    return get_db().execute("SELECT COUNT(*) FROM produtos WHERE ativo = 1").fetchone()[0]


def apagar_todos():
    with transaction() as db:
        db.execute("DELETE FROM produtos")
