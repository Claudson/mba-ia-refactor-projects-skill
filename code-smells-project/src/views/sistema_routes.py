from flask import Blueprint, current_app, jsonify

from src.controllers import sistema_controller

sistema_bp = Blueprint("sistema", __name__)


@sistema_bp.get("/")
def index():
    return jsonify(sistema_controller.index(current_app.config["VERSION"]))


@sistema_bp.get("/health")
def health_check():
    return jsonify(sistema_controller.health(current_app.config["VERSION"])), 200
