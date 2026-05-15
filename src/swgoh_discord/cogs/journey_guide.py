import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from swgoh_helper.app import JourneyGuidePathApp
from swgoh_discord.utils import (
    DiscordProgressNotifier,
    log_command,
    run_with_progress,
    safe_defer,
    safe_followup_send,
    safe_send_message,
    split_message,
)


class JourneyGuideCog(commands.Cog):
    def __init__(self, bot: commands.Bot, api_key: str):
        self.bot = bot
        self.api_key = api_key

    @app_commands.command(
        name="journey-guide",
        description="Recommend the best Journey Guide unlock paths for your roster",
    )
    @app_commands.describe(
        ally_code="Player ally code (e.g. 123456789)",
        target_gl="Filter by specific GL (e.g. Executor, SithEmpire, CraitonNebula)",
        top_n="Number of paths to show (default: 3)",
        include_unowned="Include characters the player doesn't own",
    )
    async def journey_guide(
        self,
        interaction: discord.Interaction,
        ally_code: str,
        target_gl: Optional[str] = None,
        top_n: Optional[int] = 3,
        include_unowned: bool = True,
    ):
        log_command(
            interaction,
            "journey-guide",
            ally_code=ally_code,
            target_gl=target_gl,
            top_n=top_n,
            include_unowned=include_unowned,
        )
        try:
            if not await safe_defer(interaction, thinking=True):
                return

            notifier = DiscordProgressNotifier()
            app = JourneyGuidePathApp(self.api_key, progress=notifier)
            output = await run_with_progress(
                interaction,
                app.analyze_player,
                ally_code,
                target_gl,
                top_n,
                include_unowned,
                progress=notifier,
            )
            await self._send_output(interaction, output)
        except Exception as e:
            await safe_send_message(interaction, f"Error: {e}", ephemeral=True)

    async def _send_output(self, interaction: discord.Interaction, output: str) -> None:
        if not output.strip():
            await safe_followup_send(interaction, "No results found.")
            return
        for chunk in split_message(output):
            sent = await safe_followup_send(interaction, f"```\n{chunk}\n```")
            if not sent:
                return


async def setup(bot: commands.Bot, api_key: str):
    await bot.add_cog(JourneyGuideCog(bot, api_key))
