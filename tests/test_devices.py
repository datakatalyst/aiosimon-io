from unittest.mock import AsyncMock, patch

import pytest

from aiosimon_io.devices import Device
from aiosimon_io.installations import Installation


@pytest.fixture
def device():
    return Device(
        id="device1",
        name="Test Device",
        room="Living Room",
        roomId="room1",
        icon="icon.png",
        deviceInfo={
            "type": "switch",
            "subtype": "default",
            "manufacturerId": "manufacturer1",
            "serieId": "s200",
            "reference": "ref1",
            "upgradeDetails": {"firmwareVersion": "1.0.0"},
        },
        schedulers=None,
        multilevel=None,
        switch={"default": {"state": True}},
        socket=None,
        deviceConfigs=None,
        favoriteExperience=None,
        installation=AsyncMock(
            spec=Installation, id="installation_1", name="Test Installation"
        ),
    )


def test_get_type(device):
    """Test that the device type is correctly retrieved."""
    assert device.get_type() == "switch", "Device type should be 'switch'."


def test_get_subtype(device):
    """Test that the device subtype is correctly retrieved."""
    assert device.get_subtype() == "default", "Device subtype should be 'default'."


def test_get_device_type(device):
    """Test that the device type and subtype are correctly combined."""
    assert device.get_device_type() == "switch", "Device type should be 'switch'."

    device.deviceInfo["type"] = None
    device.deviceInfo["subtype"] = None
    assert (
        device.get_device_type() is None
    ), "Device type should be None when type and subtype are None."


def test_get_manufacturer(device):
    """Test that the manufacturer ID is correctly retrieved."""
    assert (
        device.get_manufacturer() == "manufacturer1"
    ), "Manufacturer ID should be 'manufacturer1'."


def test_get_serie(device):
    """Test that the series ID is correctly retrieved."""
    assert device.get_serie() == "s200", "Series ID should be 's200'."


def test_get_serie_name(device):
    """Test that the series name is correctly mapped from the series ID."""
    assert device.get_serie_name() == "Serie 270", "Series name should be 'Serie 270'."

    device.deviceInfo["serieId"] = "s100"
    assert device.get_serie_name() == "Serie 100", "Series name should be 'Serie 100'."

    device.deviceInfo["serieId"] = "other serie"
    assert (
        device.get_serie_name() is None
    ), "Series name should be None for unknown series ID."


def test_get_reference(device):
    """Test that the device reference is correctly retrieved."""
    assert device.get_reference() == "ref1", "Device reference should be 'ref1'."


def test_get_firmware_version(device):
    """Test that the firmware version is correctly retrieved."""
    assert (
        device.get_firmware_version() == "1.0.0"
    ), "Firmware version should be '1.0.0'."

    device.deviceInfo["upgradeDetails"] = None
    assert (
        device.get_firmware_version() is None
    ), "Firmware version should be None when upgrade details are missing."


def test_get_capabilities(device):
    """Test that the device capabilities are correctly retrieved."""
    assert device.get_capabilities() == [
        "onOff"
    ], "Capabilities should include 'onOff'."

    device.deviceInfo["type"] = None
    device.deviceInfo["subtype"] = None
    device.deviceInfo["serieId"] = None
    assert (
        device.get_capabilities() == []
    ), "Capabilities should be an empty list when type, subtype, and series ID are None."


def test_get_state(device):
    """Test that the device state is correctly retrieved."""
    assert device.get_state() is True, "Device state should be True."

    device.deviceInfo["type"] = "switch"
    device.deviceInfo["subtype"] = "custom"
    assert (
        device.get_state() is None
    ), "Device state should be None for unsupported subtype."

    device.deviceInfo["type"] = None
    device.deviceInfo["subtype"] = None
    assert (
        device.get_state() is None
    ), "Device state should be None when type and subtype are None."

    device.deviceInfo["type"] = "switch"
    device.deviceInfo["subtype"] = "default"
    device.switch = None
    with pytest.raises(ValueError, match="Not found 'switch' property for device"):
        device.get_state()

    del device.switch
    device.multilevel = {"default": {"state": True, "level": 50}}
    device.deviceInfo["type"] = "multilevel"
    device.deviceInfo["subtype"] = "default"
    assert (
        device.get_state() is True
    ), "Device state should be True for multilevel device."


