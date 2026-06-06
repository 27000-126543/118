import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./geodynamo.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "geodynamo-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    UPLOAD_DIR: str = "./uploads"
    OUTPUT_DIR: str = "./outputs"
    REPORT_DIR: str = "./reports"
    MAX_CONCURRENT_SIMULATIONS: int = 3
    CRITICAL_MAGNETIC_REYNOLDS: float = 50.0
    MAX_DIPOLE_TILT: float = 10.0
    MAX_CONSECUTIVE_FAILURES: int = 3

    class Config:
        env_file = ".env"

    def ensure_dirs(self):
        for dir_path in [self.UPLOAD_DIR, self.OUTPUT_DIR, self.REPORT_DIR]:
            os.makedirs(dir_path, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
