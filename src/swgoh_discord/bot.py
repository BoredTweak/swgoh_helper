import os

import discord
from discord.ext import commands
import dotenv

from swgoh_discord.cogs.kyrotech import setup as kyrotech_setup
from swgoh_discord.cogs.rote import setup as rote_setup
from swgoh_discord.cogs.bonus_readiness import setup as bonus_readiness_setup


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    return commands.Bot(command_prefix="!", intents=intents)


bot = create_bot()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    api_key = os.getenv("SWGOH_API_KEY")
    if not api_key:
        print("WARNING: SWGOH_API_KEY not set. Commands will fail.")

    await kyrotech_setup(bot, api_key)
    await rote_setup(bot, api_key)
    await bonus_readiness_setup(bot)

    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} slash commands.")


def main():
    dotenv.load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables.")
        print("Add DISCORD_TOKEN to your .env file.")
        raise SystemExit(1)

    bot.run(token)


if __name__ == "__main__":
    main()
