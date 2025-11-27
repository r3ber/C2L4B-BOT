import discord
from discord.ext import commands
import subprocess
import sys
import os


class AdminCommands(commands.Cog, name="Admin Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='sync', help='Syncs slash commands with Discord (Admin only)')
    @commands.has_role('admin')
    async def sync_tree(self, ctx):
        await ctx.send('Syncing slash commands...')
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f'Synced {len(synced)} command(s)!')
        except Exception as e:
            await ctx.send(f'Failed to sync: {e}')

    @commands.hybrid_command(name='update', help='Pulls latest changes from git and reloads the bot (Admin only)')
    @commands.has_role('admin')
    async def update_bot(self, ctx):
        await ctx.send('Executing Git Pull...')
        
        try:
            result = subprocess.run(
                ['git', 'pull'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            output = result.stdout if result.stdout else result.stderr
            await ctx.send(f'```\n{output}\n```')
            
            if result.returncode != 0:
                await ctx.send('Git pull failed!')
                return
            
            if 'Already up to date' in output:
                await ctx.send('Already up to date! No reload needed.')
                return
            
            await ctx.send('Reloading bot...')
            
            # Reload all cogs
            from cogs import AdminCommands, CTFCommands, CTFTimeCommands, LibraryCommands, ScoreboardCommands
            
            for cog_name in list(self.bot.cogs.keys()):
                await self.bot.remove_cog(cog_name)
            
            await self.bot.add_cog(CTFCommands(self.bot))
            await self.bot.add_cog(AdminCommands(self.bot))
            await self.bot.add_cog(CTFTimeCommands(self.bot))
            await self.bot.add_cog(LibraryCommands(self.bot))
            await self.bot.add_cog(ScoreboardCommands(self.bot))
            
            await ctx.send('Bot updated and reloaded successfully!')
            
        except Exception as e:
            await ctx.send(f'Error during update: {e}')

    @commands.hybrid_command(name='reload', help='Reloads all Cogs (Admin only)')
    @commands.has_role('admin')
    async def reload_cogs(self, ctx):
        try:
            await ctx.send('Reloading cogs...')
            
            from cogs import AdminCommands, CTFCommands, CTFTimeCommands, LibraryCommands, ScoreboardCommands
            
            for cog_name in list(self.bot.cogs.keys()):
                await self.bot.remove_cog(cog_name)
            
            await self.bot.add_cog(CTFCommands(self.bot))
            await self.bot.add_cog(AdminCommands(self.bot))
            await self.bot.add_cog(CTFTimeCommands(self.bot))
            await self.bot.add_cog(LibraryCommands(self.bot))
            await self.bot.add_cog(ScoreboardCommands(self.bot))
            
            await ctx.send('Cogs reloaded successfully!')
        except Exception as e:
            await ctx.send(f'Error reloading: {e}')

    @commands.hybrid_command(name='restart', help='Completely restarts the bot (Admin only)')
    @commands.has_role('admin')
    async def restart_bot(self, ctx):
        await ctx.send('Restarting bot...')
        await self.bot.close()
        os.execv(sys.executable, ['python3'] + sys.argv)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))