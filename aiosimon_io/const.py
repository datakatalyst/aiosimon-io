"""
Constants for the Simon iO system.

This module defines base URLs and API endpoints used throughout the Simon iO system.
"""

# Base URLs

AUTH_BASE_URL: str = "https://auth.simon-cloud.com"
"""Base URL for the Simon Cloud authentication service."""

SNS_BASE_URL: str = "https://sns.simon-cloud.com"
"""Base URL for the Simon Cloud S&S (Switch & Socket) API."""

# User endpoints

USER_ENDPOINT: str = "api/v1/users"
"""API endpoint for accessing user data."""

# Installation endpoints

INSTALLATIONS_ENDPOINT: str = "api/v1/users/installations"
"""API endpoint to retrieve the list of installations linked to a user."""

SNS_ELEMENTS_ENDPOINT: str = "api/v1/installations/{installation_id}/elements"
"""S&S API endpoint to retrieve elements within a specific installation."""

HUB_ELEMENTS_ENDPOINT: str = "api/v1/elements"
"""Hub endpoint to retrieve elements directly from the hub."""

HUB_HARDWARE_TOKEN_ENDPOINT: str = "api/v1/installation/hardware-token"
"""Endpoint to obtain the Hub hardware token for an installation."""

# Device endpoints

HUB_DEVICES_ENDPOINT: str = "api/v1/devices"
"""Hub endpoint to retrieve the list of connected devices."""

SNS_DEVICES_ENDPOINT: str = "api/v1/installations/{installation_id}/devices"
"""S&S API endpoint to retrieve devices associated with a specific installation."""
