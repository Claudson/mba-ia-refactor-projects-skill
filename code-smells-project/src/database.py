import sqlite3
from contextlib import contextmanager

from flask import current_app, g
from werkzeug.security import generate_password_hash

from src.logger import get_logger

logger = get_logger(__name__)

HASH_PREFIXES = ("scrypt:", "pbkdf2:")

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
)

SEED_PRODUTOS = (
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

# Usuários de demonstração; as senhas são gravadas com hash no seed.
SEED_USUARIOS = (
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
)


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    """Conexão da requisição atual, aberta sob demanda e guardada em flask.g."""
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def transaction():
    """Transação atômica (commit ou rollback); chamadas aninhadas reutilizam a externa."""
    db = get_db()
    if g.get("tx_depth", 0):
        g.tx_depth += 1
        try:
            yield db
        finally:
            g.tx_depth -= 1
        return
    g.tx_depth = 1
    try:
        with db:
            yield db
    finally:
        g.tx_depth = 0


def _seed(db):
    if db.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
        return
    db.executemany(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        SEED_PRODUTOS,
    )
    db.executemany(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        [(nome, email, generate_password_hash(senha), tipo) for nome, email, senha, tipo in SEED_USUARIOS],
    )
    logger.info("Banco populado com dados de exemplo")


def _hash_legacy_passwords(db):
    rows = db.execute("SELECT id, senha FROM usuarios").fetchall()
    legacy = [(generate_password_hash(row["senha"]), row["id"])
              for row in rows if row["senha"] and not row["senha"].startswith(HASH_PREFIXES)]
    if legacy:
        db.executemany("UPDATE usuarios SET senha = ? WHERE id = ?", legacy)
        logger.info("Senhas legadas convertidas para hash: %d", len(legacy))


def init_db(app):
    """Registra o ciclo de vida da conexão e prepara schema, seed e migração de senhas."""
    app.teardown_appcontext(close_db)
    db = _connect(app.config["DATABASE_PATH"])
    try:
        with db:
            for statement in SCHEMA:
                db.execute(statement)
            _seed(db)
            _hash_legacy_passwords(db)
    finally:
        db.close()
