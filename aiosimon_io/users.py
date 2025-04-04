# aiosimon_io/users.py
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
Module for managing users in the Simon iO system.

This module provides the `User` class, which represents a user in the Simon iO system,
and includes methods for retrieving user information.
"""

from __future__ import annotations

import logging
from typing import ClassVar, Optional

from pydantic import BaseModel

from .auth import AbstractAuth
from .const import USER_ENDPOINT

logger = logging.getLogger(__name__)


class User(BaseModel):
    """Represents a user in the Simon iO system.

    :canonical: aiosimon_io.users.User
    """

    endpoint: ClassVar[str] = USER_ENDPOINT
    api_client: ClassVar[AbstractAuth]

    id: str
    name: Optional[str] = None
    lastName: Optional[str] = None
    email: str
    isBlocked: bool
    country: Optional[str] = None
    gdprRegion: Optional[str] = None

    @classmethod
    async def async_get_current_user(cls, api_client: AbstractAuth) -> User:
        """Retrieve the current authenticated user asynchronously."""
        logger.debug("Getting current authenticated user")
        cls.api_client = api_client
        response: dict = await cls.api_client.async_request("GET", cls.endpoint)
        return cls(**response)
