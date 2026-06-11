"""Tests for the prediction validation service."""

from datetime import datetime, timedelta, timezone

from app.models import Match
from app.services.validation_service import can_predict


def _make_match(fecha_hora: datetime) -> Match:
    m = Match()
    m.fecha_hora = fecha_hora
    return m


class TestPredictionValidation:
    def test_can_predict_before_kickoff(self):
        # Match starts in 1 hour
        kickoff = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        match = _make_match(fecha_hora=kickoff)
        assert can_predict(match) is True

    def test_cannot_predict_after_kickoff(self):
        # Match started 1 hour ago
        kickoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        match = _make_match(fecha_hora=kickoff)
        assert can_predict(match) is False

    def test_cannot_predict_exactly_at_kickoff(self):
        # Match starts right now
        kickoff = datetime.now(timezone.utc).replace(tzinfo=None)
        match = _make_match(fecha_hora=kickoff)
        # kickoff time is equal to now, so not <, hence should return False
        assert can_predict(match) is False
