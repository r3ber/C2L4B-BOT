import discord
from discord.ext import commands
import time

from config import TOKEN
from cogs import (
    AdminCommands,
    CTFCommands,
    CTFTimeCommands,
    LibraryCommands,
    ScoreboardCommands,
    AIAssistantCommands
)

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.guild_scheduled_events = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """Bot startup event"""
    # Load all cogs
    await bot.add_cog(CTFCommands(bot))
    await bot.add_cog(AdminCommands(bot))
    await bot.add_cog(CTFTimeCommands(bot))
    await bot.add_cog(LibraryCommands(bot))
    await bot.add_cog(ScoreboardCommands(bot))
    await bot.add_cog(AIAssistantCommands(bot))
    
    # Log connection
    current_time = time.gmtime()
    timestamp = time.strftime('%Y/%m/%d - %H:%M:%S', current_time)
    print(f'{bot.user.name} has connected to Discord - {timestamp}')
    print(f'Loaded {len(bot.cogs)} cogs: {", ".join(bot.cogs.keys())}')


def main():
    """Main entry point"""
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\nShutting down bot...")
    except Exception as e:
        print(f"Error running bot: {e}")


if __name__ == "__main__":
    main()