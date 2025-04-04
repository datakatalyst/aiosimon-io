# aiosimon_io/auth.py
#
# Copyright (c) 2025 Datakatalyst
#
# This file is part of aiosimon-io.
#
# aiosimon-io is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# aiosimon-io is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with aiosimon-io. If not, see <https://www.gnu.org/licenses/>.

"""
Module for handling authentication and making authenticated requests.

This module provides an abstract base class and a concrete implementation
for managing authentication with the Simon Cloud API.
"""

from __future__ import annotations

import datetime
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

import aiohttp

from .const import AUTH_BASE_URL, SNS_BASE_URL

logger = logging.getLogger(__name__)


class AbstractAuth(ABC):
    """Abstract base class for making authenticated requests.

    This class provides a framework for handling authentication and making
    HTTP requests with an access token.

    :canonical: aiosimon_io.auth.AbstractAuth
    """

    def __init__(self, websession: aiohttp.ClientSession, host: str):
        """Initialize the AbstractAuth instance.

        Args:
            websession (aiohttp.ClientSession): The aiohttp session to use for requests.
            host (str): The base URL for the API.
        """
        self.session = websession
        self.sns_url = host

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Retrieve a valid access token.

        Returns:
            str: A valid access token.
        """

    async def async_request(self, method, endpoint, **kwargs) -> dict:
        """Make an authenticated HTTP request.

        Args:
            method (str): The HTTP method (e.g., 'GET', 'POST').
            endpoint (str): The API endpoint to call.
            **kwargs: Additional arguments to pass to the request.

        Returns:
            dict: The JSON response from the API.

        Raises:
            aiohttp.ClientConnectionError: If a connection error occurs.
            aiohttp.ClientResponseError: If the response contains an error.
            aiohttp.ClientError: For other client-related errors.
            Exception: For unexpected errors.
        """
        try:
            token: str = await self.async_get_access_token()
            headers: Dict[str, str] = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            url: str = f"{self.sns_url}/{endpoint}"
            logger.debug(f"Making SNS request: {method} {url}")

            async with self.session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                response.raise_for_status()
                logger.debug(f"SNS request successful. Status: {response.status}")
                return await response.json()

        except aiohttp.ClientConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise
        except aiohttp.ClientResponseError as e:
            logger.error(f"Response error: {e}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Client error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def async_request_hub(
        self, method, url, failover_endpoint, auth, **kwargs
    ) -> dict:
        """Make a request to the hub, with failover support.

        Args:
            method (str): The HTTP method (e.g., 'GET', 'POST').
            url (str): The primary URL for the request.
            failover_endpoint (str): The failover endpoint to use if the primary request fails.
            auth: Authentication information for the request.
            **kwargs: Additional arguments to pass to the request.

        Returns:
            dict: The JSON response from the API.

        Raises:
            Exception: If both the primary and failover requests fail.
        """
        try:
            headers: Dict[str, str] = {"Content-Type": "application/json"}
            logger.debug(f"Making hub request: {method} {url}")

            async with self.session.request(
                method, url, headers=headers, auth=auth, **kwargs
            ) as response:
                response.raise_for_status()
                logger.debug(f"Hub request successful. Status: {response.status}")
                return await response.json()

        except Exception as e:
            logger.debug(f"Getting error in hub local request: {e}")

            if failover_endpoint:
                logger.debug(f"Failing over to {failover_endpoint} by S&S API.")
                try:
                    return await self.async_request(method, failover_endpoint, **kwargs)
                except Exception as e:
                    logger.error(f"Error in hub failover request: {e}")
                    raise
            else:
                raise


class SimonAuth(AbstractAuth):
    """Handle authentication with the Simon Cloud API.

    This class manages access and refresh tokens for interacting with the
    Simon Cloud API.

    :canonical: aiosimon_io.auth.SimonAuth
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the SimonAuth instance.

        Args:
            client_id (str): The client ID for the application.
            client_secret (str): The client secret for the application.
            username (str): The username for authentication.
            password (str): The password for authentication.
            session (aiohttp.ClientSession): The aiohttp session to use for requests.
        """
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.username: str = username
        self.password: str = password
        self.auth_base_url: str = AUTH_BASE_URL
        self.sns_base_url: str = SNS_BASE_URL
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime.datetime] = None
        self.session: aiohttp.ClientSession = session
        super().__init__(self.session, self.sns_base_url)

    async def _async_authenticate(self) -> None:
        """Authenticate with the Simon Cloud API.

        Retrieves access and refresh tokens.

        Raises:
            aiohttp.ClientResponseError: If the authentication request fails.
        """
        url: str = f"{self.auth_base_url}/oauth/v2/token"
        logger.debug(f"Authenticating with {url}")

        async with self.session.post(
            url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password,
                "grant_type": "password",
            },
        ) as response:
            if response.status != 200:
                logger.error(
                    f"Authentication failed: {response.status} {await response.text()}"
                )
                response.raise_for_status()

            logger.debug(f"Authentication successful: {response.status}")
            response_data: dict = await response.json()
            self.access_token = response_data.get("access_token")
            self.refresh_token = response_data.get("refresh_token")
            self.token_expires_at = self._parse_expires_in(
                response_data.get("expires_in", 0)
            )

    async def async_refresh_access_token(self) -> None:
        """Refresh the access token using the refresh token.

        Raises:
            ValueError: If no refresh token is available.
            aiohttp.ClientResponseError: If the token refresh request fails.
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available.")

        url: str = f"{self.auth_base_url}/oauth/v2/token"
        logger.debug(f"Refreshing access token with {url}")

        async with self.session.post(
            url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        ) as response:
            if response.status != 200:
                logger.error(
                    f"Access token refresh failed: {response.status} {await response.text()}"
                )
                response.raise_for_status()

            logger.debug(f"Access token refresh successful: {response.status}")
            response_data: dict = await response.json()
            self.access_token = response_data.get("access_token")
            self.refresh_token = response_data.get("refresh_token")
            self.token_expires_at = self._parse_expires_in(
                response_data.get("expires_in", 0)
            )

    def _parse_expires_in(self, expires_in: int) -> datetime.datetime:
        """Calculate the token expiration time.

        Args:
            expires_in (int): The number of seconds until the token expires.

        Returns:
            datetime.datetime: The calculated expiration time.

        Raises:
            ValueError: If no expires_in value is provided.
        """
        if expires_in is None:
            raise ValueError("No expires_in value provided.")
        elif expires_in is not None and expires_in > 500:
            seconds = expires_in - 500
        else:
            seconds = expires_in
        return datetime.datetime.now() + datetime.timedelta(seconds=seconds)

    def _is_token_expired(self) -> bool:
        """Check if the current access token is expired.

        Returns:
            bool: True if the token is expired, False otherwise.

        Raises:
            ValueError: If no refresh token is available.
        """
        if self.refresh_token is not None and self.token_expires_at is not None:
            return True if datetime.datetime.now() >= self.token_expires_at else False
        else:
            raise ValueError("No refresh token available.")

    async def async_get_access_token(self) -> str:
        """Retrieve the current access token, refreshing it if necessary.

        Returns:
            str: The current access token.

        Raises:
            ValueError: If no access token is available.
        """
        if self.access_token is None:
            await self._async_authenticate()
        elif self._is_token_expired():
            await self.async_refresh_access_token()

        if not self.access_token:
            raise ValueError("No access token available.")

        return self.access_token
