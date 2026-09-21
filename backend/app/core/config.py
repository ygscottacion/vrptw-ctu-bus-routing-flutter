from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "CTU Bus Routing API"
    API_V1_STR: str = "/api/v1"

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "123456"
    POSTGRES_DB: str = "ctu_bus_db"
    POSTGRES_PORT: int = 5432
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # Supabase Settings
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    CRON_SECRET: str = "ctu_bus_cron_secret_2026_super_secure_x987"

    # Security Settings
    SECRET_KEY: str = "changeme_secret_key_please_set_in_env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Environment Settings
    ENVIRONMENT: str = "development"

    # Google Routes API Settings
    GOOGLE_ROUTES_API_KEY: str = ""

    # Goong Maps API Settings
    GOONG_API_KEY: str = ""
    GOONG_MAPTILES_KEY: str = ""
    GOONG_DIRECTION_BASE_URL: str = "https://rsapi.goong.io/Direction"
    GOONG_DISTANCE_MATRIX_BASE_URL: str = "https://rsapi.goong.io/DistanceMatrix"

    def validate_goong_config(self) -> None:
        """Validate Goong API key configuration.
        Fail-fast in production if missing. Log warning in development.
        """
        import logging
        logger = logging.getLogger(__name__)
        if not self.GOONG_API_KEY or self.GOONG_API_KEY.startswith("your-"):
            if self.ENVIRONMENT.lower() in ("production", "prod"):
                raise ValueError(
                    "CRITICAL: GOONG_API_KEY is missing or unconfigured in production environment! "
                    "Cannot start service without valid Goong API key."
                )
            else:
                logger.warning(
                    "WARNING: GOONG_API_KEY is not configured. "
                    "Goong distance matrix service will fallback to StaticDistanceMatrixProvider."
                )



    @property
    def SUPABASE_JWKS_URL(self) -> str:
        if self.SUPABASE_URL:
            base = self.SUPABASE_URL.rstrip("/")
            return f"{base}/auth/v1/.well-known/jwks.json"
        return ""

    @property
    def SUPABASE_ISSUER(self) -> str:
        if self.SUPABASE_URL:
            base = self.SUPABASE_URL.rstrip("/")
            return f"{base}/auth/v1"
        return ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def assemble_db_connection(self) -> str:
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
