"""
Constants for the SunWEG integration.

This module defines the shared constants used across the integration files. It
includes the integration domain, default update intervals, and common keys
referenced in the configuration and data storage.
"""

from datetime import timedelta


# Update the integration domain to a unique name to avoid collisions with core components.
DOMAIN: str = "sunweg_custom"

CONF_USERNAME: str = "username"
CONF_PASSWORD: str = "password"
CONF_PLANT_ID: str = "plant_id"
CONF_PLANT_NAME: str = "plant_name"

DEFAULT_SCAN_INTERVAL: timedelta = timedelta(minutes=5)

API_BASE_URL: str = "https://api.sunweg.net/v2"

HEADER_USER_AGENT: str = "Mozilla/5.0"
