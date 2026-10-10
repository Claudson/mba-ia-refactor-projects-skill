from datetime import datetime, timezone


def utcnow():
    """Agora em UTC, sem tzinfo — mesmo formato dos valores já gravados no banco."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def completion_rate(done, total):
    return round((done / total) * 100, 2) if total > 0 else 0
