"""Domain exception hierarchy."""
from __future__ import annotations


class VisaCheckerError(Exception):
    """Base for all visa_checker errors."""


class ScraperError(VisaCheckerError):
    """Provider returned an unexpected response or the page flow failed."""


class AuthError(ScraperError):
    """Login failed or session was rejected."""


class BlockedError(ScraperError):
    """Provider is actively blocking the request (Cloudflare, IP ban, etc.)."""


class CaptchaError(VisaCheckerError):
    """CAPTCHA solving failed or timed out."""


class ProxyError(VisaCheckerError):
    """Proxy connection failure."""


class AlertError(VisaCheckerError):
    """Notification delivery failure."""


class CircuitOpenError(VisaCheckerError):
    """Circuit breaker is open; request not attempted."""


class ConfigValidationError(VisaCheckerError):
    """Configuration file is missing or invalid."""
