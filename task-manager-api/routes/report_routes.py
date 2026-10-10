from flask import Blueprint, jsonify

from controllers import report_controller

report_bp = Blueprint('reports', __name__)


@report_bp.get('/reports/summary')
def summary_report():
    return jsonify(report_controller.summary_report()), 200


@report_bp.get('/reports/user/<int:user_id>')
def user_report(user_id):
    return jsonify(report_controller.user_report(user_id)), 200
