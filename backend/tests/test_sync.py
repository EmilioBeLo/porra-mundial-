import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.models import Match, Prediction, User, SystemSetting
from app.services.api_football_service import (
    fetch_and_sync_fixtures,
    sync_match_results,
    parse_datetime
)


def test_parse_datetime():
    dt_z = parse_datetime("2026-06-11T18:00:00Z")
    assert dt_z.year == 2026
    assert dt_z.month == 6
    assert dt_z.day == 11
    assert dt_z.hour == 18
    assert dt_z.tzinfo is None

    dt_offset = parse_datetime("2026-06-11T18:00:00+02:00")
    # 18:00 +02:00 is 16:00 UTC
    assert dt_offset.hour == 16
    assert dt_offset.tzinfo is None


@patch("app.services.api_football_service.requests.get")
def test_fetch_and_sync_fixtures_api_football(mock_get, db_session):
    # Set league to 140 (not 1) to trigger original API-Football path
    setting = db_session.query(SystemSetting).filter(SystemSetting.key == "active_league_id").first()
    setting.value = "140"
    db_session.commit()

    # Mock response data
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": [
            {
                "fixture": {
                    "id": 1001,
                    "date": "2026-06-11T18:00:00+00:00",
                    "status": {"short": "NS"}
                },
                "league": {
                    "round": "Group Stage - Group E"
                },
                "teams": {
                    "home": {"name": "Spain"},
                    "away": {"name": "Germany"}
                },
                "goals": {"home": None, "away": None}
            },
            {
                "fixture": {
                    "id": 1002,
                    "date": "2026-06-12T15:00:00+00:00",
                    "status": {"short": "NS"}
                },
                "league": {
                    "round": "Group Stage - Group E"
                },
                "teams": {
                    "home": {"name": "Japan"},
                    "away": {"name": "Costa Rica"}
                },
                "goals": {"home": None, "away": None}
            },
            {
                "fixture": {
                    "id": 1003,
                    "date": "2026-06-13T20:00:00+00:00",
                    "status": {"short": "NS"}
                },
                "league": {
                    "round": "Group Stage - Group A"
                },
                "teams": {
                    "home": {"name": "Brazil"},
                    "away": {"name": "Argentina"}
                },
                "goals": {"home": None, "away": None}
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    # Sync first time
    result = fetch_and_sync_fixtures(db_session)
    assert result == {"status": "success", "synchronized": 3}

    # Verify matches in DB
    matches = db_session.query(Match).order_by(Match.api_id).all()
    assert len(matches) == 3

    # Spain's group is "Group Stage - Group E"
    # Matches in Group E must have es_partido_doble = True
    assert matches[0].api_id == 1001
    assert matches[0].equipo_local == "Spain"
    assert matches[0].es_partido_doble is True

    assert matches[1].api_id == 1002
    assert matches[1].equipo_local == "Japan"
    assert matches[1].es_partido_doble is True

    # Group A must have es_partido_doble = False
    assert matches[2].api_id == 1003
    assert matches[2].equipo_local == "Brazil"
    assert matches[2].es_partido_doble is False


@patch("app.services.api_football_service.requests.get")
def test_fetch_and_sync_fixtures_worldcup(mock_get, db_session):
    # Keep league_id = 1 (default) to trigger World Cup path

    # First call: teams, Second call: matches
    mock_teams_resp = MagicMock()
    mock_teams_resp.json.return_value = [
        {"id": "1", "name_en": "Spain", "groups": "H"},
        {"id": "2", "name_en": "Germany", "groups": "H"},
        {"id": "3", "name_en": "Brazil", "groups": "A"}
    ]
    mock_teams_resp.raise_for_status = MagicMock()

    mock_matches_resp = MagicMock()
    mock_matches_resp.json.return_value = [
        {
            "id": "1001",
            "home_team_id": "1",
            "away_team_id": "2",
            "home_score": "0",
            "away_score": "0",
            "group": "H",
            "local_date": "06/11/2026 18:00",
            "stadium_id": "1",  # Mexico City (offset -6)
            "finished": "FALSE",
            "type": "group"
        },
        {
            "id": "1002",
            "home_team_id": "3",
            "away_team_id": "2",
            "home_score": "0",
            "away_score": "0",
            "group": "A",
            "local_date": "06/12/2026 15:00",
            "stadium_id": "4",  # Dallas (offset -5)
            "finished": "FALSE",
            "type": "group"
        }
    ]
    mock_matches_resp.raise_for_status = MagicMock()

    mock_get.side_effect = [mock_teams_resp, mock_matches_resp]

    result = fetch_and_sync_fixtures(db_session)
    assert result == {"status": "success", "synchronized": 2}

    matches = db_session.query(Match).order_by(Match.api_id).all()
    assert len(matches) == 2

    assert matches[0].api_id == 1001
    assert matches[0].equipo_local == "Spain"
    # Local: 18:00 - (-6 hours) = 24:00 (which is 06/12 00:00 UTC)
    assert matches[0].fecha_hora == datetime(2026, 6, 12, 0, 0, 0)
    assert matches[0].es_partido_doble is True

    assert matches[1].api_id == 1002
    assert matches[1].equipo_local == "Brazil"
    # Local: 15:00 - (-5 hours) = 20:00 UTC
    assert matches[1].fecha_hora == datetime(2026, 6, 12, 20, 0, 0)
    assert matches[1].es_partido_doble is False


def test_sync_match_results_no_pending_matches(db_session):
    # If no matches with api_id and null real scores, return immediately
    result = sync_match_results(db_session)
    assert result == {"status": "success", "updated": 0}


@patch("app.services.api_football_service.requests.get")
def test_sync_match_results_updates_and_recalculates_api_football(mock_get, db_session):
    # Set league to 140 (not 1) to trigger original API-Football path
    setting = db_session.query(SystemSetting).filter(SystemSetting.key == "active_league_id").first()
    setting.value = "140"
    db_session.commit()

    # Setup: 1 user, 1 match, 1 prediction
    user = User(nombre="Diego", password_hash="dummy_hash")
    db_session.add(user)
    db_session.commit()

    match = Match(
        api_id=2001,
        equipo_local="Spain",
        equipo_visitante="Germany",
        fecha_hora=datetime(2026, 6, 11, 18, 0, 0),
        grupo_o_fase="Group Stage - Group E",
        es_partido_doble=True,
        league_id=140
    )
    db_session.add(match)
    db_session.commit()

    prediction = Prediction(
        user_id=user.id,
        match_id=match.id,
        goles_local_pred=2,
        goles_visitante_pred=1,
        puntos_obtenidos=0
    )
    db_session.add(prediction)
    db_session.commit()

    # Mock response showing the match is finished (FT) with 2-1 result
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": [
            {
                "fixture": {
                    "id": 2001,
                    "status": {"short": "FT"}
                },
                "goals": {"home": 2, "away": 1}
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    # Run sync
    result = sync_match_results(db_session)
    assert result == {"status": "success", "updated_matches_count": 1}

    # Verify match result updated
    db_session.refresh(match)
    assert match.goles_local_real == 2
    assert match.goles_visitante_real == 1

    # Verify prediction points updated (Perfect: 3 base * 2 double multiplier = 6 points)
    db_session.refresh(prediction)
    assert prediction.puntos_obtenidos == 6


@patch("app.services.api_football_service.requests.get")
def test_sync_match_results_updates_and_recalculates_worldcup(mock_get, db_session):
    # Keep league_id = 1 (default) to trigger World Cup path

    # Setup: 1 user, 1 match, 1 prediction
    user = User(nombre="Diego", password_hash="dummy_hash")
    db_session.add(user)
    db_session.commit()

    match = Match(
        api_id=2001,
        equipo_local="Spain",
        equipo_visitante="Germany",
        fecha_hora=datetime(2026, 6, 11, 18, 0, 0),
        grupo_o_fase="Grupo H",
        es_partido_doble=True,
        league_id=1
    )
    db_session.add(match)
    db_session.commit()

    prediction = Prediction(
        user_id=user.id,
        match_id=match.id,
        goles_local_pred=2,
        goles_visitante_pred=1,
        puntos_obtenidos=0
    )
    db_session.add(prediction)
    db_session.commit()

    # Mock response showing the match is finished (TRUE) with 2-1 result
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": "2001",
            "home_team_id": "29",
            "away_team_id": "30",
            "home_score": "2",
            "away_score": "1",
            "group": "H",
            "local_date": "06/11/2026 18:00",
            "finished": "TRUE",
            "type": "group"
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    # Run sync
    result = sync_match_results(db_session)
    assert result == {"status": "success", "updated_matches_count": 1}

    # Verify match result updated
    db_session.refresh(match)
    assert match.goles_local_real == 2
    assert match.goles_visitante_real == 1

    # Verify prediction points updated (Perfect: 3 base * 2 double multiplier = 6 points)
    db_session.refresh(prediction)
    assert prediction.puntos_obtenidos == 6


def test_match_response_serialization():
    from app.schemas import MatchResponse
    from datetime import datetime, timezone
    
    # test naive datetime gets serialized with UTC tzinfo
    naive_dt = datetime(2026, 6, 11, 18, 0, 0)
    match_data = {
        "id": 1,
        "equipo_local": "Spain",
        "equipo_visitante": "Germany",
        "fecha_hora": naive_dt,
        "grupo_o_fase": "Group Stage",
        "es_partido_doble": True,
        "api_id": 1001,
        "league_id": 1
    }
    
    response = MatchResponse(**match_data)
    # Serialize to dict / json
    serialized = response.model_dump()
    assert serialized["fecha_hora"].tzinfo == timezone.utc
    
    json_serialized = response.model_dump_json()
    assert "+00:00" in json_serialized or "Z" in json_serialized
