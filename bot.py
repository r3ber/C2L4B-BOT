import discord
from discord.ext import commands
import time

from config import TOKEN
from cogs import (
    AdminCommands,
    CTFCommands,
    CTFTimeCommands,
    LibraryCommands,
    ScoreboardCommands
)

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.guild_scheduled_events = True
intents.members = True

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
    
    # Log connection
    current_time = time.gmtime()
    timestamp = time.strftime('%Y/%m/%d - %H:%M:%S', current_time)
    print(f'{bot.user.name} has connected to Discord - {timestamp}')
    print(f'Loaded {len(bot.cogs)} cogs: {", ".join(bot.cogs.keys())}')

@bot.event
async def on_member_join(member):
    """Welcome message when a new member joins"""
    # Encontra o canal de boas-vindas (ajusta o nome do canal)
    welcome_channel = discord.utils.get(member.guild.text_channels, name='welcome')
    
    if not welcome_channel:
        # Se não existir canal "welcome", usa o canal geral
        welcome_channel = discord.utils.get(member.guild.text_channels, name='general')
    
    if welcome_channel:
        # Cria embed de boas-vindas
        embed = discord.Embed(
            title=f"Bem-vindo(a) ao {member.guild.name}! 🎉",
            description=f"Olá {member.mention}! Bem-vindo à nossa comunidade de CTF!",
            color=discord.Color.green()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(
            name="📚 Sobre Nós",
            value="Somos o C2L4B, uma equipa de CTF focada em aprender e competir juntos!",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Primeiros Passos",
            value=(
                "1. Usa `!help` para ver os comandos disponíveis\n"
                "2. Participa connosco nas reuniões e nas competições de CTF!"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Membro #{member.guild.member_count}")
        
        await welcome_channel.send(f"👋 {member.mention}", embed=embed)
        
        print(f"New member joined: {member.name} ({member.id})")


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