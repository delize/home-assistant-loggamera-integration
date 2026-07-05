"""API client for Loggamera."""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

import certifi
import requests

from .const import (
    API_ENDPOINT_COOLING_UNIT,
    API_ENDPOINT_DEVICES,
    API_ENDPOINT_EXECUTE_SCENARIO_ASYNC,
    API_ENDPOINT_GENERIC_DEVICE,
    API_ENDPOINT_HEAT_PUMP,
    API_ENDPOINT_ORGANIZATIONS,
    API_ENDPOINT_POWER_METER,
    API_ENDPOINT_RAW_DATA,
    API_ENDPOINT_ROOM_SENSOR,
    API_ENDPOINT_SCENARIOS,
    API_ENDPOINT_WATER_METER,
    API_URL,
)

_LOGGER = logging.getLogger(__name__)

# Map device class -> dedicated endpoint. Devices not listed here fall through
# to the generic fallback chain (RawData, GenericDevice).
PRIMARY_ENDPOINTS = {
    "PowerMeter": API_ENDPOINT_POWER_METER,
    "RoomSensor": API_ENDPOINT_ROOM_SENSOR,
    "WaterMeter": API_ENDPOINT_WATER_METER,
    "CoolingUnit": API_ENDPOINT_COOLING_UNIT,
    "HeatPump": API_ENDPOINT_HEAT_PUMP,
}

FALLBACK_ENDPOINTS = [API_ENDPOINT_RAW_DATA, API_ENDPOINT_GENERIC_DEVICE]

# Retry behavior
MAX_RETRIES = 3
BACKOFF_DELAYS = [15, 30, 60]
RETRYABLE_STATUS_CODES = {429, *range(500, 600)}


class LoggameraAPIError(Exception):
    """Exception for Loggamera API errors."""


class ErrorType(Enum):
    """Classification used to decide retry behavior."""

    NETWORK = "network"
    HTTP_RETRYABLE = "http_retryable"
    HTTP_CLIENT = "http_client"
    TIMEOUT = "timeout"
    INVALID_ENDPOINT = "invalid_endpoint"
    API_ERROR = "api_error"


RETRYABLE_ERRORS = {ErrorType.NETWORK, ErrorType.TIMEOUT, ErrorType.HTTP_RETRYABLE}


