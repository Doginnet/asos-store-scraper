from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
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
    LANG: str = Field(default="en-GB", validation_alias=AliasChoices("ASOS_LANG", "BROWSE_LANGUAGE", "LANG"))
    KEYSTORE_DATAVERSION: str = "7qyyrb1-46"

    @field_validator("LANG", mode="after")
    @classmethod
    def sanitize_lang(cls, v: str) -> str:
        """Ensure system POSIX locales like en_US.UTF-8 don't leak into ASOS API calls."""
        if "_" in v or "." in v or not v:
            return "en-GB"
        return v

    DEFAULT_LIMIT: int = 72
    REQUEST_TIMEOUT: int = 20
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5

    # Verified Postman session cookies from working cURL
    DEFAULT_COOKIES: dict[str, str] = {
        "geocountry": "BG",
        "asos_drmlp": "14ab6a29a24b59f27780282b3d79cb7d",
        "keyStoreDataversion": "7qyyrb1-46",
        "siteChromeVersion": "au=13&com=13&de=13&dk=13&es=13&fr=13&it=13&nl=13&pl=13&roe=13&row=13&ru=13&se=13&us=13",
        "asosAffiliate": "affiliateId=31343",
        "browseCountry": "BG",
        "browseCurrency": "EUR",
        "browseLanguage": "en-GB",
        "browseSizeSchema": "EU",
        "storeCode": "ROE",
        "currency": "19",
        "featuresId": "c9885693-4fb4-4fb9-ae8e-6502eb",
    }

    DB_PATH: Path = Path("data/asos.db")
    SAMPLES_DIR: Path = Path("data/samples")
    RAW_DIR: Path = Path("data/raw")
    LOGS_DIR: Path = Path("logs")
    HEADLESS: bool = True

    # Telegram Alerting Skeleton (tokens optional in .env)
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    ALERT_MIN_DISCOUNT_PERCENT: float = 60.0



settings = Settings()
