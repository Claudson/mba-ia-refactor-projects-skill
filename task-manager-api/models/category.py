import re

from database import db
from models.common import utcnow

DEFAULT_COLOR = '#000000'
COLOR_PATTERN = re.compile(r'^#[0-9a-fA-F]{6}$')


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utcnow)

    @staticmethod
    def is_valid_color(color):
        return isinstance(color, str) and bool(COLOR_PATTERN.match(color))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'created_at': str(self.created_at),
        }
