# aiosimon_io/installations.py
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
Module for managing installations in the Simon iO system.

This module provides classes and methods to interact with installations,
retrieve their details, and manage associated devices.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timedelta
from typing import ClassVar, Dict, List, Literal, Optional

import aiohttp
from pydantic import BaseModel, Field

from .auth import AbstractAuth
from .const import (
    HUB_ELEMENTS_ENDPOINT,
    HUB_HARDWARE_TOKEN_ENDPOINT,
    INSTALLATIONS_ENDPOINT,
    SNS_ELEMENTS_ENDPOINT,
)
from .devices import Device

logger = logging.getLogger(__name__)


class Reachable(BaseModel):
    """Represents the reachability status of an installation."""

    type: Literal["WAN", "LAN"]
    next_check: Optional[datetime] = None


class Elements(BaseModel):
    """Represents the elements associated with an installation."""

    devices: Dict[str, "Device"] = {}
    # experiences: Dict[str, Experience] = {}


class Installation(BaseModel):
    """Represents an installation in the Simon iO system.

    :canonical: aiosimon_io.installations.Installation
    """

    _installations_endpoint: ClassVar[str] = INSTALLATIONS_ENDPOINT
    _sns_elements_endpoint: ClassVar[str] = SNS_ELEMENTS_ENDPOINT
    _hub_elements_endpoint: ClassVar[str] = HUB_ELEMENTS_ENDPOINT
    _api_client: ClassVar[AbstractAuth]

    id: str
    name: str
    icon: str
    role: Optional[str] = None
    mode: Literal["managed", "virtual"]
    status: Literal["up", "down"]
    username: Optional[str] = None
    password: Optional[str] = None
    hardwareToken: Optional[str] = None
    cleanMac: Optional[str] = None
    mac: Optional[str] = None
    apiVersion: Optional[str] = None
    softwareVersion: Optional[str] = None
    hardwareType: Optional[str] = None
    hardwareSubType: Optional[str] = None
    hardwareVersion: Optional[str] = None
    lanIp: Optional[str] = None
    wifiIp: Optional[str] = None
    port: Optional[int] = None
    currentNetwork: Optional[str] = None
    notificationSettings: Optional[dict] = None
    savedDateTime: Optional[str] = None
    mqttHost: Optional[str] = None
    mqttPort: Optional[int] = None
    mqttTls: Optional[bool] = None
    mdns: Optional[str] = None
    location: Optional[dict] = None
    backups: Optional[List[dict]] = None
    countryCode: Optional[str] = None
    elements: Elements = Field(default_factory=Elements)

    _reachable: Reachable = Reachable(type="WAN", next_check=None)
    _refresh_after: Optional[datetime] = None
    _ttl: int = 5
    _refresh_future: Optional[asyncio.Future] = None

    def __init__(self, **data) -> None:
        """Initialize an Installation instance.

        Args:
            **data: Arbitrary keyword arguments representing installation attributes.
        """
        super().__init__(**data)
        self._fetch_lock = asyncio.Lock()

    @classmethod
    async def async_get_installations(
        cls, api_client: AbstractAuth, ttl: int = 5
    ) -> List[Installation]:
        """
        Retrieve all installations for the current user asynchronously.

        Args:
            api_client (aiosimon_io.auth.AbstractAuth): The API client for authentication.
            ttl (int): The time-to-live for the cache in seconds.

        Returns:
            List[Installation]: A list of installations.
        """
        logger.debug("Getting installations")
        cls._api_client = api_client
        cls._ttl = ttl
        response: dict = await cls._api_client.async_request(
            "GET", cls._installations_endpoint
        )
        return [cls(**data) for data in response]

    @classmethod
    async def async_get_installation(
        cls, api_client: AbstractAuth, id: str, ttl: int = 5
    ) -> Installation:
        """
        Retrieve a specific installation by its ID asynchronously.

        Args:
            api_client (aiosimon_io.auth.AbstractAuth): The API client for authentication.
            id (str): The ID of the installation.
            ttl (int): The time-to-live for the cache in seconds.

        Returns:
            Installation: The installation object.
        """
        logger.debug(f"Getting intallation with id {id}")
        cls._api_client = api_client
        cls._ttl = ttl
        response: dict = await cls._api_client.async_request(
            "GET", f"{cls._installations_endpoint}/{id}"
        )
        return cls(**response)

    async def async_get_devices(self) -> Dict[str, Device]:
        """
        Retrieve all devices for the installation asynchronously.

        Returns:
            Dict[str, aiosimon_io.devices.Device]: A dictionary of devices associated with the installation.
        """
        logger.debug(f"Getting devices for installation {self.name}")
        if self.elements.devices is None or self._refresh():
            await self._fetch_elements_from_origin()
        return self.elements.devices

    async def async_get_device(self, id: str) -> Optional[Device]:
        """
        Retrieve a specific device by its ID asynchronously.

        Args:
            id (str): The ID of the device.

        Returns:
            Optional[aiosimon_io.devices.Device]: The device object if found, otherwise None.
        """
        logger.debug(f"Getting device {id} for installation {self.name}")
        if self.elements.devices.get(id) is None or self._refresh():
            await self._fetch_elements_from_origin()
        return self.elements.devices.get(id)

    def _get_local_base_url(self) -> str:
        """
        Get the base URL for the installation.

        Returns:
            str: The base URL.

        Raises:
            ValueError: If the installation is not in 'managed' mode or has invalid LAN IP or port.
        """
        if self.mode != "managed":
            raise ValueError(
                f"Base URL is only available for 'managed' installations. Installation {self.name} is in mode '{self.mode}'."
            )

        if not self.lanIp or not self.port:
            raise ValueError(
                f"Invalid LAN IP or port for installation {self.name}. LAN IP: {self.lanIp}, Port: {self.port}"
            )

        return f"http://{self.lanIp}:{self.port}"

    def _get_local_basic_auth(self) -> aiohttp.BasicAuth:
        """
        Get the basic authentication credentials for the installation.

        Returns:
            aiohttp.BasicAuth: The basic authentication object.

        Raises:
            ValueError: If the installation is not in 'managed' mode or has invalid credentials.
        """
        if self.mode != "managed":
            raise ValueError(
                f"Basic Auth is only available for 'managed' installations. Installation {self.name} is in mode '{self.mode}'."
            )
        if not self.username or not self.password:
            raise ValueError(
                f"Invalid username or password for installation {self.name}."
            )
        try:
            decoded_password: str = base64.b64decode(self.password).decode("utf-8")
            return aiohttp.BasicAuth(self.username, decoded_password)
        except Exception as e:
            raise ValueError(
                f"Error getting Basic Auth credentials for installation {self.name}: {e}"
            )

    def _refresh(self) -> bool:
        """
        Check if the devices need to be refreshed.

        Returns:
            bool: True if refresh is needed, otherwise False.
        """
        if self._refresh_after is None or self._refresh_after <= datetime.now():
            return True
        return False

    async def _fetch_elements_from_origin(self) -> None:
        """
        Fetch the elements from the origin and update the elements dictionary.

        Raises:
            Exception: If an error occurs during the fetch process.
        """
        # If there is an ongoing fetch, wait for it to finish
        if self._refresh_future is not None:
            logger.debug(f"Waiting for an ongoing fetch for installation {self.id}")
            await self._refresh_future
            return

        # Shield the fetch with a lock
        async with self._fetch_lock:
            logger.debug(
                f"Acquiring 'fetch from origin' lock for installation {self.id}"
            )

            # If the devices don't need to be refreshed, return
            if not self._refresh():
                return

            # Create a new Future
            self._refresh_future = asyncio.Future()

            try:
                local_path = self._hub_elements_endpoint
                sns_path = (
                    f"{self._sns_elements_endpoint.format(installation_id=self.id)}"
                )
                response: dict = await self._async_request_switcher(
                    "GET", local_path, sns_path
                )

                # Create, update or delete devices
                # 1. Get devices from response
                devices_from_response = {
                    device["id"]: device for device in response.get("devices", [])
                }

                # 2. Update or create devices
                for device_id, device_data in devices_from_response.items():
                    if device_id in self.elements.devices:
                        # Update existing device
                        for key, value in device_data.items():
                            if hasattr(self.elements.devices[device_id], key):
                                setattr(self.elements.devices[device_id], key, value)
                            else:
                                logger.warning(
                                    f"{device_id}: Attribute '{key}' does not exist in the Device class. Ignoring it."
                                )

                    else:
                        # Create new device
                        self.elements.devices[device_id] = Device(
                            **device_data, installation=self
                        )
                        self.elements.devices[device_id].installation = self

                # 3. Delete devices that are no longer in the response
                existing_device_ids = set(self.elements.devices.keys())
                response_device_ids = set(devices_from_response.keys())
                devices_to_remove = existing_device_ids - response_device_ids

                for device_id in devices_to_remove:
                    del self.elements.devices[device_id]

                # Set the Future result
                self._refresh_future.set_result(None)

            except Exception as e:
                logger.error(f"Error fetching elements for installation {self.id}: {e}")
                # Propagate the exception to the Future
                self._refresh_future.set_exception(e)
                raise

            finally:
                # Set a new refresh time
                self._refresh_after = datetime.now() + timedelta(seconds=self._ttl)
                # Clear the Future
                self._refresh_future = None

    async def _async_request_switcher(
        self, method, local_path, sns_path, **kwargs
    ) -> dict:
        """
        Switch between local and S&S API requests based on the installation reachability.

        Args:
            method (str): The HTTP method (e.g., "GET", "POST").
            local_path (str): The local API path.
            sns_path (str): The S&S API path.
            **kwargs: Additional arguments for the request.

        Returns:
            dict: The response from the API.
        """
        response: dict = {}
        if await self._async_reachable_by_lan():
            logger.debug("Make request to hub by local network")
            response = await self._api_client.async_request_hub(
                method=method,
                url=f"{self._get_local_base_url()}/{local_path}",
                failover_endpoint=sns_path,
                auth=self._get_local_basic_auth(),
                **kwargs,
            )
        else:
            logger.debug("Make request to hub by S&S API")
            response = await self._api_client.async_request(method, sns_path, **kwargs)

        return response

    async def _async_reachable_by_lan(self) -> bool:
        """
        Check if the installation is reachable by LAN.

        Returns:
            bool: True if reachable by LAN, otherwise False.
        """
        if self.mode != "managed":
            return False

        if (
            self._reachable.next_check is None
            or self._reachable.next_check <= datetime.now()
        ):
            url = self._get_local_base_url()
            auth = self._get_local_basic_auth()
            timeout = aiohttp.ClientTimeout(total=0.5)
            try:
                token = await self._api_client.async_request_hub(
                    method="GET",
                    url=f"{url}/{HUB_HARDWARE_TOKEN_ENDPOINT}",
                    failover_endpoint=None,
                    auth=auth,
                    timeout=timeout,
                )

                if token == self.hardwareToken:
                    self._reachable.type = "LAN"
                    self._reachable.next_check = datetime.now() + timedelta(days=1)
                    return True
                else:
                    self._reachable.type = "WAN"
                    self._reachable.next_check = datetime.now() + timedelta(days=1)
                    return False

            except aiohttp.ClientConnectionError as e:
                logger.debug(f"Installation {self.name} is unreachable by LAN: {e}")
                self._reachable.type = "WAN"
                self._reachable.next_check = datetime.now() + timedelta(days=1)
                return False
            except Exception as e:
                logger.debug(
                    f"Error checking connection for installation {self.name}: {e}"
                )
                self._reachable.type = "WAN"
                self._reachable.next_check = datetime.now() + timedelta(hours=1)
                return False

        else:
            return True if self._reachable.type == "LAN" else False


Elements.model_rebuild()
Installation.model_rebuild()
Device.model_rebuild()
