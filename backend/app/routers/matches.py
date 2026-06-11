from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Match, SystemSetting
from app.schemas import MatchDetail, MatchResponse, PredictionInMatch

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get("", response_model=List[MatchResponse])
def list_matches(
    fase: Optional[str] = Query(None, description="Filtrar por grupo o fase"),
    db: Session = Depends(get_db),
) -> List[MatchResponse]:
    """List all matches of the active league, optionally filtered by fase. Ordered by fecha_hora ASC."""
    active_league_id = SystemSetting.get_int(db, "active_league_id", 1)

    query = db.query(Match).filter(Match.league_id == active_league_id)
    if fase:
        query = query.filter(Match.grupo_o_fase == fase)
    matches = query.order_by(Match.fecha_hora.asc()).all()
    return [MatchResponse.model_validate(m) for m in matches]



@router.get("/{match_id}", response_model=MatchDetail)
def get_match(match_id: int, db: Session = Depends(get_db)) -> MatchDetail:
    """Get a single match with all its predictions."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partido no encontrado",
        )

    predictions_out = [
        PredictionInMatch(
            id=p.id,
            user_id=p.user_id,
            nombre_usuario=p.user.nombre,
            goles_local_pred=p.goles_local_pred,
            goles_visitante_pred=p.goles_visitante_pred,
            puntos_obtenidos=p.puntos_obtenidos,
        )
        for p in match.predictions
    ]

    return MatchDetail(
        id=match.id,
        equipo_local=match.equipo_local,
        equipo_visitante=match.equipo_visitante,
        fecha_hora=match.fecha_hora,
        grupo_o_fase=match.grupo_o_fase,
        goles_local_real=match.goles_local_real,
        goles_visitante_real=match.goles_visitante_real,
        es_partido_doble=match.es_partido_doble,
        predictions=predictions_out,
    )
