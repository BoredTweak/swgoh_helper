import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping

import discord
from discord import app_commands

from swgoh_helper.progress import ProgressNotifier


MAX_DISCORD_MESSAGE_LENGTH = 2000
CODE_BLOCK_OVERHEAD = len("```\n\n```")
PROGRESS_POLL_INTERVAL = 2.0
PROGRESS_HEARTBEAT_SECONDS = 1.0

_executor = ThreadPoolExecutor(max_workers=4)


class CommandLogger:
    """Abstract command logger for Discord command invocations."""

    def log(
        self,
        interaction: discord.Interaction,
        command: str,
        params: Mapping[str, Any],
    ) -> None:
        raise NotImplementedError


class ConsoleCommandLogger(CommandLogger):
    """Writes command audit logs to stdout."""

    def __init__(
        self,
        clock: Callable[[], datetime] | None = None,
        output: Callable[[str], None] | None = None,
    ):
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._output = output or print

    def log(
        self,
        interaction: discord.Interaction,
        command: str,
        params: Mapping[str, Any],
    ) -> None:
        user = interaction.user
        timestamp = self._clock().strftime("%Y-%m-%d %H:%M:%S UTC")
        params_str = ", ".join(
            f"{key}={value}" for key, value in params.items() if value is not None
        )
        suffix = f" {params_str}" if params_str else ""
        self._output(f"[{timestamp}] {user} ({user.id}) called /{command}{suffix}")


_default_command_logger = ConsoleCommandLogger()


def log_command(interaction: discord.Interaction, command: str, **params) -> None:
    """Compatibility wrapper for command logging."""
    _default_command_logger.log(interaction, command, params)


class LatestProgressState:
    """Thread-safe holder for the most recent progress message."""

    def __init__(self):
        self._latest = ""
        self._lock = threading.Lock()

    def update(self, message: str) -> None:
        with self._lock:
            self._latest = message

    @property
    def latest(self) -> str:
        with self._lock:
            return self._latest


class DiscordProgressNotifier(ProgressNotifier):
    """Routes progress updates to a thread-safe message holder for Discord polling."""

    def __init__(self, state: LatestProgressState | None = None):
        self._state = state or LatestProgressState()
        super().__init__(callback=self._state.update)

    @property
    def latest(self) -> str:
        return self._state.latest


class ProgressHeartbeatPolicy:
    """Controls when to emit progress updates and heartbeat messages."""

    def __init__(
        self,
        poll_interval: float = PROGRESS_POLL_INTERVAL,
        heartbeat_seconds: float = PROGRESS_HEARTBEAT_SECONDS,
    ):
        self.poll_interval = poll_interval
        self._heartbeat_seconds = heartbeat_seconds
        self._last_status = ""
        self._status_started_at = 0.0
        self._last_sent_at = 0.0

    def next_message(self, status: str, now: float) -> str | None:
        if not status:
            return None

        if status != self._last_status:
            self._last_status = status
            self._status_started_at = now
            self._last_sent_at = 0.0

        should_heartbeat = (
            self._last_sent_at > 0.0
            and now - self._last_sent_at >= self._heartbeat_seconds
        )
        if self._last_sent_at == 0.0 or should_heartbeat:
            self._last_sent_at = now
            return self._format_status(status, now)
        return None

    def _format_status(self, status: str, now: float) -> str:
        elapsed = int(now - self._status_started_at)
        if elapsed < 2:
            return f"⏳ {status}"
        return f"⏳ {status} ({elapsed}s elapsed)"


class DiscordProgressReporter:
    """Bridges progress updates from worker code to Discord status edits."""

    def __init__(
        self,
        interaction: discord.Interaction,
        notifier: DiscordProgressNotifier,
        policy: ProgressHeartbeatPolicy | None = None,
    ):
        self._interaction = interaction
        self._notifier = notifier
        self._policy = policy or ProgressHeartbeatPolicy()

    async def run(self, worker_task: Awaitable[str]) -> str:
        poll_task = asyncio.create_task(self._poll_progress())
        try:
            return await worker_task
        finally:
            poll_task.cancel()
            with suppress(asyncio.CancelledError):
                await poll_task

    async def _poll_progress(self) -> None:
        while True:
            await asyncio.sleep(self._policy.poll_interval)
            now = time.monotonic()
            status = self._notifier.latest
            content = self._policy.next_message(status, now)
            if not content:
                continue
            try:
                await self._interaction.edit_original_response(content=content)
            except discord.HTTPException:
                continue


def unwrap_app_command_error(error: app_commands.AppCommandError) -> Exception:
    """Unwrap app-command invocation errors to their original exception."""
    if isinstance(error, app_commands.CommandInvokeError):
        return error.original
    return error


def _format_permission_names(permissions: list[str]) -> str:
    return ", ".join(permission.replace("_", " ") for permission in permissions)


def permission_error_message(error: Exception) -> str | None:
    """Return user-facing text for permission-related command failures."""
    if isinstance(error, app_commands.BotMissingPermissions):
        missing = _format_permission_names(error.missing_permissions)
        return f"I need additional Discord permissions to run this command: {missing}."
    if isinstance(error, app_commands.MissingPermissions):
        missing = _format_permission_names(error.missing_permissions)
        return f"You are missing required permissions to run this command: {missing}."
    if isinstance(error, discord.Forbidden):
        return "I don't have permission to perform that action in this channel."
    return None


async def safe_defer(interaction: discord.Interaction, thinking: bool = True) -> bool:
    """Defer safely, returning False when Discord rejects the response."""
    try:
        await interaction.response.defer(thinking=thinking)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


async def safe_followup_send(
    interaction: discord.Interaction,
    content: str,
    *,
    ephemeral: bool = False,
) -> bool:
    """Send follow-up safely without raising when permissions are missing."""
    try:
        await interaction.followup.send(content, ephemeral=ephemeral)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


async def safe_send_message(
    interaction: discord.Interaction,
    content: str,
    *,
    ephemeral: bool = False,
) -> bool:
    """Safely send a response whether the interaction was acknowledged or not."""
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content, ephemeral=ephemeral)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


async def handle_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    """Handle global slash-command errors with permission-aware messaging."""
    root_error = unwrap_app_command_error(error)
    permission_message = permission_error_message(root_error)
    if permission_message:
        await safe_send_message(interaction, permission_message, ephemeral=True)
        return

    await safe_send_message(interaction, f"Error: {root_error}", ephemeral=True)


async def run_with_progress(
    interaction: discord.Interaction,
    func,
    *args,
    progress: DiscordProgressNotifier | None = None,
    **kwargs,
) -> str:
    """Run a blocking function in a thread while updating Discord with progress.

    The worker callable must return a string payload for Discord output.
    """
    notifier = progress or DiscordProgressNotifier()
    reporter = DiscordProgressReporter(interaction, notifier)

    loop = asyncio.get_running_loop()
    worker_task = loop.run_in_executor(_executor, _run_worker, func, args, kwargs)
    return await reporter.run(worker_task)


def _run_worker(func, args, kwargs) -> str:
    result = func(*args, **kwargs)
    if not isinstance(result, str):
        actual_type = type(result).__name__
        raise TypeError(
            f"Worker function must return str for Discord output, got {actual_type}"
        )
    return result


def split_message(text: str, limit: int = MAX_DISCORD_MESSAGE_LENGTH) -> list[str]:
    """Split text into chunks that fit within Discord's message limit."""
    if len(text) <= limit:
        return [text]

    usable = limit - CODE_BLOCK_OVERHEAD
    lines = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > usable and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks
