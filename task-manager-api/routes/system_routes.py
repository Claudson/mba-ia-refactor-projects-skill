from datetime import datetime

from flask import Blueprint

system_bp = Blueprint('system', __name__)


@system_bp.get('/health')
def health():
    return {'status': 'ok', 'timestamp': str(datetime.now())}


@system_bp.get('/')
def index():
    return {'message': 'Task Manager API', 'version': '1.0'}
