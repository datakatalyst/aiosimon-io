"""
Constants for the Simon iO system.

This module defines base URLs and API endpoints used throughout the Simon iO system.
"""

# Base urls
AUTH_BASE_URL: str = "https://auth.simon-cloud.com"
SNS_BASE_URL: str = "https://sns.simon-cloud.com"

# User endpoints
USER_ENDPOINT: str = "api/v1/users"

# Installation endpoints
INSTALLATIONS_ENDPOINT: str = "api/v1/users/installations"
SNS_ELEMENTS_ENDPOINT: str = "api/v1/installations/{installation_id}/elements"
HUB_ELEMENTS_ENDPOINT: str = "api/v1/elements"
HUB_HARDWARE_TOKEN_ENDPOINT: str = "api/v1/installation/hardware-token"

# Device endpoints
HUB_DEVICES_ENDPOINT: str = "api/v1/devices"
SNS_DEVICES_ENDPOINT: str = "api/v1/installations/{installation_id}/devices"
