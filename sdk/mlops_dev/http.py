"""HTTP layer — all API calls go through here."""
import os
import json
from typing import Any, Dict, Optional

from .exceptions import (
    MLOpsError, AuthenticationError,
    RateLimitError, NetworkError,
)

DEFAULT_BASE = "https://api.mlops.dev/v1"


class HTTPClient:
    """
    Thin wrapper around requests.
    Raises typed exceptions for every HTTP error.
    """

    def __init__(
        self,
        api_key:  str,
        base_url: str = DEFAULT_BASE,
        timeout:  int = 30,
    ):
        self.api_key  = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout  = timeout

    def _headers(self, extra: Optional[Dict] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "User-Agent":    "mlops-dev-python/0.7.0",
            "Accept":        "application/json",
        }
        if extra:
            h.update(extra)
        return h

    def request(
        self,
        method: str,
        path:   str,
        *,
        json:   Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            import requests as _r
        except ImportError:
            raise MLOpsError(
                "requests is required: pip install mlops-dev"
            )

        url = f"{self.base_url}{path}"
        try:
            resp = _r.request(
                method.upper(), url,
                headers=self._headers(headers),
                json=json,
                params=params,
                timeout=timeout or self.timeout,
            )
        except _r.exceptions.ConnectionError as e:
            raise NetworkError(f"Cannot reach {url}: {e}") from e
        except _r.exceptions.Timeout:
            raise NetworkError(f"Request timed out: {url}")

        # ── Error handling ─────────────────────────────────────────
        if resp.status_code == 401:
            raise AuthenticationError(
                "Invalid API key. Get yours at https://www.mlops.dev/dashboard → Settings."
            )
        if resp.status_code == 404:
            try:    detail = resp.json().get("error", "not found")
            except: detail = "not found"
            raise MLOpsError(f"Not found ({path}): {detail}")
        if resp.status_code == 429:
            retry = resp.headers.get("Retry-After", "60")
            raise RateLimitError(
                f"Rate limited. Retry after {retry}s. "
                "Consider caching results or reducing poll frequency."
            )
        if resp.status_code >= 500:
            raise MLOpsError(
                f"Server error {resp.status_code}. "
                "Check https://www.mlops.dev/status or email hello@mlops.dev"
            )
        if not resp.ok:
            try:    detail = resp.json().get("error", resp.text[:120])
            except: detail = resp.text[:120]
            raise MLOpsError(f"API error {resp.status_code}: {detail}")

        return resp.json()

    def upload(
        self,
        path:  str,
        files: Dict,
        data:  Dict,
    ) -> Dict[str, Any]:
        """Multipart upload — used for model push."""
        try:
            import requests as _r
        except ImportError:
            raise MLOpsError("requests is required: pip install mlops-dev")

        # Do NOT set Content-Type here — requests sets it automatically
        # for multipart/form-data including the boundary parameter.
        # Setting it manually breaks the upload.
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent":    "mlops-dev-python/0.7.0",
            "Accept":        "application/json",
        }
        url = f"{self.base_url}{path}"
        try:
            resp = _r.post(url, files=files, data=data,
                           headers=headers, timeout=300)
        except _r.exceptions.ConnectionError as e:
            raise NetworkError(f"Upload failed — cannot reach {url}: {e}") from e

        if resp.status_code == 401:
            raise AuthenticationError("Invalid API key.")
        if not resp.ok:
            raise MLOpsError(f"Upload failed {resp.status_code}: {resp.text[:120]}")
        return resp.json()
