from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Session

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    puntos_totales = Column(Integer, default=0)
    aciertos_perfectos = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    predictions = relationship("Prediction", back_populates="user", lazy="selectin")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipo_local = Column(String(100), nullable=False)
    equipo_visitante = Column(String(100), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    grupo_o_fase = Column(String(50), nullable=False)
    goles_local_real = Column(Integer, nullable=True)
    goles_visitante_real = Column(Integer, nullable=True)
    es_partido_doble = Column(Boolean, default=False)
    api_id = Column(Integer, unique=True, nullable=True)
    league_id = Column(Integer, default=1, nullable=False)

    predictions = relationship("Prediction", back_populates="match", lazy="selectin")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(String(255), nullable=False)

    @classmethod
    def get_int(cls, db: Session, key: str, default: int) -> int:
        try:
            setting = db.query(cls).filter(cls.key == key).first()
            if setting and setting.value is not None:
                try:
                    return int(setting.value)
                except ValueError:
                    pass
        except Exception:
            pass
        return default

    @classmethod
    def get_str(cls, db: Session, key: str, default: str) -> str:
        try:
            setting = db.query(cls).filter(cls.key == key).first()
            if setting and setting.value is not None:
                return setting.value
        except Exception:
            pass
        return default


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_user_match"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    goles_local_pred = Column(Integer, nullable=False)
    goles_visitante_pred = Column(Integer, nullable=False)
    puntos_obtenidos = Column(Integer, default=0)

    user = relationship("User", back_populates="predictions")
    match = relationship("Match", back_populates="predictions")
