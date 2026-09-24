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


settings = Settings()
