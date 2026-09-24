from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BASE_URL: str = "https://www.asos.com"
    STORE_CODE: str = "ROE"
    COUNTRY: str = "BG"
    CURRENCY: str = "EUR"
    LANG: str = "en-GB"
    KEYSTORE_DATAVERSION: str = "7qyyrb1-46"

    DEFAULT_LIMIT: int = 72
    REQUEST_TIMEOUT: int = 20
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5

    DB_PATH: Path = Path("data/asos.db")
    SAMPLES_DIR: Path = Path("data/samples")
    RAW_DIR: Path = Path("data/raw")
    LOGS_DIR: Path = Path("logs")

    HEADLESS: bool = True


settings = Settings()