class CircuitBreaker:
    """Trip after `failure_threshold` failures; recover after `timeout` seconds."""

    def __init__(self, failure_threshold: int = 6, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # closed | open | half_open

    def is_open(self) -> bool:
        if self.state != "open":
            return False
        if time.time() - self.last_failure_time > self.timeout:
            self.state = "half_open"
            return False
        return True

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            _LOGGER.warning(
                f"Circuit breaker opened after {self.failure_count} failures; "
                f"will retry in {self.timeout}s"
            )


def _classify_error(exception: Exception) -> ErrorType:
    """Map an exception to a retry-decision category."""
    if isinstance(exception, requests.exceptions.Timeout):
        return ErrorType.TIMEOUT
    if isinstance(exception, requests.exceptions.ConnectionError):
        return ErrorType.NETWORK
    if isinstance(exception, LoggameraAPIError):
        if "invalid endpoint" in str(exception).lower():
            return ErrorType.INVALID_ENDPOINT
        return ErrorType.API_ERROR
    return ErrorType.NETWORK


def _is_invalid_endpoint_response(result: Dict[str, Any]) -> bool:
    """Check whether an API response indicates the endpoint isn't valid for this caller."""
    error = result.get("Error")
    return isinstance(error, dict) and error.get("Message") == "invalid endpoint"


class LoggameraAPI:
    """API client for Loggamera.

    The PowerMeter endpoint typically updates every ~30 minutes upstream;
    polling more frequently does not yield more data.
    """

    def __init__(self, api_key: str, organization_id: Optional[Union[str, int]] = None) -> None:
        self.api_key = api_key
        self.organization_id = organization_id
        self.session = requests.Session()
        self.session.verify = certifi.where()

        self._endpoint_cache: Dict[str, bool] = {}
        self._data_gap_tracker: Dict[str, Dict[str, Any]] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

    def _circuit_breaker(self, endpoint: str) -> CircuitBreaker:
        if endpoint not in self._circuit_breakers:
            self._circuit_breakers[endpoint] = CircuitBreaker()
        return self._circuit_breakers[endpoint]

    def _make_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST to a Loggamera endpoint with retry + per-endpoint circuit breaker."""
        breaker = self._circuit_breaker(endpoint)
        if breaker.is_open():
            raise LoggameraAPIError(
                f"Circuit breaker is open for endpoint {endpoint}; too many recent failures"
            )

        url = f"{API_URL}/{endpoint}"
        payload = {"ApiKey": self.api_key, **(data or {})}

        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                result = self._attempt_request(url, payload, endpoint)
            except LoggameraAPIError as exc:
                last_exc = exc
                error_type = _classify_error(exc)
                if error_type in RETRYABLE_ERRORS and attempt < MAX_RETRIES:
                    delay = BACKOFF_DELAYS[min(attempt, len(BACKOFF_DELAYS) - 1)]
                    _LOGGER.warning(
                        f"{endpoint} failed (attempt {attempt + 1}): {exc}; retrying in {delay}s"
                    )
                    time.sleep(delay)
                    continue
                breaker.record_failure()
                raise

            breaker.record_success()
            if attempt > 0:
                _LOGGER.info(f"{endpoint} succeeded after {attempt} retries")
            return result

        breaker.record_failure()
        raise LoggameraAPIError(f"Request failed: {last_exc}") from last_exc

    def _attempt_request(self, url: str, payload: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Perform a single HTTP attempt and validate the response shape."""
        try:
            response = self.session.post(
                url, headers={"Content-Type": "application/json"}, json=payload, timeout=30
            )
        except requests.exceptions.RequestException as exc:
            raise LoggameraAPIError(f"Network error: {exc}") from exc

        if response.status_code != 200:
            msg = f"HTTP {response.status_code}: {response.text}"
            if response.status_code in RETRYABLE_STATUS_CODES:
                # Caller's retry loop will see this as retryable via _classify_error
                raise LoggameraAPIError(msg)
            raise LoggameraAPIError(msg)

        try:
            result = response.json() if response.text.strip() else {"Data": None, "Error": None}
        except ValueError as exc:
            raise LoggameraAPIError(f"Invalid JSON response: {response.text}") from exc

        error = result.get("Error")
        if error is not None:
            message = error.get("Message") if isinstance(error, dict) else str(error)
            if message == "invalid endpoint":
                self._endpoint_cache[endpoint] = False
            raise LoggameraAPIError(f"API error: {message}")

        return result

    def get_organizations(self) -> Dict[str, Any]:
        return self._make_request(API_ENDPOINT_ORGANIZATIONS)

    def get_devices(self) -> Dict[str, Any]:
        if not self.organization_id:
            raise LoggameraAPIError("Organization ID is required for get_devices")
        return self._make_request(API_ENDPOINT_DEVICES, {"OrganizationId": self.organization_id})

    def get_device_data(self, device_id: Union[str, int], device_type: str) -> Dict[str, Any]:
        """Fetch device data, preferring the device-type endpoint then falling back."""
        device_id = self._validate_device_id(device_id)
        return self._fetch_with_fallbacks(device_id, device_type)

    def get_raw_data(self, device_id: Union[str, int]) -> Dict[str, Any]:
        device_id = self._validate_device_id(device_id)
        return self._make_request(API_ENDPOINT_RAW_DATA, {"DeviceId": device_id})

    def get_scenarios(self) -> Dict[str, Any]:
        if not self.organization_id:
            return {"Data": {"Scenarios": []}, "Error": None}
        try:
            return self._make_request(
                API_ENDPOINT_SCENARIOS, {"OrganizationId": self.organization_id}
            )
        except LoggameraAPIError as exc:
            if "invalid endpoint" in str(exc):
                return {"Data": {"Scenarios": []}, "Error": None}
            raise

    def execute_scenario_async(
        self, scenario_id: Union[str, int], duration_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"ScenarioId": scenario_id}
        if duration_minutes is not None:
            payload["DurationMinutes"] = duration_minutes
        return self._make_request(API_ENDPOINT_EXECUTE_SCENARIO_ASYNC, payload)

    @staticmethod
    def _validate_device_id(device_id: Union[str, int]) -> int:
        try:
            return int(device_id)
        except (ValueError, TypeError) as exc:
            raise LoggameraAPIError(f"Invalid device ID: {device_id}") from exc

    def _fetch_with_fallbacks(self, device_id: int, device_type: str) -> Dict[str, Any]:
        """Try the primary endpoint for the device type, then RawData/GenericDevice."""
        primary = PRIMARY_ENDPOINTS.get(device_type)
        candidates = [e for e in (primary, *FALLBACK_ENDPOINTS) if e]

        for endpoint in candidates:
            if self._endpoint_cache.get(endpoint) is False:
                continue
            try:
                response = self._make_request(endpoint, {"DeviceId": device_id})
            except LoggameraAPIError as exc:
                _LOGGER.debug(f"Endpoint {endpoint} failed for device {device_id}: {exc}")
                continue

            has_data = self._has_valid_data(response)
            self._track_data_gap(device_id, has_data, endpoint)
            if has_data:
                response["_endpoint_used"] = endpoint
                return response

        self._track_data_gap(device_id, False, "all_endpoints_failed")
        raise LoggameraAPIError(f"All endpoints failed for device {device_id}")

    @staticmethod
    def _has_valid_data(response: Dict[str, Any]) -> bool:
        data = response.get("Data") or {}
        return bool(data.get("Values"))

    def _track_data_gap(self, device_id: int, has_data: bool, endpoint: str) -> None:
        """Track gap start/end per device for the API health diagnostic sensor."""
        now = time.time()
        key = str(device_id)
        tracker = self._data_gap_tracker.setdefault(
            key,
            {
                "gap_start": None,
                "gap_count": 0,
                "last_successful": now if has_data else None,
                "consecutive_failures": 0,
                "endpoint": endpoint,
            },
        )

        if has_data:
            if tracker["gap_start"] is not None:
                gap_minutes = int((now - tracker["gap_start"]) / 60)
                _LOGGER.warning(
                    f"Data gap ended for device {device_id} after {gap_minutes} minutes "
                    f"({tracker['consecutive_failures']} failed attempts on {endpoint})"
                )
                tracker["gap_start"] = None
                tracker["consecutive_failures"] = 0
            tracker["last_successful"] = now
            tracker["endpoint"] = endpoint
            return

        tracker["consecutive_failures"] += 1
        if tracker["gap_start"] is None:
            tracker["gap_start"] = now
            tracker["gap_count"] += 1
            _LOGGER.warning(
                f"Data gap started for device {device_id} at {datetime.now().isoformat()} "
                f"(gap #{tracker['gap_count']}, endpoint: {endpoint})"
            )
        elif tracker["consecutive_failures"] % 5 == 0:
            gap_minutes = int((now - tracker["gap_start"]) / 60)
            _LOGGER.error(
                f"Ongoing data gap for device {device_id}: {gap_minutes} minutes, "
                f"{tracker['consecutive_failures']} consecutive failures on {endpoint}"
            )

    def get_data_gap_status(self) -> Dict[str, Any]:
        """Snapshot of gap state, used by the API health binary sensor."""
        now = time.time()
        devices: Dict[str, Dict[str, Any]] = {}
        with_gaps = 0

        for device_id, tracker in self._data_gap_tracker.items():
            entry: Dict[str, Any] = {
                "has_active_gap": tracker["gap_start"] is not None,
                "total_gaps": tracker["gap_count"],
                "consecutive_failures": tracker["consecutive_failures"],
                "last_successful": tracker["last_successful"],
                "endpoint": tracker.get("endpoint", "unknown"),
            }
            if tracker["gap_start"]:
                entry["gap_duration_minutes"] = int((now - tracker["gap_start"]) / 60)
                with_gaps += 1
            elif tracker["last_successful"]:
                entry["minutes_since_last_success"] = int((now - tracker["last_successful"]) / 60)
            devices[device_id] = entry

        return {
            "devices_with_gaps": with_gaps,
            "total_devices_tracked": len(self._data_gap_tracker),
            "devices": devices,
        }
