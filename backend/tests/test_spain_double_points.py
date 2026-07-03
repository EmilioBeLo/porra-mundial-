from datetime import datetime, timezone
import pytest
from app.models import Match, User, Prediction
from app.services.scoring_service import recalculate_all_users_points

def test_spain_match_auto_double_insert(db_session):
    # Insert a new match with local "Spain" and visitor "France"
    match = Match(
        equipo_local="Spain",
        equipo_visitante="France",
        fecha_hora=datetime.now(timezone.utc),
        grupo_o_fase="Fase de Grupos",
        es_partido_doble=False  # Start as False, event listener should toggle it to True
    )
    db_session.add(match)
    db_session.commit()

    # Assert that its es_partido_doble is True
    assert match.es_partido_doble is True

    # Try with "España" as visitor
    match2 = Match(
        equipo_local="Germany",
        equipo_visitante="España",
        fecha_hora=datetime.now(timezone.utc),
        grupo_o_fase="Fase de Grupos",
    )
    db_session.add(match2)
    db_session.commit()
    assert match2.es_partido_doble is True

def test_spain_match_auto_double_update(db_session):
    # Insert a normal match
    match = Match(
        equipo_local="Germany",
        equipo_visitante="France",
        fecha_hora=datetime.now(timezone.utc),
        grupo_o_fase="Fase de Grupos",
        es_partido_doble=False
    )
    db_session.add(match)
    db_session.commit()
    assert match.es_partido_doble is False

    # Update its visitor team to "España"
    match.equipo_visitante = "España"
    db_session.commit()

    # Assert that its es_partido_doble is updated to True
    assert match.es_partido_doble is True

def test_spain_match_double_points_calculation(db_session):
    # Create a match with Spain (which gets marked as double automatically)
    match = Match(
        equipo_local="Spain",
        equipo_visitante="Italy",
        fecha_hora=datetime.now(timezone.utc),
        grupo_o_fase="Fase de Grupos",
    )
    db_session.add(match)
    db_session.commit()
    assert match.es_partido_doble is True

    # Set the real match result (e.g. 2 - 1)
    match.goles_local_real = 2
    match.goles_visitante_real = 1
    db_session.commit()

    # Create a user and a prediction (e.g. 2 - 1, perfect prediction)
    user = User(nombre="TestSpainUser", password_hash="hash", is_admin=False)
    db_session.add(user)
    db_session.commit()

    pred = Prediction(
        user_id=user.id,
        match_id=match.id,
        goles_local_pred=2,
        goles_visitante_pred=1,
        puntos_obtenidos=0
    )
    db_session.add(pred)
    db_session.commit()

    # Run recalculate_all_users_points
    recalculate_all_users_points(db_session, league_id=1)

    # Refresh prediction and user from DB
    db_session.refresh(pred)
    db_session.refresh(user)

    # Assert that the prediction's points obtained are doubled (3 * 2 = 6 points)
    # Also user's total points should be updated to 6
    assert pred.puntos_obtenidos == 6
    assert user.puntos_totales == 6
