"""Validation service — deadline checks for predictions."""

from datetime import datetime, timedelta, timezone

from app.models import Match


def can_predict(match: Match) -> bool:
    """
    Check if predictions are still allowed for this match.

    Deadline: 23:59:59 UTC of the day BEFORE match.fecha_hora.
    """
    deadline = match.fecha_hora.replace(
        hour=23, minute=59, second=59, microsecond=0
    ) - timedelta(days=1)

    return datetime.now(timezone.utc).replace(tzinfo=None) < deadline
