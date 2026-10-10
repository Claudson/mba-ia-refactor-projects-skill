"""Ciclo de vida da conexao SQLite, schema e seed (P-06, P-09).

Substitui a conexao global mutavel do projeto original: cada requisicao recebe
sua propria conexao, guardada em ``flask.g`` e fechada no teardown do contexto.
"""

import logging
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        preco REAL NOT NULL,
        estoque INTEGER NOT NULL,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
        produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
        quantidade INTEGER NOT NULL,
        preco_unitario REAL NOT NULL
    )
    """,
)

_PRODUTOS_SEED = (
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
)

# Usuarios de demonstracao. As senhas sao gravadas com hash (P-07), nunca em claro.
_USUARIOS_SEED = (
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
)


def connect(database_path):
    """Abre uma conexao configurada (row_factory + integridade referencial ativa)."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_connection():
    """Conexao da requisicao atual, criada sob demanda."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_connection(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_schema(conn):
    with conn:
        for ddl in _SCHEMA:
            conn.execute(ddl)


def seed(conn):
    """Popula o banco com dados de exemplo, apenas se estiver vazio."""
    if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]:
        return False
    with conn:
        conn.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
            "VALUES (?, ?, ?, ?, ?)",
            _PRODUTOS_SEED,
        )
        conn.executemany(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            [
                (nome, email, generate_password_hash(senha), tipo)
                for nome, email, senha, tipo in _USUARIOS_SEED
            ],
        )
    logger.info("Banco populado com dados de exemplo")
    return True


def init_app(app):
    """Registra o teardown e garante schema + seed no startup."""
    app.teardown_appcontext(close_connection)
    with app.app_context():
        conn = get_connection()
        init_schema(conn)
        seed(conn)
