import logging

from controllers.validators import is_int, parse_date, parse_int, require_payload
from database import db
from middlewares.errors import NotFoundError, ValidationError
from models.category import Category
from models.common import completion_rate, utcnow
from models.task import (
    DATE_FORMAT, DEFAULT_PRIORITY, DEFAULT_STATUS, MAX_PRIORITY, MAX_TITLE_LENGTH, MIN_PRIORITY,
    MIN_TITLE_LENGTH, VALID_STATUSES, Task,
)
from models.user import User

logger = logging.getLogger(__name__)


def get_task_or_404(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    return task


def _check_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')


def _check_status(status):
    if status not in VALID_STATUSES:
        raise ValidationError('Status inválido')


def _check_priority(priority):
    if not is_int(priority) or not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise ValidationError('Prioridade deve ser entre 1 e 5')


def _check_references(user_id, category_id):
    for field, value in (('user_id', user_id), ('category_id', category_id)):
        if value and not (is_int(value) or isinstance(value, str)):
            raise ValidationError(f'{field} inválido')
    if user_id and not db.session.get(User, user_id):
        raise NotFoundError('Usuário não encontrado')
    if category_id and not db.session.get(Category, category_id):
        raise NotFoundError('Categoria não encontrada')


def _check_tags(tags):
    if tags is not None and not isinstance(tags, (str, list)):
        raise ValidationError('Tags inválidas')
    if isinstance(tags, list) and not all(isinstance(tag, str) for tag in tags):
        raise ValidationError('Tags inválidas')


def list_tasks():
    result = []
    for task in Task.list_all(with_relations=True):
        result.append({
            **task.to_dict_with_overdue(),
            'user_name': task.user.name if task.user else None,
            'category_name': task.category.name if task.category else None,
        })
    return result


def get_task(task_id):
    return get_task_or_404(task_id).to_dict_with_overdue()


def create_task(data):
    data = require_payload(data)
    title = data.get('title')
    if not title:
        raise ValidationError('Título é obrigatório')
    _check_title(title)

    status = data.get('status', DEFAULT_STATUS)
    priority = data.get('priority', DEFAULT_PRIORITY)
    user_id = data.get('user_id')
    category_id = data.get('category_id')
    _check_status(status)
    _check_priority(priority)
    _check_references(user_id, category_id)

    task = Task(
        title=title,
        description=data.get('description', ''),
        status=status,
        priority=priority,
        user_id=user_id,
        category_id=category_id,
    )
    if data.get('due_date'):
        task.due_date = parse_date(data['due_date'], DATE_FORMAT, 'Formato de data inválido. Use YYYY-MM-DD')
    if data.get('tags'):
        _check_tags(data['tags'])
        task.set_tags(data['tags'])

    db.session.add(task)
    db.session.commit()
    logger.info('Task criada id=%s', task.id)
    return task.to_dict()


def update_task(task_id, data):
    task = get_task_or_404(task_id)
    data = require_payload(data)

    if 'title' in data:
        _check_title(data['title'])
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        _check_status(data['status'])
        task.status = data['status']
    if 'priority' in data:
        _check_priority(data['priority'])
        task.priority = data['priority']
    if 'user_id' in data:
        _check_references(data['user_id'], None)
        task.user_id = data['user_id']
    if 'category_id' in data:
        _check_references(None, data['category_id'])
        task.category_id = data['category_id']
    if 'due_date' in data:
        task.due_date = parse_date(data['due_date'], DATE_FORMAT, 'Formato de data inválido') if data['due_date'] else None
    if 'tags' in data:
        _check_tags(data['tags'])
        task.set_tags(data['tags'])

    task.updated_at = utcnow()
    db.session.commit()
    logger.info('Task atualizada id=%s', task.id)
    return task.to_dict()


def delete_task(task_id):
    task = get_task_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    logger.info('Task deletada id=%s', task_id)
    return {'message': 'Task deletada com sucesso'}


def search_tasks(params):
    priority = params.get('priority')
    user_id = params.get('user_id')
    tasks = Task.search(
        text=params.get('q'),
        status=params.get('status'),
        priority=parse_int(priority, 'Prioridade inválida') if priority else None,
        user_id=parse_int(user_id, 'user_id inválido') if user_id else None,
    )
    return [task.to_dict() for task in tasks]


def task_stats():
    by_status = Task.count_by_status()
    total = Task.count()
    return {
        'total': total,
        **by_status,
        'overdue': Task.count(Task.overdue_filter(utcnow())),
        'completion_rate': completion_rate(by_status['done'], total),
    }
