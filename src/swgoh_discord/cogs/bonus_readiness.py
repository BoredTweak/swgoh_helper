import discord
from discord import app_commands
from discord.ext import commands

from swgoh_helper.rote_bonus_readiness import BonusReadinessApp
from swgoh_discord.utils import (
    DiscordProgressNotifier,
    log_command,
    run_with_progress,
    safe_defer,
    safe_followup_send,
    safe_send_message,
    split_message,
)


class BonusReadinessCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="rote-bonus-readiness",
        description="Analyze guild readiness for RotE bonus zones",
    )
    @app_commands.describe(
        guild_id="Guild ID (run rote-platoon first to populate cache)",
    )
    async def rote_bonus_readiness(
        self,
        interaction: discord.Interaction,
        guild_id: str,
    ):
        log_command(interaction, "rote-bonus-readiness", guild_id=guild_id)
        try:
            if not await safe_defer(interaction, thinking=True):
                return

            notifier = DiscordProgressNotifier()
            app = BonusReadinessApp(progress=notifier)
            output = await run_with_progress(
                interaction, app.analyze, guild_id, progress=notifier
            )
            await self._send_output(interaction, output)
        except FileNotFoundError:
            await safe_send_message(
                interaction,
                "Error: Guild/player data not found. "
                "Run `/rote-platoon` first to populate the cache.",
                ephemeral=True,
            )
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


async def setup(bot: commands.Bot):
    await bot.add_cog(BonusReadinessCog(bot))
