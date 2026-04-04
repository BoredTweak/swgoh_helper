import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from swgoh_helper.app import RotePlatoonApp, RoteFarmAdvisorApp
from swgoh_helper.models import VALID_ROTE_OUTPUT_FORMATS
from swgoh_discord.utils import (
    DiscordProgressNotifier,
    log_command,
    run_with_progress,
    split_message,
)


class RoteCog(commands.Cog):
    def __init__(self, bot: commands.Bot, api_key: str):
        self.bot = bot
        self.api_key = api_key

    @app_commands.command(
        name="rote-platoon",
        description="Analyze guild for RotE platoon requirements",
    )
    @app_commands.describe(
        ally_code="Player ally code (e.g. 123456789)",
        max_phase="Limit analysis to phases up to N (e.g. 4, 3b, 5)",
        refresh="Force fresh data from API (ignore cache)",
        output_format="Output format: all, coverage, gaps, owners, farming, farming-by-territory",
        ignored_players="Comma-separated list of player names to exclude",
    )
    async def rote_platoon(
        self,
        interaction: discord.Interaction,
        ally_code: str,
        max_phase: Optional[str] = None,
        refresh: bool = False,
        output_format: Optional[str] = "gaps",
        ignored_players: Optional[str] = None,
    ):
        log_command(
            interaction,
            "rote-platoon",
            ally_code=ally_code,
            max_phase=max_phase,
            refresh=refresh,
            output_format=output_format,
            ignored_players=ignored_players,
        )
        await interaction.response.defer(thinking=True)
        try:
            if output_format not in VALID_ROTE_OUTPUT_FORMATS:
                await interaction.followup.send(
                    f"Invalid output format. Expected one of: {', '.join(VALID_ROTE_OUTPUT_FORMATS)}"
                )
                return

            parsed_ignored = None
            if ignored_players:
                parsed_ignored = [
                    p.strip() for p in ignored_players.split(",") if p.strip()
                ]

            notifier = DiscordProgressNotifier()
            app = RotePlatoonApp(self.api_key, progress=notifier)
            output = await run_with_progress(
                interaction,
                app.analyze_guild,
                ally_code,
                max_phase=max_phase,
                refresh=refresh,
                output_format=output_format,
                ignored_players=parsed_ignored,
                progress=notifier,
            )
            await self._send_output(interaction, output)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @app_commands.command(
        name="rote-farm",
        description="Personal farm recommendations based on guild needs",
    )
    @app_commands.describe(
        ally_code="Player ally code (e.g. 123456789)",
        max_phase="Limit analysis to phases up to N (e.g. 4, 3b, 5)",
        max_recommendations="Max units to recommend (default 15)",
        include_unowned="Include units you don't own yet",
    )
    async def rote_farm(
        self,
        interaction: discord.Interaction,
        ally_code: str,
        max_phase: Optional[str] = None,
        max_recommendations: int = 15,
        include_unowned: bool = False,
    ):
        log_command(
            interaction,
            "rote-farm",
            ally_code=ally_code,
            max_phase=max_phase,
            max_recommendations=max_recommendations,
            include_unowned=include_unowned,
        )
        await interaction.response.defer(thinking=True)
        try:
            notifier = DiscordProgressNotifier()
            app = RoteFarmAdvisorApp(self.api_key, progress=notifier)
            output = await run_with_progress(
                interaction,
                app.recommend_for_player,
                ally_code,
                max_phase=max_phase,
                max_recommendations=max_recommendations,
                include_unowned=include_unowned,
                progress=notifier,
            )
            await self._send_output(interaction, output)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    async def _send_output(self, interaction: discord.Interaction, output: str) -> None:
        if not output.strip():
            await interaction.followup.send("No results found.")
            return
        for chunk in split_message(output):
            await interaction.followup.send(f"```\n{chunk}\n```")


async def setup(bot: commands.Bot, api_key: str):
    await bot.add_cog(RoteCog(bot, api_key))
