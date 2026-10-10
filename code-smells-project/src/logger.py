"""Configuracao unica de logging (P-14). Substitui os prints da aplicacao."""

import logging
import sys

_FORMATO = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"


def configure(level="INFO"):
    """Configura o root logger uma unica vez, no composition root."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMATO))
        root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
    return root
