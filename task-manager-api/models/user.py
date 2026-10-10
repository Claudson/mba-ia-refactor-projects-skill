import hashlib
import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models.common import utcnow

VALID_ROLES = ('user', 'admin', 'manager')
DEFAULT_ROLE = 'user'
MIN_PASSWORD_LENGTH = 4
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')
_LEGACY_MD5_PATTERN = re.compile(r'^[0-9a-f]{32}$')


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        """Serialização pública — nunca inclui o hash da senha."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    @staticmethod
    def is_valid_email(email):
        return isinstance(email, str) and bool(EMAIL_PATTERN.match(email))

    @classmethod
    def find_by_email(cls, email):
        return db.session.execute(db.select(cls).where(cls.email == email)).scalar_one_or_none()

    def set_password(self, raw):
        self.password = generate_password_hash(raw)

    def check_password(self, raw):
        """Valida a senha; hashes MD5 legados são aceitos uma vez e migrados para o hash forte."""
        if _LEGACY_MD5_PATTERN.match(self.password or ''):
            legacy = hashlib.md5(raw.encode()).hexdigest()  # somente para migrar hashes antigos
            if not hmac.compare_digest(legacy, self.password):
                return False
            self.set_password(raw)
            return True
        return check_password_hash(self.password, raw)
