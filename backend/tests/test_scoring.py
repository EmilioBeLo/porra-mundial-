"""Tests for the scoring service — the most critical business logic."""

import pytest

from app.models import Match, Prediction
from app.services.scoring_service import calculate_points, _same_tendency


# ──────────────────────────────────────────────
# Helpers to create model instances without DB
# ──────────────────────────────────────────────

def _make_match(
    local_real: int | None = None,
    visit_real: int | None = None,
    doble: bool = False,
) -> Match:
    m = Match()
    m.goles_local_real = local_real
    m.goles_visitante_real = visit_real
    m.es_partido_doble = doble
    return m


def _make_prediction(local_pred: int, visit_pred: int) -> Prediction:
    p = Prediction()
    p.goles_local_pred = local_pred
    p.goles_visitante_pred = visit_pred
    return p


# ──────────────────────────────────────────────
# Tests: Match not played yet
# ──────────────────────────────────────────────

class TestMatchNotPlayed:
    def test_returns_zero_when_no_result(self):
        match = _make_match(local_real=None, visit_real=None)
        pred = _make_prediction(2, 1)
        points, is_perfect = calculate_points(pred, match)
        assert points == 0
        assert is_perfect is False

    def test_returns_zero_when_partial_result(self):
        match = _make_match(local_real=2, visit_real=None)
        pred = _make_prediction(2, 1)
        points, is_perfect = calculate_points(pred, match)
        assert points == 0
        assert is_perfect is False


# ──────────────────────────────────────────────
# Tests: Perfect score (3 points base)
# ──────────────────────────────────────────────

class TestPerfectScore:
    def test_exact_match_home_win(self):
        match = _make_match(local_real=2, visit_real=0)
        pred = _make_prediction(2, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 3
        assert is_perfect is True

    def test_exact_match_draw(self):
        match = _make_match(local_real=1, visit_real=1)
        pred = _make_prediction(1, 1)
        points, is_perfect = calculate_points(pred, match)
        assert points == 3
        assert is_perfect is True

    def test_exact_match_away_win(self):
        match = _make_match(local_real=0, visit_real=3)
        pred = _make_prediction(0, 3)
        points, is_perfect = calculate_points(pred, match)
        assert points == 3
        assert is_perfect is True

    def test_exact_match_zero_zero(self):
        match = _make_match(local_real=0, visit_real=0)
        pred = _make_prediction(0, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 3
        assert is_perfect is True


# ──────────────────────────────────────────────
# Tests: Correct tendency (1 point base)
# ──────────────────────────────────────────────

class TestCorrectTendency:
    def test_correct_home_win_wrong_score(self):
        match = _make_match(local_real=3, visit_real=1)
        pred = _make_prediction(2, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 1
        assert is_perfect is False

    def test_correct_draw_wrong_score(self):
        match = _make_match(local_real=2, visit_real=2)
        pred = _make_prediction(0, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 1
        assert is_perfect is False

    def test_correct_away_win_wrong_score(self):
        match = _make_match(local_real=1, visit_real=3)
        pred = _make_prediction(0, 2)
        points, is_perfect = calculate_points(pred, match)
        assert points == 1
        assert is_perfect is False


# ──────────────────────────────────────────────
# Tests: Wrong prediction (0 points)
# ──────────────────────────────────────────────

class TestWrongPrediction:
    def test_predicted_home_win_but_draw(self):
        match = _make_match(local_real=1, visit_real=1)
        pred = _make_prediction(2, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 0
        assert is_perfect is False

    def test_predicted_home_win_but_away_win(self):
        match = _make_match(local_real=0, visit_real=2)
        pred = _make_prediction(3, 1)
        points, is_perfect = calculate_points(pred, match)
        assert points == 0
        assert is_perfect is False

    def test_predicted_draw_but_home_win(self):
        match = _make_match(local_real=2, visit_real=0)
        pred = _make_prediction(1, 1)
        points, is_perfect = calculate_points(pred, match)
        assert points == 0
        assert is_perfect is False

    def test_predicted_away_win_but_home_win(self):
        match = _make_match(local_real=3, visit_real=0)
        pred = _make_prediction(0, 1)
        points, is_perfect = calculate_points(pred, match)
        assert points == 0
        assert is_perfect is False


# ──────────────────────────────────────────────
# Tests: Double points multiplier (es_partido_doble)
# ──────────────────────────────────────────────

class TestDoubleMultiplier:
    def test_perfect_score_doubled(self):
        match = _make_match(local_real=1, visit_real=0, doble=True)
        pred = _make_prediction(1, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 6  # 3 * 2
        assert is_perfect is True

    def test_tendency_doubled(self):
        match = _make_match(local_real=2, visit_real=0, doble=True)
        pred = _make_prediction(1, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 2  # 1 * 2
        assert is_perfect is False

    def test_wrong_not_doubled(self):
        match = _make_match(local_real=0, visit_real=1, doble=True)
        pred = _make_prediction(2, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 0  # 0 * 2
        assert is_perfect is False

    def test_normal_match_no_multiplier(self):
        match = _make_match(local_real=1, visit_real=0, doble=False)
        pred = _make_prediction(1, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 3  # 3 * 1
        assert is_perfect is True


# ──────────────────────────────────────────────
# Tests: _same_tendency helper
# ──────────────────────────────────────────────

class TestSameTendency:
    def test_both_home_wins(self):
        pred = _make_prediction(3, 1)
        match = _make_match(local_real=2, visit_real=0)
        assert _same_tendency(pred, match) is True

    def test_both_draws(self):
        pred = _make_prediction(0, 0)
        match = _make_match(local_real=3, visit_real=3)
        assert _same_tendency(pred, match) is True

    def test_both_away_wins(self):
        pred = _make_prediction(0, 2)
        match = _make_match(local_real=1, visit_real=4)
        assert _same_tendency(pred, match) is True

    def test_different_tendencies(self):
        pred = _make_prediction(2, 0)
        match = _make_match(local_real=0, visit_real=1)
        assert _same_tendency(pred, match) is False

    def test_draw_vs_home_win(self):
        pred = _make_prediction(1, 1)
        match = _make_match(local_real=2, visit_real=1)
        assert _same_tendency(pred, match) is False


# ──────────────────────────────────────────────
# Tests: Edge cases
# ──────────────────────────────────────────────

class TestEdgeCases:
    def test_high_scoring_perfect(self):
        match = _make_match(local_real=7, visit_real=5)
        pred = _make_prediction(7, 5)
        points, is_perfect = calculate_points(pred, match)
        assert points == 3
        assert is_perfect is True

    def test_high_scoring_tendency_only(self):
        match = _make_match(local_real=7, visit_real=5)
        pred = _make_prediction(1, 0)
        points, is_perfect = calculate_points(pred, match)
        assert points == 1
        assert is_perfect is False

    def test_perfect_double_high_score(self):
        match = _make_match(local_real=4, visit_real=4, doble=True)
        pred = _make_prediction(4, 4)
        points, is_perfect = calculate_points(pred, match)
        assert points == 6  # 3 * 2
        assert is_perfect is True
