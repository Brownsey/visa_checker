"""Wires together all adapters from a Settings object (composition root)."""
from __future__ import annotations

from visa_checker.adapters.alerts.discord import DiscordChannel
from visa_checker.adapters.alerts.email_channel import EmailChannel
from visa_checker.adapters.alerts.ntfy import NtfyChannel
from visa_checker.adapters.alerts.sms import SMSChannel
from visa_checker.adapters.alerts.telegram import TelegramChannel
from visa_checker.adapters.alerts.wechat_work import WeChatWorkChannel
from visa_checker.adapters.alerts.wxpusher import WxPusherChannel
from visa_checker.adapters.anti_detection.captcha import build_captcha_solver
from visa_checker.adapters.anti_detection.fingerprint import FingerprintRotator
from visa_checker.adapters.anti_detection.proxy import build_proxy_provider
from visa_checker.adapters.browser.engine import PlaywrightBrowserEngine
from visa_checker.adapters.scrapers.base import get_scraper_class
from visa_checker.adapters.state.sqlite_repository import SQLiteStateRepository
from visa_checker.application.alert_dispatcher import AlertDispatcher
from visa_checker.application.orchestrator import Orchestrator
from visa_checker.config.settings import CredentialsConfig, Settings
from visa_checker.ports.alert import IAlertChannel
from visa_checker.ports.scraper import IScraper


def build_alert_channels(settings: Settings) -> list[IAlertChannel]:
    channels: list[IAlertChannel] = []
    a = settings.alerts
    if a.telegram.enabled:
        channels.append(TelegramChannel(a.telegram.bot_token, a.telegram.chat_id))
    if a.ntfy.enabled:
        channels.append(NtfyChannel(a.ntfy.topic, a.ntfy.server))
    if a.email.enabled:
        channels.append(
            EmailChannel(
                a.email.smtp_host,
                a.email.smtp_port,
                a.email.username,
                a.email.password,
                a.email.to,
            )
        )
    if a.sms.enabled:
        channels.append(
            SMSChannel(
                a.sms.twilio_sid,
                a.sms.twilio_token,
                a.sms.from_number,
                a.sms.to_number,
            )
        )
    if a.discord.enabled:
        channels.append(DiscordChannel(a.discord.webhook_url, a.discord.username, a.discord.avatar_url))
    if a.wxpusher.enabled:
        channels.append(WxPusherChannel(a.wxpusher.app_token, a.wxpusher.uid, a.wxpusher.topic_id))
    if a.wechat_work.enabled:
        channels.append(WeChatWorkChannel(a.wechat_work.webhook_url, a.wechat_work.mention_mobiles))
    return channels


def _creds_for(provider: str, creds: CredentialsConfig) -> tuple[str, str]:
    mapping = {
        "vfs_global": creds.vfs_global,
        "tlscontact": creds.tlscontact,
        "bls": creds.bls,
        "capago": creds.capago,
    }
    c = mapping.get(provider, creds.vfs_global)
    return c.email, c.password


def build_scrapers(settings: Settings, browser: PlaywrightBrowserEngine) -> list[IScraper]:
    # Ensure all scraper modules are imported so the registry is populated
    import visa_checker.adapters.scrapers.bls_international  # noqa: F401
    import visa_checker.adapters.scrapers.capago  # noqa: F401
    import visa_checker.adapters.scrapers.tls_contact  # noqa: F401
    import visa_checker.adapters.scrapers.vfs_global  # noqa: F401

    captcha = build_captcha_solver(settings.captcha)
    scrapers: list[IScraper] = []
    for target in settings.targets:
        cls = get_scraper_class(target.provider)
        email, password = _creds_for(target.provider, settings.credentials)
        scrapers.append(cls(target=target, browser=browser, email=email, password=password, captcha_solver=captcha))
    return scrapers


def build_orchestrator(settings: Settings) -> tuple[Orchestrator, PlaywrightBrowserEngine, SQLiteStateRepository]:
    proxy_provider = build_proxy_provider(settings.proxies)
    fingerprint_rotator = FingerprintRotator()
    browser = PlaywrightBrowserEngine(
        headless=True,
        proxy_provider=proxy_provider,
        fingerprint_rotator=fingerprint_rotator,
    )
    state = SQLiteStateRepository(settings.state.db_path)
    channels = build_alert_channels(settings)
    dispatcher = AlertDispatcher(channels, state)
    scrapers = build_scrapers(settings, browser)
    orchestrator = Orchestrator(scrapers, dispatcher, state, settings)
    return orchestrator, browser, state
