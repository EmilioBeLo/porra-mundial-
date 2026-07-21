"""Scoring service — calculates points for predictions."""

from typing import Tuple
from sqlalchemy.orm import Session

from app.models import Match, Prediction, User, SystemSetting, TournamentPrediction


def recalculate_match(db: Session, match: Match) -> None:
    """
    Recalculate points for all predictions of this match and update
    affected users' points and perfect counts.
    """
    predictions = db.query(Prediction).filter(Prediction.match_id == match.id).all()

    affected_user_ids = set()

    for prediction in predictions:
        points, _is_perfect = calculate_points(prediction, match)
        prediction.puntos_obtenidos = points
        affected_user_ids.add(prediction.user_id)

    # Also include users whose assigned underdog team is playing in this match
    underdog_users = db.query(User).filter(
        (User.assigned_team == match.equipo_local) | (User.assigned_team == match.equipo_visitante)
    ).all()
    for uu in underdog_users:
        affected_user_ids.add(uu.id)

    # Flush pending changes (like match scores) so calculate_assigned_team_points can query them
    db.flush()

    for user_id in affected_user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            continue

        user_predictions = db.query(Prediction).filter(Prediction.user_id == user_id).all()

        total_points = 0
        perfect_count = 0

        for pred in user_predictions:
            total_points += pred.puntos_obtenidos

            pred_match = db.query(Match).filter(Match.id == pred.match_id).first()
            if pred_match and pred_match.goles_local_real is not None:
                _pts, is_perfect = calculate_points(pred, pred_match)
                if is_perfect:
                    perfect_count += 1

        user.puntos_totales = total_points + calculate_assigned_team_points(db, user)
        active_league_id = SystemSetting.get_int(db, "active_league_id", 1)
        if active_league_id == 1:
            user.puntos_totales += calculate_tournament_points(db, user.id)
        user.aciertos_perfectos = perfect_count


def calculate_assigned_team_points(db: Session, user: User) -> int:
    """Calculate minigame points for the user's assigned team in World Cup (league_id == 1)."""
    active_league_id = SystemSetting.get_int(db, "active_league_id", 1)
    if not user.assigned_team or active_league_id != 1:
        return 0

    matches = (
        db.query(Match)
        .filter(
            Match.league_id == 1,
            Match.goles_local_real.isnot(None),
            Match.goles_visitante_real.isnot(None),
        )
        .all()
    )

    points = 0
    for match in matches:
        if user.assigned_team == match.equipo_local:
            points += match.goles_local_real + (match.goles_visitante_real // 3)
        elif user.assigned_team == match.equipo_visitante:
            points += match.goles_visitante_real + (match.goles_local_real // 3)
    return points


def calculate_tournament_points_breakdown(db: Session, user_id: int) -> dict:
    """Calculate tournament prediction points breakdown for a user."""
    prediction = db.query(TournamentPrediction).filter(TournamentPrediction.user_id == user_id).first()
    if not prediction:
        return {"campeon": 0, "subcampeon": 0, "goleador": 0, "asistente": 0, "total": 0}

    real_campeon = SystemSetting.get_str(db, "real_campeon", "")
    real_subcampeon = SystemSetting.get_str(db, "real_subcampeon", "")
    real_maximo_goleador = SystemSetting.get_str(db, "real_maximo_goleador", "")
    real_maximo_asistente = SystemSetting.get_str(db, "real_maximo_asistente", "")

    def _match(pred: str, real: str) -> bool:
        if not real or not pred:
            return False
        return pred.strip().lower() == real.strip().lower()

    pts_campeon = 10 if _match(prediction.campeon, real_campeon) else 0
    pts_subcampeon = 5 if _match(prediction.subcampeon, real_subcampeon) else 0
    pts_goleador = 5 if _match(prediction.maximo_goleador, real_maximo_goleador) else 0
    pts_asistente = 5 if _match(prediction.maximo_asistente, real_maximo_asistente) else 0

    total = pts_campeon + pts_subcampeon + pts_goleador + pts_asistente

    return {
        "campeon": pts_campeon,
        "subcampeon": pts_subcampeon,
        "goleador": pts_goleador,
        "asistente": pts_asistente,
        "total": total,
    }


def calculate_tournament_points(db: Session, user_id: int) -> int:
    """Calculate total tournament prediction points for a user."""
    return calculate_tournament_points_breakdown(db, user_id)["total"]


def calculate_points(prediction: Prediction, match: Match) -> Tuple[int, bool]:
    """
    Calculate points for a single prediction against the actual result.

    Returns:
        Tuple of (total_points, is_perfect).
        is_perfect is True when the prediction exactly matches the result
        (before any multiplier).
    """
    if match.goles_local_real is None or match.goles_visitante_real is None:
        return 0, False

    base_points = 0
    is_perfect = False

    # Perfect score: exact match
    if (
        prediction.goles_local_pred == match.goles_local_real
        and prediction.goles_visitante_pred == match.goles_visitante_real
    ):
        base_points = 3
        is_perfect = True

    # Tendency: correct winner or correct draw
    elif _same_tendency(prediction, match):
        base_points = 1

    # Apply x2 multiplier for double-point matches
    multiplier = 2 if match.es_partido_doble else 1

    return base_points * multiplier, is_perfect


def _same_tendency(prediction: Prediction, match: Match) -> bool:
    """Check if the prediction has the same tendency (win/draw/loss) as the real result."""
    pred_diff = prediction.goles_local_pred - prediction.goles_visitante_pred
    real_diff = match.goles_local_real - match.goles_visitante_real  # type: ignore[operator]

    return (
        (pred_diff > 0 and real_diff > 0)
        or (pred_diff == 0 and real_diff == 0)
        or (pred_diff < 0 and real_diff < 0)
    )


def recalculate_all_users_points(db: Session, league_id: int) -> None:
    """Recalculate points and perfect count for all users for a specific league."""
    users = db.query(User).all()
    for user in users:
        preds = (
            db.query(Prediction)
            .join(Match)
            .filter(Prediction.user_id == user.id, Match.league_id == league_id)
            .all()
        )
        # Update prediction points before summing to apply rules retroactively (e.g. double points)
        for p in preds:
            p.puntos_obtenidos, _ = calculate_points(p, p.match)
            
        puntos_totales = sum(p.puntos_obtenidos for p in preds)

        perfectos = 0
        for p in preds:
            match = p.match
            if (
                match.goles_local_real is not None
                and match.goles_visitante_real is not None
                and p.goles_local_pred == match.goles_local_real
                and p.goles_visitante_pred == match.goles_visitante_real
            ):
                perfectos += 1

        user.puntos_totales = puntos_totales
        if league_id == 1:
            user.puntos_totales += calculate_assigned_team_points(db, user)
            user.puntos_totales += calculate_tournament_points(db, user.id)
        user.aciertos_perfectos = perfectos
    db.commit()

