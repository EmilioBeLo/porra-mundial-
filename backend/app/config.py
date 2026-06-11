import os
from typing import List


class Settings:
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./porra_mundial.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

    API_FOOTBALL_KEY: str = os.getenv("API_FOOTBALL_KEY", "295d4fb1c2874959ac098d3978746dcb")
    API_FOOTBALL_URL: str = os.getenv("API_FOOTBALL_URL", "https://v3.football.api-sports.io")
    API_FOOTBALL_LEAGUE_ID: int = int(os.getenv("API_FOOTBALL_LEAGUE_ID", "1"))
    API_FOOTBALL_SEASON: int = int(os.getenv("API_FOOTBALL_SEASON", "2026"))

    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins_env = os.getenv("CORS_ORIGINS", "")
        if origins_env:
            return [o.strip() for o in origins_env.split(",")]
        return [
            "http://localhost:4200",
            "http://localhost:5173",
            "https://*.vercel.app",
        ]


settings = Settings()
