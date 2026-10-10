"""Acesso a dados e regras da entidade usuario (P-02, P-07, P-08)."""

import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

TIPO_PADRAO = "cliente"

# A coluna `senha` nunca entra na serializacao publica.
CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")
CAMPOS_AUTENTICACAO = ("id", "nome", "email", "tipo")


def serializar(row):
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS}


def _serializar_autenticado(row):
    return {campo: row[campo] for campo in CAMPOS_AUTENTICACAO}


def listar(conn):
    rows = conn.execute(
        "SELECT id, nome, email, tipo, criado_em FROM usuarios"
    ).fetchall()
    return [serializar(row) for row in rows]


def buscar_por_id(conn, usuario_id):
    row = conn.execute(
        "SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    return serializar(row) if row else None


def existe(conn, usuario_id):
    row = conn.execute("SELECT 1 FROM usuarios WHERE id = ? LIMIT 1", (usuario_id,)).fetchone()
    return row is not None


def email_cadastrado(conn, email):
    row = conn.execute("SELECT 1 FROM usuarios WHERE email = ? LIMIT 1", (email,)).fetchone()
    return row is not None


def criar(conn, nome, email, senha, tipo=TIPO_PADRAO):
    """Grava a senha com hash forte; devolve None se o email ja existir."""
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, generate_password_hash(senha), tipo),
            )
    except sqlite3.IntegrityError:
        return None
    return cursor.lastrowid


def autenticar(conn, email, senha):
    """Busca por email e verifica o hash em memoria (nunca compara senha no SQL)."""
    row = conn.execute(
        "SELECT id, nome, email, tipo, senha FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
    if row is None or not check_password_hash(row["senha"], senha):
        return None
    return _serializar_autenticado(row)


def contar(conn):
    return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
