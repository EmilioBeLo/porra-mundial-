from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal, run_auto_migrations
from app.models import SystemSetting
from app.routers import admin, auth, matches, predictions, users, settings as settings_router, sync

# Create all tables on startup
Base.metadata.create_all(bind=engine)
run_auto_migrations(engine)

# Seed database with initial system settings if not present
db = SessionLocal()
try:
    if db.query(SystemSetting).count() == 0:
        db.add_all([
            SystemSetting(key="active_league_id", value="1"),
            SystemSetting(key="active_season", value="2026"),
            SystemSetting(key="active_league_name", value="Mundial de Fútbol"),
        ])
        db.commit()
    
    # Ensure tournament_predictions_locked key exists
    lock_setting = db.query(SystemSetting).filter(SystemSetting.key == "tournament_predictions_locked").first()
    if not lock_setting:
        db.add(SystemSetting(key="tournament_predictions_locked", value="true"))
        db.commit()
    
    # Ensure all Spain/España matches are marked as double matches (x2)
    from app.models import Match
    spain_matches = db.query(Match).filter(
        (Match.equipo_local.in_(["Spain", "España"])) | 
        (Match.equipo_visitante.in_(["Spain", "España"]))
    ).all()
    updated_any = False
    for m in spain_matches:
        if not m.es_partido_doble:
            m.es_partido_doble = True
            updated_any = True
    if updated_any:
        db.commit()

    # Recalculate standings on startup to ensure historical manual entries are updated/corrected
    from app.services.scoring_service import recalculate_all_users_points
    recalculate_all_users_points(db, league_id=1)

finally:
    db.close()

app = FastAPI(
    title="Porra Mundial API",
    description="API para el juego de predicciones del Mundial",
    version="1.0.0",
)

# CORS
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
for o in settings.CORS_ORIGINS:
    if "*" not in o and o not in origins:
        origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(matches.router)
app.include_router(predictions.router)
app.include_router(admin.router)
app.include_router(settings_router.router)
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Porra Mundial"}

