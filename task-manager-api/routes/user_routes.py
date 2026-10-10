from flask import Blueprint, jsonify, request

from controllers import user_controller
from middlewares.auth import is_admin_request, require_admin

user_bp = Blueprint('users', __name__)


@user_bp.get('/users')
def get_users():
    return jsonify(user_controller.list_users()), 200


@user_bp.get('/users/<int:user_id>')
def get_user(user_id):
    return jsonify(user_controller.get_user(user_id)), 200


@user_bp.post('/users')
def create_user():
    return jsonify(user_controller.create_user(request.get_json(silent=True), is_admin=is_admin_request())), 201


@user_bp.put('/users/<int:user_id>')
def update_user(user_id):
    data = request.get_json(silent=True)
    return jsonify(user_controller.update_user(user_id, data, is_admin=is_admin_request())), 200


@user_bp.delete('/users/<int:user_id>')
@require_admin
def delete_user(user_id):
    return jsonify(user_controller.delete_user(user_id)), 200


@user_bp.get('/users/<int:user_id>/tasks')
def get_user_tasks(user_id):
    return jsonify(user_controller.list_user_tasks(user_id)), 200


@user_bp.post('/login')
def login():
    return jsonify(user_controller.login(request.get_json(silent=True))), 200
