from abc import ABC, abstractmethod
from typing import Any, Optional
from src.core.client import ResilientHttpClient


class BaseExtractor(ABC):
    """
    Abstract base class for target website extractors.
    """

    def __init__(self, client: Optional[ResilientHttpClient] = None):
        self.client = client or ResilientHttpClient()

    @abstractmethod
    def fetch_page(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch a single page of data from the target."""
        pass

    def close(self) -> None:
        if self.client:
            self.client.close()
