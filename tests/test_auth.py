import datetime
from unittest.mock import patch

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from aiosimon_io.auth import SimonAuth

# URL for obtaining OAuth tokens
AUTH_URL = "https://auth.simon-cloud.com/oauth/v2/token"

# Base URL for SNS API
SNS_BASE_URL = "https://sns.simon-cloud.com"

# Mock URL for hub health-check endpoint
MOCK_HUB_URL = "http://192.168.1.20:8000/api/v1/installation/health-check"

# Mock basic authentication credentials
MOCK_BASIC_AUTH = aiohttp.BasicAuth("admin", "password")

# Mock response for token retrieval
MOCK_TOKEN_RESPONSE = {
    "access_token": "test_access_token",
    "expires_in": 3600,
    "refresh_token": "test_refresh_token",
    "token_type": "Bearer",
}

# Test scenarios for SNS requests
SNS_TEST_SCENARIOS = [
    ("success", 200, {"key": "value"}, None),
    ("unauthorized", 401, None, Exception),
    ("unauthorized", 500, None, Exception),
]

# Exception scenarios for SNS requests
SNS_EXCEPTION_SCENARIOS = [
    (
        "client_connection_error",
        aiohttp.ClientConnectionError,
        "Simulated client connection error",
    ),
    ("client_error", aiohttp.ClientError, "Simulated client error"),
    ("unexpected_error", Exception, "Simulated unexpected error"),
]

# Test scenarios for hub requests
HUB_TEST_SCENARIOS = [
    # (scenario, hub_code, hub_payload, hub_exception, sns_code, sns_payload, sns_exception)
    ("success", 200, {"msg": "OK"}, None, None, None, None),
    (
        "sns_failover",
        401,
        None,
        aiohttp.ClientResponseError,
        200,
        {"origin": "sns", "msg": "OK"},
        None,
    ),
    (
        "sns_failver_error",
        500,
        None,
        aiohttp.ClientResponseError,
        500,
        {"origin": "sns", "msg": "Error"},
        Exception,
    ),
]

# Exception scenarios for hub requests
HUB_EXCEPTION_SCENARIOS = [
    ("timeout_error", aiohttp.ServerTimeoutError, "Timeout error"),
    ("connection_error", aiohttp.ClientConnectionError, "Connection refused"),
    ("client_error", aiohttp.ClientError, "Generic client error"),
    ("unexpected_error", Exception, "Unexpected error"),
]


def assert_token_response(auth, access_token, refresh_token=None):
    """
    Assert that the token response matches the expected values.

    :param auth: SimonAuth instance
    :param access_token: Expected access token
    :param refresh_token: Expected refresh token (optional)
    """
    assert (
        auth.access_token == access_token
    ), f"Expected access_token '{access_token}', got '{auth.access_token}'"
    if refresh_token:
        assert (
            auth.refresh_token == refresh_token
        ), f"Expected refresh_token '{refresh_token}', got '{auth.refresh_token}'"
    assert isinstance(
        auth.token_expires_at, datetime.datetime
    ), "token_expires_at is not a datetime object"
    assert (
        auth.token_expires_at > datetime.datetime.now()
    ), "token_expires_at is not in the future"


@pytest_asyncio.fixture
async def auth():
    """
    Fixture to provide a SimonAuth instance with mock credentials.
    """
    async with aiohttp.ClientSession() as session:
        yield SimonAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            username="test_username",
            password="test_password",
            session=session,
        )


@pytest.mark.asyncio
async def test_get_access_token(auth):
    """
    Test successful retrieval of an access token.
    """
    with aioresponses() as mocked:
        mocked.post(AUTH_URL, payload=MOCK_TOKEN_RESPONSE)
        token = await auth.async_get_access_token()

        assert (
            token == "test_access_token"
        ), f"Expected token 'test_access_token', got '{token}'"
        assert_token_response(auth, "test_access_token", "test_refresh_token")


@pytest.mark.asyncio
async def test_get_access_token_error(auth):
    """
    Test error handling when access token retrieval fails.
    """
    with aioresponses() as mocked:
        mocked.post(AUTH_URL, status=401)
        with pytest.raises(Exception):
            await auth.async_get_access_token()

    with aioresponses() as mocked:
        mocked.post(AUTH_URL, payload={})
        with pytest.raises(ValueError, match="No access token available."):
            await auth.async_get_access_token()


@pytest.mark.asyncio
async def test_refresh_access_token(auth):
    """
    Test successful refresh of an access token.
    """
    new_token_response = {
        **MOCK_TOKEN_RESPONSE,
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
    }

    with aioresponses() as mocked:
        # First call to get the initial token
        mocked.post(AUTH_URL, payload=MOCK_TOKEN_RESPONSE)
        token = await auth.async_get_access_token()
        assert (
            token == "test_access_token"
        ), f"Expected token 'test_access_token', got '{token}'"

        # Simulate that the token has expired
        auth.token_expires_at = datetime.datetime.now() - datetime.timedelta(seconds=10)

        # Second call to refresh the token
        mocked.post(AUTH_URL, payload=new_token_response)
        token = await auth.async_get_access_token()

        assert (
            token == "new_access_token"
        ), f"Expected token 'new_access_token', got '{token}'"
        assert_token_response(auth, "new_access_token", "new_refresh_token")


