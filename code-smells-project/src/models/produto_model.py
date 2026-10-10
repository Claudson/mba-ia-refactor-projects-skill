"""Acesso a dados e regras da entidade produto (P-02, P-03, P-08, P-12)."""

# Constantes de dominio: fonte unica para validadores e controllers.
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"
NOME_MIN_TAMANHO = 2
NOME_MAX_TAMANHO = 200

CAMPOS_PUBLICOS = (
    "id",
    "nome",
    "descricao",
    "preco",
    "estoque",
    "categoria",
    "ativo",
    "criado_em",
)


def serializar(row):
    """Serializador unico da entidade (evita o mapeamento duplicado do original)."""
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS}


def listar(conn):
    rows = conn.execute("SELECT * FROM produtos").fetchall()
    return [serializar(row) for row in rows]


def buscar_por_id(conn, produto_id):
    row = conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return serializar(row) if row else None


def buscar(conn, termo=None, categoria=None, preco_min=None, preco_max=None):
    """Busca com filtros opcionais; apenas fragmentos fixos de SQL sao concatenados."""
    clausulas = ["1=1"]
    params = []
    if termo:
        clausulas.append("(nome LIKE ? OR descricao LIKE ?)")
        params.extend(["%%%s%%" % termo, "%%%s%%" % termo])
    if categoria:
        clausulas.append("categoria = ?")
        params.append(categoria)
    if preco_min is not None:
        clausulas.append("preco >= ?")
        params.append(preco_min)
    if preco_max is not None:
        clausulas.append("preco <= ?")
        params.append(preco_max)

    sql = "SELECT * FROM produtos WHERE %s" % " AND ".join(clausulas)
    return [serializar(row) for row in conn.execute(sql, params).fetchall()]


def criar(conn, nome, descricao, preco, estoque, categoria):
    with conn:
        cursor = conn.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
            "VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(conn, produto_id, nome, descricao, preco, estoque, categoria):
    with conn:
        cursor = conn.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, "
            "categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )
    return cursor.rowcount > 0


def remover(conn, produto_id):
    with conn:
        cursor = conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    return cursor.rowcount > 0


def tem_pedidos_vinculados(conn, produto_id):
    row = conn.execute(
        "SELECT 1 FROM itens_pedido WHERE produto_id = ? LIMIT 1", (produto_id,)
    ).fetchone()
    return row is not None


def contar(conn):
    return conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
