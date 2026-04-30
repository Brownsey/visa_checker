"""CLI entry point: visa-checker run | check-now | test-alerts | history | status"""
from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

console = Console()


def _load(config_path: str | None) -> object:
    from visa_checker.config.settings import load_settings

    return load_settings(config_path)


@click.group()
@click.option("--config", "-c", default=None, help="Path to config.yaml")
@click.pass_context
def cli(ctx: click.Context, config: str | None) -> None:
    """Schengen visa slot monitor for UK residents."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@cli.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """Start the continuous monitoring loop."""
    settings = _load(ctx.obj["config_path"])

    from visa_checker.application.factory import build_orchestrator
    from visa_checker.domain.logging import configure_logging

    configure_logging(settings.logging.level, settings.logging.file)
    orchestrator, browser, state = build_orchestrator(settings)

    async def _run() -> None:
        await state.initialise()
        async with browser:
            await orchestrator.start()
            logger.info("Visa checker running. Press Ctrl+C to stop.")
            try:
                while True:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
            finally:
                await orchestrator.stop()

    asyncio.run(_run())


@cli.command("check-now")
@click.option("--provider", default=None, help="Limit to one provider")
@click.pass_context
def check_now(ctx: click.Context, provider: str | None) -> None:
    """Run a single check and print results (no state changes, no alerts)."""
    settings = _load(ctx.obj["config_path"])

    from visa_checker.adapters.anti_detection.captcha import build_captcha_solver
    from visa_checker.adapters.browser.engine import PlaywrightBrowserEngine
    from visa_checker.application.factory import build_scrapers
    from visa_checker.domain.logging import configure_logging

    configure_logging(settings.logging.level)

    async def _check() -> None:
        browser = PlaywrightBrowserEngine(headless=True)
        async with browser:
            scrapers = build_scrapers(settings, browser)
            if provider:
                scrapers = [s for s in scrapers if s.provider_name == provider]

            table = Table(title="Available Slots", show_header=True)
            table.add_column("Provider")
            table.add_column("Country")
            table.add_column("Centre")
            table.add_column("Date")
            table.add_column("Time")
            table.add_column("URL")

            for scraper in scrapers:
                try:
                    slots = await scraper.run_once()
                    for slot in slots:
                        table.add_row(
                            slot.provider,
                            slot.country,
                            slot.centre,
                            slot.human_date(),
                            slot.human_time(),
                            slot.booking_url[:60] + "…" if len(slot.booking_url) > 60 else slot.booking_url,
                        )
                except Exception as exc:
                    console.print(f"[red][{scraper.provider_name}] Error: {exc}[/red]")

            console.print(table)

    asyncio.run(_check())


@cli.command("test-alerts")
@click.pass_context
def test_alerts(ctx: click.Context) -> None:
    """Send a test notification to all configured alert channels."""
    settings = _load(ctx.obj["config_path"])

    from visa_checker.adapters.state.sqlite_repository import SQLiteStateRepository
    from visa_checker.application.alert_dispatcher import AlertDispatcher
    from visa_checker.application.factory import build_alert_channels

    channels = build_alert_channels(settings)
    if not channels:
        console.print("[yellow]No alert channels are enabled in config.[/yellow]")
        return

    state = SQLiteStateRepository(settings.state.db_path)

    async def _test() -> None:
        await state.initialise()
        dispatcher = AlertDispatcher(channels, state)
        results = await dispatcher.test_all()
        for channel, ok in results.items():
            icon = "✅" if ok else "❌"
            console.print(f"{icon} {channel}")

    asyncio.run(_test())


@cli.command()
@click.option("--days", default=7, show_default=True, help="History window in days")
@click.pass_context
def history(ctx: click.Context, days: int) -> None:
    """Show slot availability history from the local database."""
    settings = _load(ctx.obj["config_path"])

    from visa_checker.adapters.state.sqlite_repository import SQLiteStateRepository

    state = SQLiteStateRepository(settings.state.db_path)

    async def _history() -> None:
        await state.initialise()
        slots = await state.get_history(days)
        if not slots:
            console.print(f"[yellow]No slots recorded in the last {days} days.[/yellow]")
            return
        table = Table(title=f"Slot History (last {days} days)")
        table.add_column("Provider")
        table.add_column("Country")
        table.add_column("Centre")
        table.add_column("Date")
        table.add_column("First Seen")
        for slot in slots:
            table.add_row(
                slot.provider,
                slot.country,
                slot.centre,
                slot.human_date(),
                slot.checked_at.strftime("%Y-%m-%d %H:%M UTC"),
            )
        console.print(table)

    asyncio.run(_history())


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show circuit breaker state and last poll times."""
    settings = _load(ctx.obj["config_path"])

    from visa_checker.adapters.state.sqlite_repository import SQLiteStateRepository

    state = SQLiteStateRepository(settings.state.db_path)

    async def _status() -> None:
        await state.initialise()
        table = Table(title="Circuit Breaker Status")
        table.add_column("Provider")
        table.add_column("State")
        table.add_column("Failures")
        table.add_column("Retry At")
        # Just show available providers from targets
        seen = set()
        for target in settings.targets:
            if target.provider not in seen:
                seen.add(target.provider)
                table.add_row(target.provider, "unknown", "-", "-")
        console.print(table)
        console.print("[dim]Run visa-checker run to start monitoring.[/dim]")

    asyncio.run(_status())
