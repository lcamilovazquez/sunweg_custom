"""
API wrapper for the SunWEG platform.

This module abstracts the HTTP interactions with the SunWEG API. It uses
asyncio-compatible methods via aiohttp to login and fetch data for a given
photovoltaic plant (usina). The API encapsulates token handling and
automatically injects required headers on each request.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from .const import API_BASE_URL, HEADER_USER_AGENT

_LOGGER = logging.getLogger(__name__)


class SunWegAPIError(Exception):
    """Raised when an unexpected response is returned from the API."""


class SunWegAuthError(SunWegAPIError):
    """Raised when authentication fails or the token has expired."""


class SunWegAPI:
    """Asynchronous client for interacting with the SunWEG REST API."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: Optional[str] = None

    async def async_login(self) -> None:
        """Authenticate with the API and store the returned token.

        Raises:
            SunWegAuthError: If authentication fails.
            SunWegAPIError: If an unexpected error occurs.
        """
        url = f"{API_BASE_URL}/login/autenticacao"
        payload = {
            "usuario": self._username,
            "senha": self._password,
            # The following fields mirror those observed in the HAR capture.  The
            # service appears to accept a login without CAPTCHA tokens when
            # originating from the mobile/HA integration context; should that
            # assumption prove false the integration can be extended to prompt
            # users for a captcha token.
            "rememberMe": False,
            "aceito": False,
        }
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": HEADER_USER_AGENT,
        }
        try:
            async with self._session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    _LOGGER.error("Authentication failed, status %s", resp.status)
                    raise SunWegAuthError(f"Authentication failed: HTTP {resp.status}")
                data: Dict[str, Any] = await resp.json()
        except aiohttp.ClientError as err:
            raise SunWegAPIError(f"Error communicating with SunWEG API: {err}") from err

        if not data.get("success") or "token" not in data:
            _LOGGER.error("Authentication response missing token: %s", data)
            raise SunWegAuthError("Invalid credentials or unexpected response")
        self._token = data["token"]
        _LOGGER.debug("Logged in successfully, token set")

    def _auth_headers(self) -> Dict[str, str]:
        """Construct headers for authenticated API calls."""
        if not self._token:
            raise SunWegAuthError("Attempted to call API without a token")
        return {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": HEADER_USER_AGENT,
            "X-Auth-Token-Update": self._token,
        }

    async def _get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal helper to perform a GET request and return the parsed JSON.

        Args:
            endpoint: Path portion of the API endpoint (starting with '/').
            params: Optional dictionary of query parameters.

        Returns:
            The parsed JSON response.

        Raises:
            SunWegAuthError: If authentication is missing or the token has expired.
            SunWegAPIError: For connection problems or non-JSON responses.
        """
        url = f"{API_BASE_URL}{endpoint}"
        headers = self._auth_headers()
        try:
            async with self._session.get(url, headers=headers, params=params) as resp:
                # If unauthorized, refresh the token once and retry
                if resp.status == 401:
                    _LOGGER.warning("Token appears to have expired, attempting reauthentication")
                    await self.async_login()
                    headers = self._auth_headers()
                    async with self._session.get(url, headers=headers, params=params) as retry_resp:
                        if retry_resp.status >= 400:
                            raise SunWegAPIError(
                                f"HTTP {retry_resp.status} when fetching {endpoint}"
                            )
                        try:
                            data = await retry_resp.json()
                        except aiohttp.ContentTypeError:
                            text = await retry_resp.text()
                            raise SunWegAPIError(
                                f"Unexpected content type for {endpoint}: {text[:100]}..."
                            )
                else:
                    if resp.status >= 400:
                        raise SunWegAPIError(f"HTTP {resp.status} when fetching {endpoint}")
                    try:
                        data = await resp.json()
                    except aiohttp.ContentTypeError:
                        # API sometimes returns HTML with 500 errors; capture for debugging
                        text = await resp.text()
                        raise SunWegAPIError(
                            f"Unexpected content type for {endpoint}: {text[:100]}..."
                        )
        except aiohttp.ClientError as err:
            raise SunWegAPIError(f"Error fetching {endpoint}: {err}") from err
        except SunWegAPIError:
            raise
        except Exception as ex:
            raise SunWegAPIError(f"Unexpected response from {endpoint}: {ex}") from ex

        return data

    async def async_get_resumo(self, plant_id: str) -> Dict[str, Any]:
        """Fetch summary data (energy, power, capacity) for a given plant.

        Args:
            plant_id: Identifier of the plant (usina) to filter.

        Returns:
            A dictionary containing the summary information for the plant. If
            multiple plants are returned the first matching entry is used.

        The API for ``getdadosresumo`` appears unstable when queried with
        explicit plant parameters (usina or id). To avoid server errors, this
        method requests all plants and filters locally. Should the API
        stabilise in the future, a more targeted call can be reinstated.
        """
        # Fetch all plants to avoid API 500 errors when filtering by id.
        params = {
            "usina": "",
            "id": "",
            "situacao": "null",
            "limite": 100,
            "quantidade": 0,
            "paginaAtual": 1,
            "agrupado": "false",
            "gettotalizadores": "false",
        }
        data = await self._get_json("/getdadosresumo", params=params)
        if not data.get("success"):
            raise SunWegAPIError(f"Failed to fetch summary: {data}")
        usinas = data.get("usinas", [])
        # Find the matching plant; fallback to first entry if none explicitly match
        plant_summary: Optional[Dict[str, Any]] = None
        for u in usinas:
            if str(u.get("id")) == str(plant_id):
                plant_summary = u
                break
        if plant_summary is None and usinas:
            plant_summary = usinas[0]
        return plant_summary or {}

    async def async_get_all_plants(self) -> Dict[str, Any]:
        """Retrieve a mapping of plant IDs to their names.

        Returns:
            A dictionary {id: name} for each accessible plant.
        """
        params = {
            "usina": "",
            "id": "",
            "situacao": "null",
            "limite": 100,
            "quantidade": 0,
            "paginaAtual": 1,
            "agrupado": "false",
            "gettotalizadores": "false",
        }
        data = await self._get_json("/getdadosresumo", params=params)
        plants = {}
        if data.get("success"):
            for plant in data.get("usinas", []):
                pid = plant.get("id")
                name = plant.get("nome")
                if pid is not None and name is not None:
                    plants[str(pid)] = name
        return plants

    async def async_get_totalizadores(self) -> Dict[str, Any]:
        """Fetch aggregated totals across all plants.

        Returns:
            A dictionary containing various aggregated metrics such as total
            energy generated and power currently being produced.
        """
        data = await self._get_json("/gettotalizadores")
        if not data.get("success"):
            raise SunWegAPIError(f"Failed to fetch totalizers: {data}")
        return data.get("dados", {})
