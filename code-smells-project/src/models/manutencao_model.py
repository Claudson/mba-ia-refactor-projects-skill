"""Acesso a dados das operacoes de manutencao usadas pelos endpoints /admin."""

import sqlite3

# Ordem que respeita as chaves estrangeiras (filhos antes dos pais).
TABELAS_EM_ORDEM_DE_EXCLUSAO = ("itens_pedido", "pedidos", "produtos", "usuarios")


def limpar_tabelas(conn):
    """Apaga todas as linhas das tabelas da aplicacao em uma unica transacao."""
    with conn:
        for tabela in TABELAS_EM_ORDEM_DE_EXCLUSAO:
            # Nome de tabela nao aceita placeholder; a lista acima e fixa no codigo.
            conn.execute("DELETE FROM %s" % tabela)


def consultar_somente_leitura(database_path, sql):
    """Executa uma consulta em conexao aberta em modo somente leitura."""
    conn = sqlite3.connect("file:%s?mode=ro" % database_path, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql).fetchall()]
    finally:
        conn.close()
