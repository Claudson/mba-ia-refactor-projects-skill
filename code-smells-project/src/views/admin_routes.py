from flask import Blueprint, jsonify

from src.controllers import admin_controller
from src.middlewares.auth import require_admin

admin_bp = Blueprint("admin", __name__)


@admin_bp.post("/admin/reset-db")
@require_admin
def reset_database():
    return jsonify(admin_controller.reset_db()), 200
