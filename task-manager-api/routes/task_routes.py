from flask import Blueprint, jsonify, request

from controllers import task_controller
from middlewares.auth import require_admin

task_bp = Blueprint('tasks', __name__)


@task_bp.get('/tasks')
def get_tasks():
    return jsonify(task_controller.list_tasks()), 200


@task_bp.get('/tasks/<int:task_id>')
def get_task(task_id):
    return jsonify(task_controller.get_task(task_id)), 200


@task_bp.post('/tasks')
def create_task():
    return jsonify(task_controller.create_task(request.get_json(silent=True))), 201


@task_bp.put('/tasks/<int:task_id>')
def update_task(task_id):
    return jsonify(task_controller.update_task(task_id, request.get_json(silent=True))), 200


@task_bp.delete('/tasks/<int:task_id>')
@require_admin
def delete_task(task_id):
    return jsonify(task_controller.delete_task(task_id)), 200


@task_bp.get('/tasks/search')
def search_tasks():
    return jsonify(task_controller.search_tasks(request.args)), 200


@task_bp.get('/tasks/stats')
def task_stats():
    return jsonify(task_controller.task_stats()), 200
