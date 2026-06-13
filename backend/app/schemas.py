from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


# ──────────────────────────────────────────────
# Auth schemas
# ──────────────────────────────────────────────

class AuthRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=4, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    nombre: str
    is_admin: bool


# ──────────────────────────────────────────────
# User schemas
# ──────────────────────────────────────────────

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    puntos_totales: int
    aciertos_perfectos: int
    assigned_team: Optional[str] = None
    created_at: datetime


class UserRanking(UserPublic):
    posicion: int
    puntos_underdog: int
    puntos_predicciones: int


# ──────────────────────────────────────────────
# Match schemas
# ──────────────────────────────────────────────

class MatchCreate(BaseModel):
    equipo_local: str = Field(..., min_length=1, max_length=100)
    equipo_visitante: str = Field(..., min_length=1, max_length=100)
    fecha_hora: datetime
    grupo_o_fase: str = Field(..., min_length=1, max_length=50)
    es_partido_doble: bool = False
    api_id: Optional[int] = None
    league_id: int = 1



class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipo_local: str
    equipo_visitante: str
    fecha_hora: datetime
    grupo_o_fase: str

    @field_serializer('fecha_hora')
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    goles_local_real: Optional[int] = None
    goles_visitante_real: Optional[int] = None
    es_partido_doble: bool
    api_id: Optional[int] = None
    league_id: int = 1



class PredictionInMatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    nombre_usuario: str
    goles_local_pred: int
    goles_visitante_pred: int
    puntos_obtenidos: int


class MatchDetail(MatchResponse):
    predictions: List[PredictionInMatch] = []


# ──────────────────────────────────────────────
# Prediction schemas
# ──────────────────────────────────────────────

class PredictionCreate(BaseModel):
    match_id: int
    goles_local_pred: int = Field(..., ge=0)
    goles_visitante_pred: int = Field(..., ge=0)


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    match_id: int
    goles_local_pred: int
    goles_visitante_pred: int
    puntos_obtenidos: int


class PredictionWithMatch(PredictionResponse):
    match: MatchResponse


class CommunityPrediction(BaseModel):
    username: str
    goles_local: int
    goles_visitante: int
    puntos_ganados: int



# ──────────────────────────────────────────────
# Admin schemas
# ──────────────────────────────────────────────

class MatchResultUpdate(BaseModel):
    goles_local_real: int = Field(..., ge=0)
    goles_visitante_real: int = Field(..., ge=0)


class RecalculationResult(BaseModel):
    match_id: int
    predictions_updated: int
    users_updated: int


# ──────────────────────────────────────────────
# Settings schemas
# ──────────────────────────────────────────────

class CompetitionResponse(BaseModel):
    league_id: int
    name: str
    season: int


class SettingResponse(BaseModel):
    key: str
    value: str


class ActiveCompetitionUpdate(BaseModel):
    league_id: int

