import asyncio
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timezone

import discord

from swgoh_helper.progress import ProgressNotifier


MAX_DISCORD_MESSAGE_LENGTH = 2000
CODE_BLOCK_OVERHEAD = len("```\n\n```")
PROGRESS_POLL_INTERVAL = 2.0
PROGRESS_HEARTBEAT_SECONDS = 1.0

_executor = ThreadPoolExecutor(max_workers=4)


def log_command(interaction: discord.Interaction, command: str, **params) -> None:
    user = interaction.user
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    params_str = ", ".join(f"{k}={v}" for k, v in params.items() if v is not None)
    print(f"[{timestamp}] {user} ({user.id}) called /{command} {params_str}")


class DiscordProgressNotifier(ProgressNotifier):
    """Routes progress updates to a thread-safe message holder for Discord polling."""

    def __init__(self):
        self._latest = ""
        self._lock = threading.Lock()
        super().__init__(callback=self._store)

    def _store(self, message: str) -> None:
        with self._lock:
            self._latest = message

    @property
    def latest(self) -> str:
        with self._lock:
            return self._latest


async def run_with_progress(
    interaction: discord.Interaction,
    func,
    *args,
    progress: DiscordProgressNotifier | None = None,
    **kwargs,
) -> str:
    """Run a blocking function in a thread while updating Discord with progress."""
    notifier = progress or DiscordProgressNotifier()
    last_status = ""
    status_started_at = 0.0
    last_sent_at = 0.0
    buf = io.StringIO()

    async def poll_progress():
        nonlocal last_status, status_started_at, last_sent_at
        while True:
            await asyncio.sleep(PROGRESS_POLL_INTERVAL)
            status = notifier.latest
            if not status:
                continue

            now = time.monotonic()
            if status != last_status:
                last_status = status
                status_started_at = now
                last_sent_at = 0.0

            should_heartbeat = (
                last_sent_at > 0.0 and now - last_sent_at >= PROGRESS_HEARTBEAT_SECONDS
            )
            if last_sent_at == 0.0 or should_heartbeat:
                elapsed = int(now - status_started_at)
                content = (
                    f"⏳ {status}"
                    if elapsed < 2
                    else f"⏳ {status} ({elapsed}s elapsed)"
                )
                try:
                    await interaction.edit_original_response(content=content)
                    last_sent_at = now
                except discord.HTTPException:
                    pass

    loop = asyncio.get_running_loop()
    poll_task = asyncio.create_task(poll_progress())
    try:
        output = await loop.run_in_executor(
            _executor, _run_captured, buf, func, args, kwargs
        )
    finally:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass
    return output


def _run_captured(buf: io.StringIO, func, args, kwargs) -> str:
    with redirect_stdout(buf):
        func(*args, **kwargs)
    return buf.getvalue()


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
