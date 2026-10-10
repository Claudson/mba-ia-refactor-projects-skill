from database import db
from middlewares.errors import NotFoundError
from models.category import Category
from models.common import completion_rate, utcnow
from models.task import HIGH_PRIORITY_MAX, VALID_STATUSES, Task
from models.user import User


def summary_report():
    now = utcnow()
    users = db.session.execute(db.select(User).order_by(User.id)).scalars().all()
    totals_by_user = Task.totals_by_user()
    overdue = Task.list_overdue(now)

    user_productivity = []
    for user in users:
        total, completed = totals_by_user.get(user.id, (0, 0))
        user_productivity.append({
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': completion_rate(completed, total),
        })

    return {
        'generated_at': str(now),
        'overview': {
            'total_tasks': Task.count(),
            'total_users': len(users),
            'total_categories': db.session.execute(db.select(db.func.count(Category.id))).scalar_one(),
        },
        'tasks_by_status': Task.count_by_status(),
        'tasks_by_priority': Task.count_by_priority(),
        'overdue': {
            'count': len(overdue),
            'tasks': [{
                'id': task.id,
                'title': task.title,
                'due_date': str(task.due_date),
                'days_overdue': (now - task.due_date).days,
            } for task in overdue],
        },
        'recent_activity': Task.recent_activity(now),
        'user_productivity': user_productivity,
    }


def user_report(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    tasks = Task.list_by_user(user_id)
    now = utcnow()
    by_status = {status: sum(1 for task in tasks if task.status == status) for status in VALID_STATUSES}
    return {
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'statistics': {
            'total_tasks': len(tasks),
            **by_status,
            'overdue': sum(1 for task in tasks if task.is_overdue(now)),
            'high_priority': sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
            'completion_rate': completion_rate(by_status['done'], len(tasks)),
        },
    }
