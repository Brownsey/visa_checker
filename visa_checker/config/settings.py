"""
Configuration loading: YAML file with ${ENV_VAR} interpolation, validated by Pydantic v2.
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator, model_validator

_ENV_RE = re.compile(r"\$\{([^}]+)\}")


def _interpolate(value: object) -> object:
    """Recursively replace ${VAR} in strings with environment variable values."""
    if isinstance(value, str):
        return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

ProviderName = Literal["vfs_global", "tlscontact", "bls", "capago"]


class TargetConfig(BaseModel):
    country: str
    provider: ProviderName
    centre: str
    visa_type: str = "short_stay"
    visa_sub_category: str = ""
    earliest_date: date
    latest_date: date

    @model_validator(mode="after")
    def dates_valid(self) -> "TargetConfig":
        if self.earliest_date >= self.latest_date:
            raise ValueError("earliest_date must be before latest_date")
        return self


class ProviderCredentials(BaseModel):
    email: str = ""
    password: str = ""


class CredentialsConfig(BaseModel):
    vfs_global: ProviderCredentials = ProviderCredentials()
    tlscontact: ProviderCredentials = ProviderCredentials()
    bls: ProviderCredentials = ProviderCredentials()
    capago: ProviderCredentials = ProviderCredentials()


class PollingConfig(BaseModel):
    interval_seconds: int = 90
    jitter_pct: float = 0.20
    max_retries: int = 5

    @field_validator("jitter_pct")
    @classmethod
    def jitter_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("jitter_pct must be between 0 and 1")
        return v


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    to: str = ""


class NtfyConfig(BaseModel):
    enabled: bool = False
    server: str = "https://ntfy.sh"
    topic: str = ""


class SMSConfig(BaseModel):
    enabled: bool = False
    twilio_sid: str = ""
    twilio_token: str = ""
    from_number: str = ""
    to_number: str = ""


class DiscordConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    username: str = "Visa Checker"
    avatar_url: str = ""


class WxPusherConfig(BaseModel):
    enabled: bool = False
    app_token: str = ""
    uid: str = ""
    topic_id: str = ""


class WeChatWorkConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    mention_mobiles: list[str] = []


class AlertsConfig(BaseModel):
    telegram: TelegramConfig = TelegramConfig()
    email: EmailConfig = EmailConfig()
    ntfy: NtfyConfig = NtfyConfig()
    sms: SMSConfig = SMSConfig()
    discord: DiscordConfig = DiscordConfig()
    wxpusher: WxPusherConfig = WxPusherConfig()
    wechat_work: WeChatWorkConfig = WeChatWorkConfig()


class ProxiesConfig(BaseModel):
    enabled: bool = False
    provider: Literal["brightdata", "file"] = "file"
    endpoint: str = ""
    file: str = "proxies.txt"


class CaptchaConfig(BaseModel):
    provider: Literal[
        "audio_recaptcha",          # free — reCAPTCHA v2 audio challenge via speech-to-text
        "hcaptcha_accessibility",   # free — hCaptcha accessibility cookie bypass
        "manual",                   # free — pause and send Telegram alert for human solving
        "2captcha",                 # paid ~$2/1000
        "anticaptcha",              # paid
        "none",                     # raises immediately on any CAPTCHA
    ] = "audio_recaptcha"
    api_key: str = ""
    # For hcaptcha_accessibility: register at https://www.hcaptcha.com/accessibility
    hcaptcha_accessibility_token: str = ""
    # For manual: Telegram credentials to send the screenshot to
    manual_telegram_bot_token: str = ""
    manual_telegram_chat_id: str = ""


class StateConfig(BaseModel):
    db_path: str = "data/state.db"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "data/visa_checker.log"


class Settings(BaseModel):
    targets: list[TargetConfig]
    credentials: CredentialsConfig = CredentialsConfig()
    polling: PollingConfig = PollingConfig()
    alerts: AlertsConfig = AlertsConfig()
    proxies: ProxiesConfig = ProxiesConfig()
    captcha: CaptchaConfig = CaptchaConfig()
    state: StateConfig = StateConfig()
    logging: LoggingConfig = LoggingConfig()

    @field_validator("targets")
    @classmethod
    def at_least_one_target(cls, v: list[TargetConfig]) -> list[TargetConfig]:
        if not v:
            raise ValueError("At least one target must be configured")
        return v


class ConfigValidationError(Exception):
    pass


def load_settings(path: str | Path | None = None) -> Settings:
    """Load and validate settings from a YAML file.

    Resolves ${ENV_VAR} placeholders before validation.
    Falls back to VISA_CHECKER_CONFIG env var, then 'config/config.yaml'.
    """
    if path is None:
        path = os.environ.get("VISA_CHECKER_CONFIG", "config/config.yaml")
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigValidationError(f"Config file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"Invalid YAML in {config_path}: {exc}") from exc

    interpolated = _interpolate(raw)

    try:
        return Settings.model_validate(interpolated)
    except Exception as exc:
        raise ConfigValidationError(f"Config validation failed: {exc}") from exc
