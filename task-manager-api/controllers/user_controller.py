import logging

from flask import current_app

from controllers.validators import require_payload
from database import db
from middlewares.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from models.task import Task
from models.user import DEFAULT_ROLE, MIN_PASSWORD_LENGTH, VALID_ROLES, User
from services.auth_service import issue_token

logger = logging.getLogger(__name__)


def get_user_or_404(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')
    return user


def _check_email(email, current_user_id=None):
    if not User.is_valid_email(email):
        raise ValidationError('Email inválido')
    existing = User.find_by_email(email)
    if existing and existing.id != current_user_id:
        raise ConflictError('Email já cadastrado')


def _check_password(password, message):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(message)


def _check_role(role, is_admin):
    if role not in VALID_ROLES:
        raise ValidationError('Role inválido')
    if role != DEFAULT_ROLE and not is_admin:
        raise ForbiddenError('Somente administradores podem atribuir este role')


def list_users():
    task_counts = Task.count_by_user()
    return [{**user.to_dict(), 'task_count': task_counts.get(user.id, 0)}
            for user in db.session.execute(db.select(User).order_by(User.id)).scalars()]


def get_user(user_id):
    user = get_user_or_404(user_id)
    return {**user.to_dict(), 'tasks': [task.to_dict() for task in Task.list_by_user(user_id)]}


def create_user(data, is_admin=False):
    data = require_payload(data)
    name, email, password = data.get('name'), data.get('email'), data.get('password')
    role = data.get('role', DEFAULT_ROLE)

    if not name:
        raise ValidationError('Nome é obrigatório')
    if not email:
        raise ValidationError('Email é obrigatório')
    if not password:
        raise ValidationError('Senha é obrigatória')
    if not User.is_valid_email(email):
        raise ValidationError('Email inválido')
    _check_password(password, 'Senha deve ter no mínimo 4 caracteres')
    _check_email(email)
    _check_role(role, is_admin)

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    logger.info('Usuário criado id=%s', user.id)
    return user.to_dict()


def update_user(user_id, data, is_admin=False):
    user = get_user_or_404(user_id)
    data = require_payload(data)

    if 'name' in data:
        if not data['name'] or not isinstance(data['name'], str):
            raise ValidationError('Nome é obrigatório')
        user.name = data['name']
    if 'email' in data:
        _check_email(data['email'], current_user_id=user_id)
        user.email = data['email']
    if 'password' in data:
        _check_password(data['password'], 'Senha muito curta')
        user.set_password(data['password'])
    if 'role' in data:
        if data['role'] not in VALID_ROLES:
            raise ValidationError('Role inválido')
        if data['role'] != user.role and not is_admin:
            raise ForbiddenError('Somente administradores podem alterar o role')
        user.role = data['role']
    if 'active' in data:
        if not isinstance(data['active'], bool):
            raise ValidationError('Campo active deve ser booleano')
        user.active = data['active']

    db.session.commit()
    return user.to_dict()


def delete_user(user_id):
    user = get_user_or_404(user_id)
    Task.delete_by_user(user_id)
    db.session.delete(user)
    db.session.commit()
    logger.info('Usuário deletado id=%s', user_id)
    return {'message': 'Usuário deletado com sucesso'}


def list_user_tasks(user_id):
    get_user_or_404(user_id)
    return [task.to_summary_dict() for task in Task.list_by_user(user_id)]


def login(data):
    data = require_payload(data)
    email, password = data.get('email'), data.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')

    user = User.find_by_email(email) if isinstance(email, str) else None
    if not user or not isinstance(password, str) or not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')
    if not user.active:
        raise ForbiddenError('Usuário inativo')

    db.session.commit()  # persiste a migração de hash legado, se ocorreu
    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': issue_token(user, current_app.config['SECRET_KEY']),
    }
