import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from aiosimon_io.auth import SimonAuth
from aiosimon_io.devices import Device
from aiosimon_io.installations import Elements, Installation

# Mock data for a sample installation
MOCK_INSTALLATION = {
    "id": "installation_1",
    "name": "Test Installation",
    "icon": "test_icon",
    "mode": "managed",
    "status": "up",
    "username": "test_user",
    "password": "dGVzdF9wYXNzd29yZA==",
    "lanIp": "192.168.1.20",
    "port": 8000,
    "hardwareToken": "test_hardware_token",
    "elements": Elements(),
}

# Mock data for sample devices
MOCK_DEVICES = [
    {
        "id": "wifi-2_1",
        "name": "Switch01",
        "deviceInfo": {"type": "switch", "subtype": "default"},
        "switch": {"default": {"state": False}},
        "wrong_key": "should be ignored",
    },
    {
        "id": "wifi-1_1",
        "name": "Dimmer01",
        "deviceInfo": {"type": "multilevel", "subtype": "default"},
        "switch": {
            "default": {
                "isCalibrated": True,
                "level": 50.0,
                "state": True,
            }
        },
    },
]


@pytest.fixture
def installation():
    """
    Provides an instance of Installation with a mocked _api_client.
    """
    return Installation(
        id="installation_1",
        name="Test Installation",
        icon="test_icon",
        mode="managed",
        status="up",
        username="test_user",
        password="dGVzdF9wYXNzd29yZA==",
        lanIp="192.168.1.20",
        port=8000,
        hardwareToken="test_hardware_token",
        elements=Elements(),
        _api_client=AsyncMock(spec=SimonAuth),
    )


@pytest.mark.asyncio
async def test_async_get_installations():
    """
    Test the async_get_installations method to fetch a list of installations.
    """
    client = AsyncMock(spec=SimonAuth)
    # Mock the async_request method to return a list of installations
    with patch.object(
        client, "async_request", new_callable=AsyncMock
    ) as mock_async_request:
        mock_async_request.return_value = [MOCK_INSTALLATION]

        # Test fetching installations without TTL
        installations = await Installation.async_get_installations(client)
        assert len(installations) == 1, "Expected exactly one installation"
        assert installations[0].id == "installation_1", "Installation ID does not match"
        assert (
            installations[0].name == "Test Installation"
        ), "Installation name does not match"

        # Test fetching installations with TTL
        installations = await Installation.async_get_installations(client, ttl=10)
        assert installations[0]._ttl == 10, "TTL value does not match"


@pytest.mark.asyncio
async def test_async_get_installation():
    """
    Test the async_get_installation method to fetch a single installation.
    """
    client = AsyncMock(spec=SimonAuth)
    # Mock the async_request method to return a single installation
    with patch.object(
        client, "async_request", new_callable=AsyncMock
    ) as mock_async_request:
        mock_async_request.return_value = MOCK_INSTALLATION

        # Test fetching a single installation without TTL
        installation = await Installation.async_get_installation(
            client, "installation_1"
        )
        assert installation.id == "installation_1", "Installation ID does not match"
        assert (
            installation.name == "Test Installation"
        ), "Installation name does not match"

        # Test fetching a single installation with TTL
        installation = await Installation.async_get_installation(
            client, "installation_1", ttl=10
        )
        assert installation._ttl == 10, "TTL value does not match"


@pytest.mark.asyncio
async def test_async_get_devices(installation):
    """
    Test the async_get_devices method to fetch devices from an installation.
    """
    # Mock the async_request method to return devices
    with patch.object(
        installation._api_client, "async_request", new_callable=AsyncMock
    ) as mock_async_request:
        mock_async_request.return_value = {"devices": MOCK_DEVICES}

        # Test fetching devices
        devices = await installation.async_get_devices()
        assert len(devices) == 2, "Expected exactly two devices"
        assert "wifi-2_1" in devices, "Device 'wifi-2_1' not found"
        assert (
            devices["wifi-2_1"].name == "Switch01"
        ), "Device name for 'wifi-2_1' does not match"
        assert "wifi-1_1" in devices, "Device 'wifi-1_1' not found"
        assert (
            devices["wifi-1_1"].name == "Dimmer01"
        ), "Device name for 'wifi-1_1' does not match"


@pytest.mark.asyncio
async def test_async_get_device(installation):
    """
    Test the async_get_device method to fetch a single device by ID.
    """
    # Mock the async_request method to return devices
    with patch.object(
        installation._api_client, "async_request", new_callable=AsyncMock
    ) as mock_async_request:
        mock_async_request.return_value = {"devices": MOCK_DEVICES}

        # Test fetching a single device
        device = await installation.async_get_device("wifi-2_1")
        assert device.name == "Switch01", "Device name does not match"