@pytest.mark.asyncio
async def test_refresh_access_token_error(auth):
    """
    Test error handling when access token refresh fails.
    """
    auth.refresh_token = "test_refresh_token"
    with aioresponses() as mocked:
        mocked.post(AUTH_URL, status=500)
        with pytest.raises(Exception):
            await auth.async_refresh_access_token()


@pytest.mark.asyncio
async def test_refresh_access_token_no_refresh_token(auth):
    """
    Test error handling when no refresh token is available.
    """
    auth.refresh_token = None
    with pytest.raises(ValueError, match="No refresh token available."):
        await auth.async_refresh_access_token()


@pytest.mark.asyncio
async def test_parse_expires_in(auth):
    """
    Test parsing of expires_in value.
    """
    # Test case where expires_in is greater than 500
    expires_in = 3600
    expected_expiration = datetime.datetime.now() + datetime.timedelta(
        seconds=expires_in - 500
    )
    actual_expiration = auth._parse_expires_in(expires_in)
    assert (
        abs((expected_expiration - actual_expiration).total_seconds()) < 1
    ), "Expiration time mismatch"

    # Test case where expires_in is less than or equal to 500
    expires_in = 300
    expected_expiration = datetime.datetime.now() + datetime.timedelta(
        seconds=expires_in
    )
    actual_expiration = auth._parse_expires_in(expires_in)
    assert (
        abs((expected_expiration - actual_expiration).total_seconds()) < 1
    ), "Expiration time mismatch"

    # Test case where expires_in is None
    with pytest.raises(ValueError):
        auth._parse_expires_in(None)


@pytest.mark.asyncio
async def test_is_token_expired(auth):
    """
    Test token expiration check.
    """
    auth.refresh_token = "test_refresh_token"
    auth.token_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=10)
    assert not auth._is_token_expired(), "Token should not be expired"

    auth.token_expires_at = datetime.datetime.now() - datetime.timedelta(seconds=10)
    assert auth._is_token_expired(), "Token should be expired"

    with pytest.raises(ValueError):
        auth.token_expires_at = None
        auth._is_token_expired()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,status,payload,expected_exception", SNS_TEST_SCENARIOS
)
async def test_make_sns_request_scenarios(
    auth: SimonAuth,
    scenario: str,
    status: int,
    payload: dict,
    expected_exception: Exception,
):
    """
    Test various scenarios for making SNS requests.
    """
    with patch.object(
        auth, "async_get_access_token", return_value="access_token"
    ), patch.object(
        auth, "async_refresh_access_token", return_value="new_access_token"
    ), aioresponses() as mocked:

        url = f"{SNS_BASE_URL}/test_endpoint"
        mocked.get(
            url,
            status=status,
            payload=payload or {"error": "test error"},
            headers={
                "Authorization": "Bearer mock_access_token",
                "Content-Type": "application/json",
            },
        )

        if expected_exception:
            with pytest.raises(expected_exception):
                await auth.async_request("GET", "test_endpoint")
        else:
            response = await auth.async_request("GET", "test_endpoint")
            assert (
                response == payload
            ), f"Expected payload '{payload}', got '{response}'"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,exception_class,error_message", SNS_EXCEPTION_SCENARIOS
)
async def test_make_sns_request_errors(
    auth: SimonAuth, scenario: str, exception_class: Exception, error_message: str
):
    """
    Test error handling for SNS requests.
    """
    with patch.object(auth, "async_get_access_token", return_value="access_token"):
        with patch.object(auth.session, "request") as mock_request:
            mock_request.side_effect = exception_class(error_message)

            with pytest.raises(exception_class) as exc_info:
                await auth.async_request("GET", "test_endpoint")

            assert (
                str(exc_info.value) == error_message
            ), f"Expected error message '{error_message}', got '{str(exc_info.value)}'"
            mock_request.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,hub_status,hub_payload,hub_expected_exception,sns_status,sns_payload,sns_expected_exception",
    HUB_TEST_SCENARIOS,
)
async def test_make_hub_request_scenarios(
    auth: SimonAuth,
    scenario: str,
    hub_status: int,
    hub_payload: dict,
    hub_expected_exception: Exception,
    sns_status: int,
    sns_payload: dict,
    sns_expected_exception: Exception,
):
    """
    Test various scenarios for making hub requests.
    """
    with aioresponses() as mocked:
        url = MOCK_HUB_URL
        mocked.get(
            url,
            status=hub_status,
            payload=hub_payload or {"error": "test error"},
            headers={"Content-Type": "application/json"},
        )

        if hub_expected_exception and sns_expected_exception is None:
            with patch.object(auth, "async_request", return_value=sns_payload):
                response = await auth.async_request_hub(
                    "GET", MOCK_HUB_URL, "failover_path", MOCK_BASIC_AUTH
                )
                assert (
                    response == sns_payload
                ), f"Expected payload '{sns_payload}', got '{response}'"
        elif hub_expected_exception and sns_expected_exception:
            with patch.object(
                auth, "async_request", side_effect=sns_expected_exception
            ):
                with pytest.raises(sns_expected_exception):
                    await auth.async_request_hub(
                        "GET", MOCK_HUB_URL, "failover_path", MOCK_BASIC_AUTH
                    )
        else:
            response = await auth.async_request_hub(
                "GET", MOCK_HUB_URL, "failover_path", MOCK_BASIC_AUTH
            )
            assert (
                response == hub_payload
            ), f"Expected payload '{hub_payload}', got '{response}'"

        with pytest.raises(Exception):
            await auth.async_request_hub("GET", MOCK_HUB_URL, None, MOCK_BASIC_AUTH)
