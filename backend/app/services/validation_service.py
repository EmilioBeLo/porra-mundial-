from datetime import datetime, timezone

from app.models import Match


def can_predict(match: Match) -> bool:
    """
    Check if predictions are still allowed for this match.

    Deadline: Allow predictions until the match kickoff time (match.fecha_hora in UTC).
    """
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    return now_utc < match.fecha_hora