def test_get_local_base_url(installation):
    """
    Test the _get_local_base_url method to generate the local base URL.
    """
    # Test generating the local base URL
    base_url = installation._get_local_base_url()
    assert base_url == "http://192.168.1.20:8000", "Base URL does not match"

    # Test missing lanIp
    with pytest.raises(ValueError):
        installation.lanIp = None
        installation._get_local_base_url()

    # Test missing port
    with pytest.raises(ValueError):
        installation.port = None
        installation._get_local_base_url()

    # Test invalid mode
    with pytest.raises(ValueError):
        installation.mode = "virtual"
        installation._get_local_base_url()


def test_get_local_basic_auth(installation):
    """
    Test the _get_local_basic_auth method to generate basic authentication credentials.
    """
    # Test generating basic auth credentials
    auth = installation._get_local_basic_auth()
    assert isinstance(
        auth, aiohttp.BasicAuth
    ), "Auth object is not of type aiohttp.BasicAuth"
    assert auth == aiohttp.BasicAuth(
        "test_user", "test_password"
    ), "Auth credentials do not match"

    # Test wrong installation mode
    with pytest.raises(
        ValueError, match="Basic Auth is only available for 'managed' installations."
    ):
        installation.mode = "virtual"
        installation._get_local_basic_auth()

    # Test missing username
    with pytest.raises(
        ValueError, match="Invalid username or password for installation"
    ):
        installation.mode = "managed"
        installation.username = None
        installation.password = "dGVzdF9wYXNzd29yZA=="
        installation._get_local_basic_auth()

    # Test missing password
    with pytest.raises(
        ValueError, match="Invalid username or password for installation"
    ):
        installation.mode = "managed"
        installation.username = "test_user"
        installation.password = None
        installation._get_local_basic_auth()

    with pytest.raises(
        ValueError, match="Error getting Basic Auth credentials for installation"
    ):
        installation.mode = "managed"
        installation.username = "test_user"
        installation.password = "wrong_password"
        installation._get_local_basic_auth()


def test_refresh(installation):
    """
    Test the _refresh method to determine if a refresh is needed.
    """
    # Test refresh logic when refresh is not needed
    installation._refresh_after = datetime.now() + timedelta(seconds=10)
    refresh = installation._refresh()
    assert refresh is False, "Refresh should not be needed"

    # Test refresh logic when refresh is needed
    installation._refresh_after = datetime.now() - timedelta(seconds=10)
    refresh = installation._refresh()
    assert refresh is True, "Refresh should be needed"

    # Test refresh logic when _refresh_after is None
    installation._refresh_after = None
    refresh = installation._refresh()
    assert refresh is True, "Refresh should be needed when _refresh_after is None"


@pytest.mark.asyncio
async def test_fetch_elements_from_origin_waits_for_ongoing_fetch(installation):
    """
    Test the _fetch_elements_from_origin method to ensure it waits for ongoing fetch operations.
    """
    installation._refresh_future = asyncio.Future()
    with patch.object(installation, "_fetch_lock", new=AsyncMock()):
        fetch_task = asyncio.create_task(installation._fetch_elements_from_origin())
        assert not fetch_task.done(), "Fetch task should not be done while waiting"
        installation._refresh_future.set_result(None)
        await fetch_task
        assert fetch_task.done(), "Fetch task should be completed"


@pytest.mark.asyncio
async def test_fetch_elements_from_origin_cached(installation):
    """
    Test the _fetch_elements_from_origin method when data is cached.
    """
    installation._refresh_after = datetime.now() + timedelta(seconds=10)
    with patch.object(installation, "_fetch_lock", new=AsyncMock()), patch.object(
        installation, "_refresh", return_value=False
    ) as mock_refresh, patch.object(
        installation, "_async_request_switcher", new_callable=AsyncMock
    ) as mock_request:
        await installation._fetch_elements_from_origin()
        mock_refresh.assert_called_once(), "Refresh should be called once"
        (
            mock_request.assert_not_called(),
            "Request should not be made when data is cached",
        )


@pytest.mark.asyncio
async def test_fetch_elements_from_origin(installation):
    """
    Test the _fetch_elements_from_origin method to fetch and update devices.
    """
    installation._refresh_future = None
    installation.elements.devices["wifi-7_1"] = Device(
        id="wifi-7_1",
        name="Switch07",
        deviceInfo={},
        switch={},
        installation=installation,
    )
    installation.elements.devices["wifi-2_1"] = Device(
        id="wifi-2_1",
        name="BadNameSwitch02",
        deviceInfo={},
        switch={},
        installation=installation,
    )

    with patch.object(installation, "_fetch_lock", new=AsyncMock()), patch.object(
        installation, "_refresh", return_value=True
    ) as mock_refresh, patch.object(
        installation, "_async_request_switcher", new_callable=AsyncMock
    ) as mock_request:

        mock_request.return_value = {"devices": MOCK_DEVICES}
        await installation._fetch_elements_from_origin()

        assert len(installation.elements.devices) == 2, "Device count should be 2"
        assert (
            "wifi-7_1" not in installation.elements.devices
        ), "Device 'wifi-7_1' should be present"
        assert (
            installation.elements.devices["wifi-2_1"].name == "Switch01"
        ), "Device name for 'wifi-2_1' does not match"
        assert (
            installation.elements.devices["wifi-1_1"].name == "Dimmer01"
        ), "Device name for 'wifi-1_1' does not match"
        mock_refresh.assert_called_once()
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_elements_from_origin_exception(installation):
    """
    Test the _fetch_elements_from_origin method to handle exceptions during fetch.
    """
    installation._refresh_future = None

    with patch.object(installation, "_fetch_lock", new=AsyncMock()), patch.object(
        installation, "_refresh", return_value=True
    ), patch.object(
        installation, "_async_request_switcher", new_callable=AsyncMock
    ) as mock_request:

        mock_request.side_effect = Exception("Test exception")
        with pytest.raises(Exception):
            await installation._fetch_elements_from_origin()


