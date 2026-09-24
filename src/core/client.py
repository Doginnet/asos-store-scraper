import time
import uuid
from typing import Any, Dict, Optional
from curl_cffi import requests
from loguru import logger

from config.settings import settings


class CircuitBreakerError(Exception):
    """Raised when continuous failures trigger the circuit breaker."""
    pass


class ResilientHttpClient:
    """
    Robust HTTP Client wrapping curl_cffi with TLS fingerprint impersonation,
    exponential backoff, automatic retry handling, and circuit breaking.
    """

    def __init__(
        self,
        impersonate: str = "chrome124",
        max_retries: int = settings.MAX_RETRIES,
        backoff_factor: float = settings.RETRY_BACKOFF_FACTOR,
        circuit_threshold: int = 5,
        proxy: Optional[str] = None
    ):
        self.impersonate = impersonate
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.circuit_threshold = circuit_threshold
        self.consecutive_failures = 0
        self.proxy = proxy

        self.session = requests.Session(impersonate=self.impersonate)
        self._init_default_headers()
        self._init_default_cookies()

    def _init_default_headers(self) -> None:
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "asos-c-name": "asos-web-ui-library",
            "asos-c-plat": "Web",
            "asos-c-ver": "5.0.0",
            "asos-cid": str(uuid.uuid4()),
            "priority": "u=1, i",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        })

    def _init_default_cookies(self) -> None:
        """Inject verified Postman session cookies to guarantee 100% storeapi & edge compatibility."""
        self.session.cookies.update(settings.DEFAULT_COOKIES)

    def warmup(self, url: str = settings.BASE_URL) -> None:
        """Lightweight warmup request to establish edge session and fresh security tokens."""
        try:
            logger.debug(f"Warming up HTTP session against {url}...")
            resp = self.session.get(url, timeout=10)
            logger.debug(f"Session warmed up successfully (HTTP {resp.status_code}, {len(self.session.cookies)} cookies).")
        except Exception as exc:
            logger.warning(f"Session warmup warning (non-fatal): {exc}")

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = settings.REQUEST_TIMEOUT,
        **kwargs: Any
    ) -> requests.Response:
        """
        Executes HTTP request with exponential backoff and circuit breaker safety.
        """
        if self.consecutive_failures >= self.circuit_threshold:
            raise CircuitBreakerError(
                f"Circuit breaker tripped after {self.consecutive_failures} continuous failures for host {url}"
            )

        attempt = 0
        last_exception: Optional[Exception] = None

        request_headers = headers or {}
        # Ensure fresh correlation ID per request if desired
        if "asos-cid" not in request_headers:
            request_headers["asos-cid"] = str(uuid.uuid4())

        proxies = {"all": self.proxy} if self.proxy else None

        while attempt < self.max_retries:
            attempt += 1
            try:
                logger.debug(f"[{attempt}/{self.max_retries}] {method.upper()} {url}")
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=request_headers,
                    timeout=timeout,
                    proxies=proxies,
                    **kwargs
                )

                # Check for anti-bot or server errors
                if response.status_code in (403, 429, 500, 502, 503, 504):
                    logger.warning(
                        f"Target returned HTTP {response.status_code} on attempt {attempt}. Response preview: {response.text[:200]}"
                    )
                    self._handle_retry_sleep(attempt)
                    continue

                # Successful response
                self.consecutive_failures = 0
                return response

            except Exception as exc:
                last_exception = exc
                logger.warning(f"Network error on attempt {attempt}: {exc}")
                self._handle_retry_sleep(attempt)

        self.consecutive_failures += 1
        error_msg = f"Failed to fetch {url} after {self.max_retries} attempts."
        if last_exception:
            error_msg += f" Last error: {last_exception}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from last_exception

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> requests.Response:
        return self.request("GET", url, params=params, **kwargs)

    def _handle_retry_sleep(self, attempt: int) -> None:
        sleep_duration = self.backoff_factor ** attempt
        logger.info(f"Backing off for {sleep_duration:.2f}s before retry...")
        time.sleep(sleep_duration)

    def close(self) -> None:
        self.session.close()
