from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Match, Prediction, User, SystemSetting, TournamentPrediction
from app.schemas import (
    PredictionCreate,
    PredictionResponse,
    PredictionWithMatch,
    MatchResponse,
    CommunityPrediction,
    TournamentPredictionCreate,
    TournamentPredictionResponse,
    CommunityTournamentPrediction,
)
from app.services.validation_service import can_predict

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.post("", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_prediction(
    body: PredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionResponse:
    """Create or update a prediction (upsert). Validates deadline."""
    match = db.query(Match).filter(Match.id == body.match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partido no encontrado",
        )

    if not can_predict(match):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El plazo para pronosticar este partido ya ha cerrado",
        )

    # Upsert: check if prediction exists
    existing = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id, Prediction.match_id == body.match_id)
        .first()
    )

    if existing:
        existing.goles_local_pred = body.goles_local_pred
        existing.goles_visitante_pred = body.goles_visitante_pred
        db.commit()
        db.refresh(existing)
        return PredictionResponse.model_validate(existing)

    prediction = Prediction(
        user_id=current_user.id,
        match_id=body.match_id,
        goles_local_pred=body.goles_local_pred,
        goles_visitante_pred=body.goles_visitante_pred,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return PredictionResponse.model_validate(prediction)


@router.get("/me", response_model=List[PredictionWithMatch])
def get_my_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PredictionWithMatch]:
    """Get all predictions for the current user."""
    predictions = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .all()
    )
    return [
        PredictionWithMatch(
            id=p.id,
            user_id=p.user_id,
            match_id=p.match_id,
            goles_local_pred=p.goles_local_pred,
            goles_visitante_pred=p.goles_visitante_pred,
            puntos_obtenidos=p.puntos_obtenidos,
            match=MatchResponse.model_validate(p.match),
        )
        for p in predictions
    ]


@router.get("/user/{user_id}", response_model=List[PredictionWithMatch])
def get_user_predictions(
    user_id: int,
    db: Session = Depends(get_db),
) -> List[PredictionWithMatch]:
    """Get all predictions for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    predictions = (
        db.query(Prediction)
        .filter(Prediction.user_id == user_id)
        .all()
    )
    return [
        PredictionWithMatch(
            id=p.id,
            user_id=p.user_id,
            match_id=p.match_id,
            goles_local_pred=p.goles_local_pred,
            goles_visitante_pred=p.goles_visitante_pred,
            puntos_obtenidos=p.puntos_obtenidos,
            match=MatchResponse.model_validate(p.match),
        )
        for p in predictions
    ]


@router.get("/match/{match_id}", response_model=List[CommunityPrediction])
def get_community_predictions(
    match_id: int,
    db: Session = Depends(get_db),
) -> List[CommunityPrediction]:
    """Get predictions of other users (excluding admins) for a match after kickoff."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partido no encontrado",
        )

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if now_utc < match.fecha_hora:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Las predicciones de la comunidad solo están disponibles después del inicio del partido.",
        )

    predictions = (
        db.query(Prediction)
        .join(User)
        .filter(
            Prediction.match_id == match_id,
            User.is_admin == False,
        )
        .all()
    )

    return [
        CommunityPrediction(
            username=p.user.nombre,
            goles_local=p.goles_local_pred,
            goles_visitante=p.goles_visitante_pred,
            puntos_ganados=p.puntos_obtenidos,
        )
        for p in predictions
    ]


# ──────────────────────────────────────────────
# Tournament Predictions
# ──────────────────────────────────────────────

TOURNAMENT_DEADLINE = datetime(2026, 6, 13, 19, 0, 0)


@router.get("/tournament", response_model=TournamentPredictionResponse)
def get_my_tournament_prediction(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TournamentPredictionResponse:
    """Get current user's tournament prediction or empty values if none."""
    pred = db.query(TournamentPrediction).filter(TournamentPrediction.user_id == current_user.id).first()
    if not pred:
        return TournamentPredictionResponse(
            id=0,
            user_id=current_user.id,
            campeon="",
            subcampeon="",
            maximo_goleador="",
            maximo_asistente="",
            created_at=datetime.now(timezone.utc),
        )
    return TournamentPredictionResponse.model_validate(pred)


@router.post("/tournament", response_model=TournamentPredictionResponse)
def save_tournament_prediction(
    body: TournamentPredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TournamentPredictionResponse:
    """Save or update tournament prediction. Locked after deadline."""
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if now_utc >= TOURNAMENT_DEADLINE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El plazo para registrar/modificar predicciones del torneo ha cerrado",
        )

    existing = db.query(TournamentPrediction).filter(TournamentPrediction.user_id == current_user.id).first()
    if existing:
        existing.campeon = body.campeon
        existing.subcampeon = body.subcampeon
        existing.maximo_goleador = body.maximo_goleador
        existing.maximo_asistente = body.maximo_asistente
        existing.created_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return TournamentPredictionResponse.model_validate(existing)

    pred = TournamentPrediction(
        user_id=current_user.id,
        campeon=body.campeon,
        subcampeon=body.subcampeon,
        maximo_goleador=body.maximo_goleador,
        maximo_asistente=body.maximo_asistente,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return TournamentPredictionResponse.model_validate(pred)


@router.get("/tournament/community", response_model=List[CommunityTournamentPrediction])
def get_community_tournament_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CommunityTournamentPrediction]:
    """Get all community tournament predictions. Locked until deadline."""
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if now_utc < TOURNAMENT_DEADLINE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Las predicciones del torneo de la comunidad solo se revelan después de la fecha límite",
        )

    predictions = (
        db.query(TournamentPrediction)
        .join(User)
        .filter(User.is_admin == False)
        .all()
    )
    return [
        CommunityTournamentPrediction(
            username=p.user.nombre,
            campeon=p.campeon,
            subcampeon=p.subcampeon,
            maximo_goleador=p.maximo_goleador,
            maximo_asistente=p.maximo_asistente,
        )
        for p in predictions
    ]


@router.get("/tournament/results")
def get_tournament_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the real/final results of the tournament."""
    return {
        "real_campeon": SystemSetting.get_str(db, "real_campeon", ""),
        "real_subcampeon": SystemSetting.get_str(db, "real_subcampeon", ""),
        "real_maximo_goleador": SystemSetting.get_str(db, "real_maximo_goleador", ""),
        "real_maximo_asistente": SystemSetting.get_str(db, "real_maximo_asistente", ""),
    }
