from src.database import get_db, transaction

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_CANCELADO = "cancelado"
STATUS_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, "enviado", "entregue", STATUS_CANCELADO)

PRODUTO_DESCONHECIDO = "Desconhecido"

_SELECT_COM_ITENS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
"""


def _agrupar(rows):
    pedidos = {}
    for row in rows:
        pedido = pedidos.setdefault(row["id"], {
            "id": row["id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        })
        if row["produto_id"] is not None:
            pedido["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or PRODUTO_DESCONHECIDO,
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())


def listar(usuario_id=None):
    sql, params = _SELECT_COM_ITENS, ()
    if usuario_id is not None:
        sql += " WHERE p.usuario_id = ?"
        params = (usuario_id,)
    rows = get_db().execute(sql + " ORDER BY p.id, i.id", params).fetchall()
    return _agrupar(rows)


def criar(usuario_id, total):
    with transaction() as db:
        cursor = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, STATUS_PENDENTE, total),
        )
    return cursor.lastrowid


def adicionar_item(pedido_id, produto_id, quantidade, preco_unitario):
    with transaction() as db:
        db.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )


def atualizar_status(pedido_id, status):
    with transaction() as db:
        db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))


def resumo_vendas():
    row = get_db().execute(
        """
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS pendentes,
               COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS aprovados,
               COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS cancelados
        FROM pedidos
        """,
        (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO),
    ).fetchone()
    return dict(row)


def contar():
    return get_db().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]


def apagar_todos():
    with transaction() as db:
        db.execute("DELETE FROM itens_pedido")
        db.execute("DELETE FROM pedidos")
