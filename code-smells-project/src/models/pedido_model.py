"""Acesso a dados e regras da entidade pedido (P-02, P-05, P-09, P-12)."""

STATUS_PENDENTE = "pendente"
STATUS_VALIDOS = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
STATUS_APROVADO = "aprovado"
STATUS_CANCELADO = "cancelado"

# (faturamento minimo, taxa de desconto) — avaliadas da maior faixa para a menor.
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))

CAMPOS_PEDIDO = ("id", "usuario_id", "status", "total", "criado_em")

_SQL_LISTAGEM = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario,
           pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    %s
    ORDER BY p.id, i.id
"""


class EstoqueIndisponivel(Exception):
    """Levantada quando a baixa de estoque nao pode ser aplicada."""

    def __init__(self, produto_nome):
        super().__init__("Estoque insuficiente para %s" % produto_nome)
        self.produto_nome = produto_nome


def desconto_para(faturamento):
    """Desconto aplicavel conforme a faixa de faturamento."""
    return next(
        (faturamento * taxa for minimo, taxa in FAIXAS_DESCONTO if faturamento > minimo),
        0,
    )


def _agrupar(rows):
    """Converte o resultado do JOIN em pedidos com seus itens (sem queries extras)."""
    pedidos = {}
    for row in rows:
        pedido = pedidos.get(row["id"])
        if pedido is None:
            pedido = {campo: row[campo] for campo in CAMPOS_PEDIDO}
            pedido["itens"] = []
            pedidos[row["id"]] = pedido
        if row["produto_id"] is not None:
            pedido["itens"].append(
                {
                    "produto_id": row["produto_id"],
                    "produto_nome": row["produto_nome"] or "Desconhecido",
                    "quantidade": row["quantidade"],
                    "preco_unitario": row["preco_unitario"],
                }
            )
    return list(pedidos.values())


def listar(conn):
    return _agrupar(conn.execute(_SQL_LISTAGEM % "").fetchall())


def listar_por_usuario(conn, usuario_id):
    rows = conn.execute(_SQL_LISTAGEM % "WHERE p.usuario_id = ?", (usuario_id,)).fetchall()
    return _agrupar(rows)


def buscar_produtos_para_pedido(conn, produto_ids):
    """Carrega em uma unica query os produtos usados pelo pedido (evita N+1)."""
    if not produto_ids:
        return {}
    marcadores = ", ".join("?" * len(produto_ids))
    rows = conn.execute(
        "SELECT id, nome, preco, estoque FROM produtos WHERE id IN (%s)" % marcadores,
        list(produto_ids),
    ).fetchall()
    return {row["id"]: dict(row) for row in rows}


def criar(conn, usuario_id, total, itens):
    """Cria pedido, itens e baixa de estoque em uma unica transacao.

    `itens` e uma lista de dicts com produto_id, quantidade, preco_unitario e
    produto_nome. A baixa de estoque e condicional, de modo que duas requisicoes
    concorrentes nao podem derrubar o estoque abaixo de zero.
    """
    with conn:
        cursor = conn.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, STATUS_PENDENTE, total),
        )
        pedido_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
            "VALUES (?, ?, ?, ?)",
            [
                (pedido_id, item["produto_id"], item["quantidade"], item["preco_unitario"])
                for item in itens
            ],
        )
        for item in itens:
            baixa = conn.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (item["quantidade"], item["produto_id"], item["quantidade"]),
            )
            if baixa.rowcount == 0:
                raise EstoqueIndisponivel(item["produto_nome"])
    return pedido_id


def atualizar_status(conn, pedido_id, novo_status):
    with conn:
        cursor = conn.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id)
        )
    return cursor.rowcount > 0


def resumo_vendas(conn):
    """Totais por status em uma unica query agregada (antes: cinco queries)."""
    rows = conn.execute(
        "SELECT status, COUNT(*) AS quantidade, COALESCE(SUM(total), 0) AS soma "
        "FROM pedidos GROUP BY status"
    ).fetchall()
    por_status = {row["status"]: row for row in rows}
    return {
        "total_pedidos": sum(row["quantidade"] for row in rows),
        "faturamento": sum(row["soma"] for row in rows),
        "por_status": {status: row["quantidade"] for status, row in por_status.items()},
    }


def contar(conn):
    return conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
