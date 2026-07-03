import random
from typing import Set

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Match, Prediction, User, SystemSetting
from app.schemas import MatchCreate, MatchResponse, MatchResultUpdate, RecalculationResult, TournamentResultsUpdate
from app.services.api_football_service import fetch_and_sync_fixtures, sync_match_results
from app.services.scoring_service import (
    calculate_points,
    recalculate_all_users_points,
    recalculate_match,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/matches", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
def create_match(
    body: MatchCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MatchResponse:
    """Create a new match. Requires admin."""
    match = Match(
        equipo_local=body.equipo_local,
        equipo_visitante=body.equipo_visitante,
        fecha_hora=body.fecha_hora,
        grupo_o_fase=body.grupo_o_fase,
        es_partido_doble=body.es_partido_doble,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return MatchResponse.model_validate(match)


KNOCKOUT_MAPPING = {
    73: [(90, "local", "winner")],
    74: [(89, "local", "winner")],
    75: [(90, "visitor", "winner")],
    76: [(89, "visitor", "winner")],
    77: [(91, "local", "winner")],
    78: [(91, "visitor", "winner")],
    79: [(92, "local", "winner")],
    80: [(92, "visitor", "winner")],
    81: [(94, "local", "winner")],
    82: [(94, "visitor", "winner")],
    83: [(93, "local", "winner")],
    84: [(93, "visitor", "winner")],
    85: [(95, "local", "winner")],
    86: [(95, "visitor", "winner")],
    87: [(96, "local", "winner")],
    88: [(96, "visitor", "winner")],
    89: [(97, "local", "winner")],
    90: [(97, "visitor", "winner")],
    91: [(99, "local", "winner")],
    92: [(99, "visitor", "winner")],
    93: [(98, "local", "winner")],
    94: [(98, "visitor", "winner")],
    95: [(100, "local", "winner")],
    96: [(100, "visitor", "winner")],
    97: [(101, "local", "winner")],
    98: [(101, "visitor", "winner")],
    99: [(102, "local", "winner")],
    100: [(102, "visitor", "winner")],
    101: [(104, "local", "winner"), (103, "local", "loser")],
    102: [(104, "visitor", "winner"), (103, "visitor", "loser")],
}


@router.put("/matches/{match_id}/result", response_model=RecalculationResult)
def update_result(
    match_id: int,
    body: MatchResultUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RecalculationResult:
    """
    Update a match result and trigger full recalculation.

    Flow:
    1. Update match with real scores.
    2. Calculate points for ALL predictions of this match.
    3. Recalculate puntos_totales and aciertos_perfectos for each affected user.
    4. Commit everything in a single transaction.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partido no encontrado",
        )

    # Step 1: Update match result
    match.goles_local_real = body.goles_local_real
    match.goles_visitante_real = body.goles_visitante_real

    # Handle knockout progression
    if 73 <= match_id <= 102:
        if body.goles_local_real > body.goles_visitante_real:
            winner = match.equipo_local
            loser = match.equipo_visitante
        elif body.goles_local_real < body.goles_visitante_real:
            winner = match.equipo_visitante
            loser = match.equipo_local
        else:
            if body.penalties_winner is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Los partidos de eliminación directa no pueden terminar en empate sin definir un ganador de penaltis.",
                )
            if body.penalties_winner == 1:
                winner = match.equipo_local
                loser = match.equipo_visitante
            elif body.penalties_winner == 2:
                winner = match.equipo_visitante
                loser = match.equipo_local
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ganador de penaltis inválido.",
                )

        for target_id, slot, rel in KNOCKOUT_MAPPING[match_id]:
            target_match = db.query(Match).filter(Match.id == target_id).first()
            if target_match:
                team_name = winner if rel == "winner" else loser
                if slot == "local":
                    target_match.equipo_local = team_name
                elif slot == "visitor":
                    target_match.equipo_visitante = team_name

    # Step 2: Get all predictions for this match to compute response metrics
    predictions = db.query(Prediction).filter(Prediction.match_id == match_id).all()
    affected_user_ids = {p.user_id for p in predictions}

    # Step 3: Recalculate match predictions and underdog points, then full standings sweep
    recalculate_match(db, match)
    recalculate_all_users_points(db, league_id=1)

    # Step 4: Single commit
    db.commit()

    return RecalculationResult(
        match_id=match_id,
        predictions_updated=len(predictions),
        users_updated=len(affected_user_ids),
    )



@router.post("/recalculate", status_code=status.HTTP_200_OK)
def trigger_recalculation(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    Force a full points and standing recalculation for all users.
    Requires admin.
    """
    recalculate_all_users_points(db, league_id=1)
    return {"status": "success", "message": "Clasificación recalculada por completo"}


@router.post("/sync/matches", status_code=status.HTTP_200_OK)
def sync_matches(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Fetch and sync fixtures from API-Football. Requires admin."""
    return fetch_and_sync_fixtures(db)


@router.post("/sync/results", status_code=status.HTTP_200_OK)
def sync_results(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Fetch and sync match results from API-Football. Requires admin."""
    return sync_match_results(db)


UNDERDOG_TEAMS = [
    "New Zealand",
    "Haiti",
    "Curaçao",
    "Ghana",
    "Cape Verde",
    "Bosnia and Herzegovina",
    "Jordan",
    "Saudi Arabia",
    "South Africa",
    "Iraq",
]


@router.post("/draw-teams", status_code=status.HTTP_200_OK)
def draw_teams(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    Draw/assign one of the worst 10 teams to all active non-admin users.
    Triggers recalculation of all users' points afterwards.
    """
    users = db.query(User).filter(User.is_admin == False).all()
    if not users:
        return {"status": "success", "assignments": {}}

    teams = list(UNDERDOG_TEAMS)
    random.shuffle(teams)

    assignments = {}
    for i, user in enumerate(users):
        assigned = teams[i % len(teams)]
        user.assigned_team = assigned
        assignments[user.nombre] = assigned

    # Trigger points recalculation for league_id = 1 (World Cup)
    recalculate_all_users_points(db, league_id=1)

    db.commit()

    return {"status": "success", "assignments": assignments}


@router.put("/tournament/results", status_code=status.HTTP_200_OK)
def update_tournament_results(
    body: TournamentResultsUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Update real tournament results and recalculate points for all users."""
    for key, val in [
        ("real_campeon", body.real_campeon),
        ("real_subcampeon", body.real_subcampeon),
        ("real_maximo_goleador", body.real_maximo_goleador),
        ("real_maximo_asistente", body.real_maximo_asistente),
    ]:
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = val
        else:
            setting = SystemSetting(key=key, value=val)
            db.add(setting)

    db.flush()

    # Recalculate all users' points for World Cup (league_id = 1)
    recalculate_all_users_points(db, league_id=1)
    return {"status": "success", "message": "Resultados del torneo actualizados y puntuación recalculada"}


@router.post("/settings/toggle-tournament-lock", response_model=dict)
def toggle_tournament_lock(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Toggle the tournament predictions lock status. Requires admin."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == "tournament_predictions_locked").first()
    if not setting:
        setting = SystemSetting(key="tournament_predictions_locked", value="true")
        db.add(setting)
        new_val = "true"
    else:
        new_val = "false" if setting.value == "true" else "true"
        setting.value = new_val
    db.commit()
    return {"status": "success", "locked": new_val == "true"}

