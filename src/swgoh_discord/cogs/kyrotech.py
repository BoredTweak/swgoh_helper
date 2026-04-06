import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from swgoh_helper.app import KyrotechAnalysisApp
from swgoh_discord.utils import (
    DiscordProgressNotifier,
    log_command,
    run_with_progress,
    safe_defer,
    safe_followup_send,
    safe_send_message,
    split_message,
)


class KyrotechCog(commands.Cog):
    def __init__(self, bot: commands.Bot, api_key: str):
        self.bot = bot
        self.api_key = api_key

    @app_commands.command(
        name="kyrotech",
        description="Analyze kyrotech needs; useful for choosing Lightspeed token targets",
    )
    @app_commands.describe(
        ally_code="Player ally code (e.g. 123456789)",
        faction="Filter by faction name (e.g. Empire, Rebel)",
        include_unowned="Include characters the player doesn't own",
        verbose="Show all characters instead of default top 10",
    )
    async def kyrotech(
        self,
        interaction: discord.Interaction,
        ally_code: str,
        faction: Optional[str] = None,
        include_unowned: bool = False,
        verbose: bool = False,
    ):
        log_command(
            interaction,
            "kyrotech",
            ally_code=ally_code,
            faction=faction,
            include_unowned=include_unowned,
            verbose=verbose,
        )
        try:
            if not await safe_defer(interaction, thinking=True):
                return

            notifier = DiscordProgressNotifier()
            app = KyrotechAnalysisApp(self.api_key, progress=notifier)
            if faction:
                output = await run_with_progress(
                    interaction,
                    app.find_all_faction_kyrotech,
                    ally_code,
                    faction,
                    include_unowned,
                    verbose,
                    progress=notifier,
                )
            else:
                output = await run_with_progress(
                    interaction,
                    app.analyze_player,
                    ally_code,
                    include_unowned,
                    verbose,
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
    await bot.add_cog(KyrotechCog(bot, api_key))
