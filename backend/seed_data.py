"""
Seed script for Porra Mundial.

Creates:
- 1 admin user (admin / admin123)
- 3 test users
- 6 sample matches (mix of group stage, some with es_partido_doble=True)
- Sample predictions for the test users

Usage:
    python seed_data.py
"""

import sys
import os

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta

from app.database import Base, engine, SessionLocal
from app.models import Match, Prediction, User
from app.routers.auth import _hash_password


def seed():
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).first():
            print("⚠️  La base de datos ya tiene datos. Abortando seed.")
            return

        # ── Users ───────────────────────────────────────
        admin = User(
            nombre="admin",
            password_hash=_hash_password("admin123"),
            is_admin=True,
        )
        user1 = User(
            nombre="carlos",
            password_hash=_hash_password("carlos123"),
        )
        user2 = User(
            nombre="lucia",
            password_hash=_hash_password("lucia123"),
        )
        user3 = User(
            nombre="mateo",
            password_hash=_hash_password("mateo123"),
        )

        db.add_all([admin, user1, user2, user3])
        db.flush()  # Get IDs

        print(f"✅ Usuarios creados: admin, carlos, lucia, mateo")

        # ── Matches ─────────────────────────────────────
        base_date = datetime(2026, 6, 15, 18, 0, 0)

        matches = [
            Match(
                equipo_local="España",
                equipo_visitante="Alemania",
                fecha_hora=base_date,
                grupo_o_fase="Grupo A",
                es_partido_doble=False,
            ),
            Match(
                equipo_local="Portugal",
                equipo_visitante="Marruecos",
                fecha_hora=base_date + timedelta(days=1),
                grupo_o_fase="Grupo A",
                es_partido_doble=True,  # Spain's group rivals
            ),
            Match(
                equipo_local="Argentina",
                equipo_visitante="Brasil",
                fecha_hora=base_date + timedelta(days=2),
                grupo_o_fase="Grupo B",
                es_partido_doble=False,
            ),
            Match(
                equipo_local="Francia",
                equipo_visitante="Inglaterra",
                fecha_hora=base_date + timedelta(days=3),
                grupo_o_fase="Grupo C",
                es_partido_doble=False,
            ),
            Match(
                equipo_local="Alemania",
                equipo_visitante="Portugal",
                fecha_hora=base_date + timedelta(days=4),
                grupo_o_fase="Grupo A",
                es_partido_doble=True,  # Spain's group rivals
            ),
            Match(
                equipo_local="España",
                equipo_visitante="Marruecos",
                fecha_hora=base_date + timedelta(days=5),
                grupo_o_fase="Grupo A",
                es_partido_doble=False,
            ),
        ]

        db.add_all(matches)
        db.flush()

        print(f"✅ {len(matches)} partidos creados")

        # ── Predictions ─────────────────────────────────
        predictions = [
            # Carlos predictions
            Prediction(user_id=user1.id, match_id=matches[0].id, goles_local_pred=2, goles_visitante_pred=1),
            Prediction(user_id=user1.id, match_id=matches[1].id, goles_local_pred=1, goles_visitante_pred=1),
            Prediction(user_id=user1.id, match_id=matches[2].id, goles_local_pred=3, goles_visitante_pred=2),
            Prediction(user_id=user1.id, match_id=matches[3].id, goles_local_pred=1, goles_visitante_pred=0),
            # Lucia predictions
            Prediction(user_id=user2.id, match_id=matches[0].id, goles_local_pred=1, goles_visitante_pred=0),
            Prediction(user_id=user2.id, match_id=matches[1].id, goles_local_pred=0, goles_visitante_pred=2),
            Prediction(user_id=user2.id, match_id=matches[2].id, goles_local_pred=1, goles_visitante_pred=1),
            # Mateo predictions
            Prediction(user_id=user3.id, match_id=matches[0].id, goles_local_pred=0, goles_visitante_pred=0),
            Prediction(user_id=user3.id, match_id=matches[1].id, goles_local_pred=2, goles_visitante_pred=0),
            Prediction(user_id=user3.id, match_id=matches[3].id, goles_local_pred=2, goles_visitante_pred=2),
        ]

        db.add_all(predictions)
        db.commit()

        print(f"✅ {len(predictions)} predicciones creadas")
        print("\n🎉 Seed completado exitosamente!")
        print("\nCredenciales:")
        print("  admin  / admin123  (administrador)")
        print("  carlos / carlos123")
        print("  lucia  / lucia123")
        print("  mateo  / mateo123")

    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
