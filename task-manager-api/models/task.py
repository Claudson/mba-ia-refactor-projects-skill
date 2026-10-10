from datetime import timedelta

from sqlalchemy import case, func

from database import db
from models.common import utcnow

VALID_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
CLOSED_STATUSES = ('done', 'cancelled')
DEFAULT_STATUS = 'pending'
MIN_PRIORITY, MAX_PRIORITY = 1, 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2  # prioridades 1 e 2 contam como "alta"
PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}
MIN_TITLE_LENGTH, MAX_TITLE_LENGTH = 3, 200
DATE_FORMAT = '%Y-%m-%d'
RECENT_ACTIVITY_DAYS = 7


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=DEFAULT_STATUS)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    # --- regras de domínio -------------------------------------------------

    def is_overdue(self, now=None):
        return bool(self.due_date and self.due_date < (now or utcnow()) and self.status not in CLOSED_STATUSES)

    def set_tags(self, tags):
        self.tags = ','.join(tags) if isinstance(tags, list) else tags

    # --- serialização ------------------------------------------------------

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }

    def to_dict_with_overdue(self):
        return {**self.to_dict(), 'overdue': self.is_overdue()}

    def to_summary_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': str(self.created_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'overdue': self.is_overdue(),
        }

    # --- consultas ---------------------------------------------------------

    @classmethod
    def list_all(cls, with_relations=False):
        query = db.select(cls)
        if with_relations:
            query = query.options(db.joinedload(cls.user), db.joinedload(cls.category))
        return db.session.execute(query.order_by(cls.id)).scalars().unique().all()

    @classmethod
    def list_by_user(cls, user_id):
        return db.session.execute(db.select(cls).where(cls.user_id == user_id).order_by(cls.id)).scalars().all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        query = db.select(cls)
        if text:
            query = query.where(db.or_(cls.title.like(f'%{text}%'), cls.description.like(f'%{text}%')))
        if status:
            query = query.where(cls.status == status)
        if priority is not None:
            query = query.where(cls.priority == priority)
        if user_id is not None:
            query = query.where(cls.user_id == user_id)
        return db.session.execute(query.order_by(cls.id)).scalars().all()

    @classmethod
    def overdue_filter(cls, now):
        return db.and_(cls.due_date.is_not(None), cls.due_date < now, cls.status.not_in(CLOSED_STATUSES))

    @classmethod
    def list_overdue(cls, now):
        return db.session.execute(db.select(cls).where(cls.overdue_filter(now)).order_by(cls.id)).scalars().all()

    @classmethod
    def count(cls, *conditions):
        return db.session.execute(db.select(func.count(cls.id)).where(*conditions)).scalar_one()

    @classmethod
    def count_by(cls, column):
        rows = db.session.execute(db.select(column, func.count(cls.id)).group_by(column)).all()
        return {key: total for key, total in rows}

    @classmethod
    def count_by_status(cls):
        counts = cls.count_by(cls.status)
        return {status: counts.get(status, 0) for status in VALID_STATUSES}

    @classmethod
    def count_by_priority(cls):
        counts = cls.count_by(cls.priority)
        return {label: counts.get(priority, 0) for priority, label in PRIORITY_LABELS.items()}

    @classmethod
    def count_by_user(cls):
        return cls.count_by(cls.user_id)

    @classmethod
    def count_by_category(cls):
        return cls.count_by(cls.category_id)

    @classmethod
    def totals_by_user(cls):
        """{user_id: (total, concluídas)} numa única query agregada."""
        done = func.sum(case((cls.status == 'done', 1), else_=0))
        rows = db.session.execute(db.select(cls.user_id, func.count(cls.id), done).group_by(cls.user_id)).all()
        return {user_id: (total, completed or 0) for user_id, total, completed in rows}

    @classmethod
    def recent_activity(cls, now):
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
        return {
            'tasks_created_last_7_days': cls.count(cls.created_at >= since),
            'tasks_completed_last_7_days': cls.count(cls.status == 'done', cls.updated_at >= since),
        }

    @classmethod
    def delete_by_user(cls, user_id):
        db.session.execute(db.delete(cls).where(cls.user_id == user_id))

    @classmethod
    def detach_category(cls, category_id):
        db.session.execute(db.update(cls).where(cls.category_id == category_id).values(category_id=None))