def test_get_level(device):
    """Test that the device level is correctly retrieved."""
    assert (
        device.get_level() is None
    ), "Device level should be None for non-multilevel devices."

    del device.switch
    device.multilevel = {"default": {"state": True, "level": 50}}
    device.deviceInfo["type"] = "multilevel"
    device.deviceInfo["subtype"] = "default"
    assert device.get_level() == 50, "Device level should be 50."

    device.multilevel = {"default": {"state": True, "level": 50}}
    device.deviceInfo["type"] = None
    device.deviceInfo["subtype"] = None
    assert (
        device.get_level() is None
    ), "Device level should be None when type and subtype are None."

    device.multilevel = None
    device.deviceInfo["type"] = "multilevel"
    device.deviceInfo["subtype"] = "default"
    with pytest.raises(ValueError, match="Not found 'multilevel' property for device"):
        device.get_level()


def test_bulid_body():
    """Test that the body for device commands is correctly built."""
    body_state = Device._build_body("switch", "default", ["onOff"], state=True)
    assert body_state == {
        "switch": {"default": {"state": True}}
    }, "Body for switch state should match expected structure."

    body_level = Device._build_body("multilevel", "default", ["brightness"], level=50)
    assert body_level == {
        "multilevel": {"default": {"level": 50}}
    }, "Body for multilevel level should match expected structure."

    with pytest.raises(
        ValueError, match="Device type: 'wrong_type' and subtype: 'wrong_subtype'"
    ):
        Device._build_body("wrong_type", "wrong_subtype", [])


@pytest.mark.asyncio
async def test_async_set_state(device, caplog):
    """Test that the device state is correctly set asynchronously."""
    with patch(
        "aiosimon_io.devices.Device._build_body",
        return_value={"switch": {"default": {"state": False}}},
    ):
        device.installation._async_request_switcher.return_value = {
            "switch": {"default": {"state": False}},
            "extra_field": "value",
        }
        await device.async_set_state(False)

        Device._build_body.assert_called_once_with(
            "switch", "default", ["onOff"], state=False
        )
        device.installation._async_request_switcher.assert_called_once()
        assert (
            device.switch["default"]["state"] is False
        ), "Device state should be updated to False."
        assert (
            "Attribute 'extra_field' does not exist in the Device class. Ignoring it."
            in caplog.text
        )

        with pytest.raises(Exception):
            device.installation._async_request_switcher.side_effect = Exception()
            await device.async_set_state(False)
            assert "Error setting state to device" in caplog.text

    device.deviceInfo["type"] = None
    device.deviceInfo["subtype"] = None
    with pytest.raises(ValueError, match="Device type or subtype is not defined."):
        await device.async_set_state(False)


@pytest.mark.asyncio
async def test_async_set_level(device, caplog):
    """Test that the device level is correctly set asynchronously."""
    device.deviceInfo["type"] = "multilevel"
    device.deviceInfo["subtype"] = "default"
    device.multilevel = {"default": {"state": False, "level": 10}}
    del device.switch

    with patch(
        "aiosimon_io.devices.Device._build_body",
        return_value={"multilevel": {"default": {"level": 50}}},
    ):
        device.installation._async_request_switcher.return_value = {
            "multilevel": {"default": {"state": True, "level": 50}},
            "extra_field": "value",
        }
        await device.async_set_level(50)

        Device._build_body.assert_called_once_with(
            "multilevel", "default", ["onOff", "brightness"], level=50
        )
        device.installation._async_request_switcher.assert_called_once()
        assert (
            device.multilevel["default"]["level"] == 50
        ), "Device level should be updated to 50."
        assert (
            device.multilevel["default"]["state"] is True
        ), "Device state should be updated to True."
        assert (
            "Attribute 'extra_field' does not exist in the Device class. Ignoring it."
            in caplog.text
        )

        with pytest.raises(Exception):
            device.installation._async_request_switcher.side_effect = Exception()
            await device.async_set_level(50)
            assert "Error setting level to device" in caplog.text

    device.deviceInfo["type"] = None
    device.deviceInfo["subtype"] = None
    with pytest.raises(ValueError, match="Device type or subtype is not defined."):
        await device.async_set_level(50)


@pytest.mark.asyncio
async def test_async_refresh(device):
    """Test that the device is correctly refreshed asynchronously."""
    device.installation.async_get_device.return_value = device

    refreshed_device = await device.async_refresh()

    device.installation.async_get_device.assert_called_once_with(device.id)
    assert (
        refreshed_device == device
    ), "Refreshed device should match the original device."