@pytest.mark.asyncio
async def test_async_request_switcher(installation):
    """
    Test the _async_request_switcher method to switch between LAN and WAN requests.
    """
    # Test request switcher for LAN
    with patch.object(
        installation, "_async_reachable_by_lan", return_value=True
    ), patch.object(
        installation._api_client, "async_request_hub", new_callable=AsyncMock
    ) as mock_request_hub:

        mock_request_hub.return_value = {"devices": MOCK_DEVICES}
        response = await installation._async_request_switcher(
            "GET", "local_path", "sns_path"
        )
        assert response == {
            "devices": MOCK_DEVICES
        }, "Response for LAN request does not match expected value"

    # Test request switcher for WAN
    with patch.object(
        installation, "_async_reachable_by_lan", return_value=False
    ), patch.object(
        installation._api_client, "async_request", new_callable=AsyncMock
    ) as mock_request:

        mock_request.return_value = {"devices": MOCK_DEVICES}
        response = await installation._async_request_switcher(
            "GET", "local_path", "sns_path"
        )
        assert response == {
            "devices": MOCK_DEVICES
        }, "Response for WAN request does not match expected value"


@pytest.mark.asyncio
async def test_async_reachable_by_lan(installation):
    """
    Test the _async_reachable_by_lan method to check LAN reachability.
    """
    # Test LAN reachability in virtual mode
    installation.mode = "virtual"
    reachable = await installation._async_reachable_by_lan()
    assert reachable is False, "LAN should not be reachable in virtual mode"

    # Test LAN reachability when already reachable
    installation.mode = "managed"
    installation._reachable.next_check = datetime.now() + timedelta(seconds=10)
    installation._reachable.type = "LAN"
    reachable = await installation._async_reachable_by_lan()
    assert (
        reachable is True
    ), "LAN should be reachable when type is 'LAN' and next_check is in the future"

    # Test LAN reachability when type is WAN
    installation._reachable.type = "WAN"
    reachable = await installation._async_reachable_by_lan()
    assert (
        reachable is False
    ), "LAN should not be reachable when type is 'WAN' and next_check is in the future"

    # Test LAN reachability with API client
    with patch.object(
        installation._api_client, "async_request_hub", new_callable=AsyncMock
    ) as mock_request:
        # Test valid hardware token
        installation._reachable.type = "WAN"
        installation._reachable.next_check = datetime.now() - timedelta(seconds=10)
        mock_request.return_value = "test_hardware_token"
        reachable = await installation._async_reachable_by_lan()
        assert reachable is True, "LAN should be reachable when hardware token matches"
        assert (
            installation._reachable.type == "LAN"
        ), "Reachable type should be updated to 'LAN'"

        # Test invalid hardware token
        installation._reachable.type = "LAN"
        installation._reachable.next_check = datetime.now() - timedelta(seconds=10)
        mock_request.return_value = "wrong_hardware_token"
        reachable = await installation._async_reachable_by_lan()
        assert (
            reachable is False
        ), "LAN should not be reachable with an invalid hardware token"
        assert (
            installation._reachable.type == "WAN"
        ), "Reachable type should be updated to 'WAN'"

        # Test connection error
        installation._reachable.type = "LAN"
        installation._reachable.next_check = datetime.now() - timedelta(seconds=10)
        mock_request.side_effect = aiohttp.ClientConnectionError()
        reachable = await installation._async_reachable_by_lan()
        assert reachable is False, "LAN should not be reachable on connection error"
        assert (
            installation._reachable.type == "WAN"
        ), "Reachable type should be updated to 'WAN' on connection error"

        # Test generic exception
        installation._reachable.type = "LAN"
        installation._reachable.next_check = datetime.now() - timedelta(seconds=10)
        mock_request.side_effect = Exception()
        reachable = await installation._async_reachable_by_lan()
        assert reachable is False, "LAN should not be reachable on generic exception"
        assert (
            installation._reachable.type == "WAN"
        ), "Reachable type should be updated to 'WAN' on generic exception"
