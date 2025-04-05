# aiosimon_io/devices.py
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
Module for managing devices in the Simon iO system.

This module provides the `Device` class, which represents a device in the Simon iO system,
and includes methods for retrieving and updating device information, as well as controlling
device states and levels.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, List, Optional, Union

from pydantic import BaseModel

from .const import HUB_DEVICES_ENDPOINT, SNS_DEVICES_ENDPOINT

if TYPE_CHECKING:
    from aiosimon_io.installations import Installation  # pragma: no cover

logger = logging.getLogger(__name__)


class Device(BaseModel):
    """Represents a device in the Simon iO system.

    :canonical: aiosimon_io.devices.Device
    """

    _hub_devices_endpoint: ClassVar[str] = HUB_DEVICES_ENDPOINT
    _sns_devices_endpoint: ClassVar[str] = SNS_DEVICES_ENDPOINT

    id: str
    name: str
    room: Optional[str] = None
    roomId: Optional[str] = None
    icon: Optional[str] = None
    deviceInfo: dict
    schedulers: Optional[List[dict]] = None
    multilevel: Optional[dict] = None
    switch: Optional[dict] = None
    socket: Optional[dict] = None
    deviceConfigs: Optional[dict] = None
    favoriteExperience: Optional[int] = None
    installation: "Installation"

    def get_type(self) -> Optional[str]:
        """
        Get the type of the device.

        Returns:
            Optional[str]: The type of the device, or None if not available.
        """
        return self.deviceInfo.get("type", None)

    def get_subtype(self) -> Optional[str]:
        """
        Get the subtype of the device.

        Returns:
            Optional[str]: The subtype of the device, or None if not available.
        """
        return self.deviceInfo.get("subtype", None)

    def get_device_type(self) -> Optional[str]:
        """
        Get the device type based on its type and subtype.

        Returns:
            Optional[str]: The device type, or None if not available.
        """
        type_map = {
            ("socket", "default"): "outlet",
            ("socket", "gateway"): "outlet",
            ("switch", "default"): "switch",
            ("switch", "custom"): "button",
            ("switch", "multimaster"): "button",
            ("multilevel", "default"): "light",
            ("multilevel", "blinds"): "blinds",
        }

        device_type = self.get_type()
        device_subtype = self.get_subtype()

        if device_type is None or device_subtype is None:
            return None

        return type_map.get((device_type, device_subtype), None)

    def get_manufacturer(self) -> Optional[str]:
        """
        Get the manufacturer of the device.

        Returns:
            Optional[str]: The manufacturer ID, or None if not available.
        """
        return self.deviceInfo.get("manufacturerId", None)

    def get_serie(self) -> Optional[str]:
        """
        Get the series ID of the device.

        Returns:
            Optional[str]: The series ID, or None if not available.
        """
        return self.deviceInfo.get("serieId", None)

    def get_serie_name(self) -> Optional[str]:
        """
        Get the series name of the device.

        Returns:
            Optional[str]: The series name, or None if not available.
        """
        if self.deviceInfo.get("serieId") == "s100":
            return "Serie 100"
        elif self.deviceInfo.get("serieId") == "s200":
            return "Serie 270"
        else:
            return None

    def get_reference(self) -> Optional[str]:
        """
        Get the reference of the device.

        Returns:
            Optional[str]: The reference, or None if not available.
        """
        return self.deviceInfo.get("reference", None)

    def get_firmware_version(self) -> Optional[str]:
        """
        Get the firmware version of the device.

        Returns:
            Optional[str]: The firmware version, or None if not available.
        """
        upgrade_details = self.deviceInfo.get("upgradeDetails")
        if upgrade_details is None:
            return None
        return upgrade_details.get("firmwareVersion", None)

    def get_capabilities(self) -> List[str]:
        """
        Get the capabilities of the device.

        Returns:
            List[str]: A list of capabilities supported by the device.
        """
        capability_map = {
            ("socket", "gateway", "s100"): [
                "onOff",
                "courtesyLight",
                "powerLimit",
                "inputBlock",
                "recoverStatus",
                "locator",
                "ledInRepose",
                "timmers",
                "locator",
                "resetFactory",
            ],
            ("socket", "default", "s200"): ["onOff"],
            ("switch", "default", "s200"): ["onOff"],
            ("switch", "custom", "s200"): [],
            ("switch", "multimaster", "s200"): [],
            ("multilevel", "default", "s200"): ["onOff", "brightness"],
            ("multilevel", "blinds", "s200"): ["openClose"],
        }

        device_type = self.get_type()
        device_subtype = self.get_subtype()
        device_serie = self.get_serie()

        if device_type is None or device_subtype is None or device_serie is None:
            return []

        return capability_map.get((device_type, device_subtype, device_serie), [])

    def get_state(self) -> Optional[bool]:
        """
        Get the current state of the device (on/off).

        Returns:
            Optional[bool]: The state of the device, or None if not available.

        Raises:
            ValueError: If the device type property is not found.
        """
        device_type = self.get_type()
        device_subtype = self.get_subtype()

        if (
            device_type is None
            or device_subtype is None
            or "onOff" not in self.get_capabilities()
        ):
            return None

        data = getattr(self, device_type, None)
        if not data:
            raise ValueError(
                f"Not found '{device_type}' property for device {self.name}."
            )

        return data.get(device_subtype, {}).get("state")

    def get_level(self) -> Optional[int]:
        """
        Get the level of the device (e.g., dimmer level).

        Returns:
            Optional[int]: The level of the device, or None if not available.

        Raises:
            ValueError: If the device type property is not found.
        """
        device_type = self.get_type()
        device_subtype = self.get_subtype()

        if (
            device_type is None
            or device_subtype is None
            or not set(self.get_capabilities()).intersection(
                ["brightness", "openClose"]
            )
        ):
            return None

        data = getattr(self, device_type, None)
        if not data:
            raise ValueError(
                f"Not found '{device_type}' property for device {self.name}."
            )

        return data.get(device_subtype, {}).get("level")

    async def async_set_state(self, state: bool) -> None:
        """
        Set the state of the device (on/off) asynchronously.

        Args:
            state (bool): The desired state of the device.

        Raises:
            ValueError: If the device type or subtype is not defined.
            Exception: If an error occurs while setting the state.
        """
        logger.debug(f"Setting state to device '{self.name}': {state}")
        device_type = self.get_type()
        device_subtype = self.get_subtype()
        if device_type is None or device_subtype is None:
            raise ValueError("Device type or subtype is not defined.")

        body: dict = self._build_body(
            device_type, device_subtype, self.get_capabilities(), state=state
        )

        try:
            local_path = f"{self._hub_devices_endpoint}/{self.id}"
            sns_path = f"{self._sns_devices_endpoint.format(installation_id=self.installation.id)}/{self.id}"
            response: dict = await self.installation._async_request_switcher(
                "PATCH", local_path, sns_path, json=body
            )

            for key, value in response.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    logger.warning(
                        f"Attribute '{key}' does not exist in the Device class. Ignoring it."
                    )
        except Exception as e:
            logger.error(f"Error setting state to device '{self.name}': {e}")
            raise

    async def async_set_level(self, level: int) -> None:
        """
        Set the level of the device (e.g., dimmer level) asynchronously.

        Args:
            level (int): The desired level of the device.

        Raises:
            ValueError: If the device type or subtype is not defined.
            Exception: If an error occurs while setting the level.
        """
        logger.debug(f"Setting level to device '{self.name}': {level}")
        device_type = self.get_type()
        device_subtype = self.get_subtype()
        if device_type is None or device_subtype is None:
            raise ValueError("Device type or subtype is not defined.")

        body: dict = self._build_body(
            device_type, device_subtype, self.get_capabilities(), level=level
        )

        try:
            local_path = f"{self._hub_devices_endpoint}/{self.id}"
            sns_path = f"{self._sns_devices_endpoint.format(installation_id=self.installation.id)}/{self.id}"
            response: dict = await self.installation._async_request_switcher(
                "PATCH", local_path, sns_path, json=body
            )

            for key, value in response.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    logger.warning(
                        f"Attribute '{key}' does not exist in the Device class. Ignoring it."
                    )
        except Exception as e:
            logger.error(f"Error setting level to device {self.name}: {e}")
            raise

    async def async_refresh(self) -> Optional[Device]:
        """
        Update the device asynchronously.

        Returns:
            Optional[Device]: The updated device instance, or None if not available.
        """
        return await self.installation.async_get_device(self.id)

    @staticmethod
    def _build_body(
        device_type: str,
        device_subtype: str,
        device_capabilities: List[str],
        state: Optional[bool] = None,
        level: Optional[int] = None,
    ) -> dict:
        """
        Build the request body for setting the state or level of the device.

        Args:
            device_type (str): The type of the device.
            device_subtype (str): The subtype of the device.
            device_capabilities (List[str]): The capabilities of the device.
            state (Optional[bool]): The desired state of the device.
            level (Optional[int]): The desired level of the device.

        Returns:
            dict: The request body.

        Raises:
            ValueError: If the requested operation is not supported by the device.
        """
        data: dict[str, Union[bool, int]] = {}

        if state is not None and "onOff" in device_capabilities:
            data["state"] = state
        if level is not None and set(device_capabilities).intersection(
            ["brightness", "openClose"]
        ):
            data["level"] = level

        if data == {}:
            raise ValueError(
                f"Device "
                f"type: '{device_type}' and subtype: '{device_subtype}'"
                f" with capabilities {device_capabilities}"
                f" does not support the requested operation: "
                f"{'state' if state is not None else ''}"
                f"{' and ' if state is not None and level is not None else ''}"
                f"{'level' if level is not None else ''}"
            )

        return {device_type: {device_subtype: data}}
