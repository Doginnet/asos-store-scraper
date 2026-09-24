"""ASOS product and search response models."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AsosPrice(BaseModel):
    """Product price details from ASOS API."""

    model_config = ConfigDict(extra="ignore")

    current: float
    previous: float | None = None
    rrp: float | None = None
    lowestPriceInLast30Days: float | None = None
    currency: str = "EUR"
    isMarkedDown: bool = False
    isOutletPrice: bool = False

    @property
    def discount_percent(self) -> float:
        """Calculate discount percentage between previous and current prices."""
        if self.previous is not None and self.previous > self.current:
            return round((self.previous - self.current) / self.previous * 100, 1)
        return 0.0

    @model_validator(mode="before")
    @classmethod
    def parse_raw_price(cls, data: Any) -> Any:
        """Parse raw price structure from ASOS API where price values are nested dicts."""
        if not isinstance(data, dict):
            return data

        parsed = dict(data)

        # Handle nested {'value': ..., 'text': ...} objects
        for field_name in ("current", "previous", "rrp", "lowestPriceInLast30Days"):
            val = parsed.get(field_name)
            if isinstance(val, dict):
                parsed[field_name] = val.get("value")

        return parsed


def _normalize_image_url(url: str) -> str:
    """Normalize image URL by prepending https: or https:// if protocol is missing."""
    if not url:
        return url
    if url.startswith("//"):
        return f"https:{url}"
    if not (url.startswith("http://") or url.startswith("https://")):
        return f"https://{url}"
    return url


class AsosProduct(BaseModel):
    """ASOS product item."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    productCode: int
    productType: str = "Product"
    brandName: str
    colour: str = ""
    price: AsosPrice
    url: str
    imageUrl: str
    additionalImageUrls: list[str] = Field(default_factory=list)
    isSellingFast: bool = False
    isPromotion: bool = False
    isNew: bool = False

    @field_validator("colour", mode="before")
    @classmethod
    def normalize_colour(cls, v: Any) -> str:
        return v or ""

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        """Make URL absolute with https://www.asos.com/ if relative."""
        if not v:
            return v
        if not v.startswith("http"):
            path = v.lstrip("/")
            return f"https://www.asos.com/{path}"
        return v

    @field_validator("imageUrl")
    @classmethod
    def normalize_image_url(cls, v: str) -> str:
        """Ensure image URL has https:// protocol."""
        return _normalize_image_url(v)

    @field_validator("additionalImageUrls")
    @classmethod
    def normalize_additional_image_urls(cls, v: list[str]) -> list[str]:
        """Ensure all additional image URLs have https:// protocol."""
        if not v:
            return []
        return [_normalize_image_url(u) for u in v if u]


class AsosSearchResponse(BaseModel):
    """Search / catalog response from ASOS API."""

    model_config = ConfigDict(extra="ignore")

    searchTerm: str = ""
    categoryName: str = ""
    itemCount: int = 0
    products: list[AsosProduct] = Field(default_factory=list)

    @field_validator("searchTerm", "categoryName", mode="before")
    @classmethod
    def normalize_strings(cls, v: Any) -> str:
        return v or ""
