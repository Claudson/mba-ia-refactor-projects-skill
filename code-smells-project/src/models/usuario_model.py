from werkzeug.security import check_password_hash, generate_password_hash

from src.database import get_db, transaction

TIPO_PADRAO = "cliente"

CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")
CAMPOS_SESSAO = ("id", "nome", "email", "tipo")


def to_public_dict(row):
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS}


def listar():
    rows = get_db().execute("SELECT * FROM usuarios").fetchall()
    return [to_public_dict(row) for row in rows]


def buscar_por_id(usuario_id):
    row = get_db().execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return to_public_dict(row) if row else None


def existe(usuario_id):
    return get_db().execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)).fetchone() is not None


def autenticar(email, senha):
    row = get_db().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if row and row["senha"] and check_password_hash(row["senha"], senha):
        return {campo: row[campo] for campo in CAMPOS_SESSAO}
    return None


def criar(nome, email, senha, tipo=TIPO_PADRAO):
    with transaction() as db:
        cursor = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
    return cursor.lastrowid


def contar():
    return get_db().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]


def apagar_todos():
    with transaction() as db:
        db.execute("DELETE FROM usuarios")
