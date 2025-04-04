from unittest.mock import AsyncMock, patch

import pytest

from aiosimon_io.auth import SimonAuth
from aiosimon_io.users import User

# Mock data representing the current user response from the API
MOCK_CURRENT_USER = {
    "id": "user_id",
    "name": "Test User",
    "email": "test@email.com",
    "isBlocked": False,
    "country": "ES",
    "gdprRegion": "EU",
}


@pytest.mark.asyncio
async def test_get_current_user():
    """
    Tests that the async_get_current_user method retrieves the correct user data.
    """
    client = AsyncMock(spec=SimonAuth)
    # Mock the async_request method of the client to return the mock user data
    with patch.object(
        client, "async_request", new_callable=AsyncMock
    ) as mock_async_request:
        mock_async_request.return_value = MOCK_CURRENT_USER

        # Call the method under test
        user_info = await User.async_get_current_user(client)

        # Verify the returned user data matches the mock data
        assert user_info.id == "user_id", "User ID does not match"
        assert user_info.name == "Test User", "User name does not match"
        assert user_info.lastName is None, "User lastName should be None"
        assert user_info.email == "test@email.com", "User email does not match"
        assert user_info.isBlocked is False, "User isBlocked status does not match"
        assert user_info.country == "ES", "User country does not match"
        assert user_info.gdprRegion == "EU", "User GDPR region does not match"

        # Verify the mock method was called with the correct parameters
        mock_async_request.assert_called_once_with("GET", "api/v1/users")

        # Additional assertion to ensure the mock response structure is correct
        assert isinstance(
            mock_async_request.return_value, dict
        ), "Mock response should be a dictionary"
