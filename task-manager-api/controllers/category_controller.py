import logging

from controllers.validators import require_payload
from database import db
from middlewares.errors import NotFoundError, ValidationError
from models.category import DEFAULT_COLOR, Category
from models.task import Task

logger = logging.getLogger(__name__)


def get_category_or_404(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        raise NotFoundError('Categoria não encontrada')
    return category


def _check_color(color):
    if not Category.is_valid_color(color):
        raise ValidationError('Cor inválida. Use o formato #RRGGBB')


def list_categories():
    task_counts = Task.count_by_category()
    return [{**category.to_dict(), 'task_count': task_counts.get(category.id, 0)}
            for category in db.session.execute(db.select(Category).order_by(Category.id)).scalars()]


def create_category(data):
    data = require_payload(data)
    if not data.get('name'):
        raise ValidationError('Nome é obrigatório')
    color = data.get('color', DEFAULT_COLOR)
    _check_color(color)

    category = Category(name=data['name'], description=data.get('description', ''), color=color)
    db.session.add(category)
    db.session.commit()
    logger.info('Categoria criada id=%s', category.id)
    return category.to_dict()


def update_category(category_id, data):
    category = get_category_or_404(category_id)
    data = require_payload(data)
    if 'name' in data:
        if not data['name']:
            raise ValidationError('Nome é obrigatório')
        category.name = data['name']
    if 'description' in data:
        category.description = data['description']
    if 'color' in data:
        _check_color(data['color'])
        category.color = data['color']
    db.session.commit()
    return category.to_dict()


def delete_category(category_id):
    category = get_category_or_404(category_id)
    Task.detach_category(category_id)  # mesma transação: tasks ficam sem categoria, nunca órfãs
    db.session.delete(category)
    db.session.commit()
    logger.info('Categoria deletada id=%s', category_id)
    return {'message': 'Categoria deletada'}
