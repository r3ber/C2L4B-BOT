import discord
import os
from dotenv import load_dotenv
import time
from discord.ext import commands
import subprocess
import sys
import requests

load_dotenv()
TOKEN = os.getenv("token")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

class AdminCommands(commands.Cog, name="Admin Commands"):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='update', help='Pulls latest changes from git and reloads the bot (Admin only)')
    @commands.has_role('admin')
    async def update_bot(self, ctx):
        await ctx.send('Executing Git Pull...')
        
        try:
            # Executar o comando git pull
            result = subprocess.run(
                ['git', 'pull'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            # Mostrar output do git pull
            output = result.stdout if result.stdout else result.stderr
            await ctx.send(f'```\n{output}\n```')
            
            if result.returncode != 0:
                await ctx.send('Git pull failed!')
                return
            
            if 'Already up to date' in output:
                await ctx.send('Already up to date! No reload needed.')
                return
            
            # Recarregar o cogs
            await ctx.send('Reloading bot...')
            
            for cog_name in list(self.bot.cogs.keys()):
                await self.bot.remove_cog(cog_name)
            
            await self.bot.add_cog(CTFCommands(self.bot))
            await self.bot.add_cog(AdminCommands(self.bot))
            await self.bot.add_cog(CTFTimeCommands(self.bot))
            
            await ctx.send('Bot updated and reloaded successfully!')
            
        except Exception as e:
            await ctx.send(f'Error during update: {e}')
    
    @commands.command(name='reload', help='Reloads all Cogs (Admin only)')
    @commands.has_role('admin')
    async def reload_cogs(self, ctx):
        try:
            await ctx.send('Reloading cogs...')
            
            for cog_name in list(self.bot.cogs.keys()):
                await self.bot.remove_cog(cog_name)
            
            await self.bot.add_cog(CTFCommands(self.bot))
            await self.bot.add_cog(AdminCommands(self.bot))
            await self.bot.add_cog(CTFTimeCommands(self.bot))
            
            await ctx.send('Cogs reloaded successfully!')
        except Exception as e:
            await ctx.send(f'Error reloading: {e}')
    
    @commands.command(name='restart', help='Completely restarts the bot (Admin only)')
    @commands.has_role('admin')
    async def restart_bot(self, ctx):
        await ctx.send('Restarting bot...')
        os.execv(sys.executable, ['python3'] + sys.argv)


class CTFCommands(commands.Cog, name="CTF Management Commands"):
    def __init__(self, bot):
        self.bot = bot

    # Function to create a CTF (creates a channel in active-ctfs category with the name of the CTF)
    @commands.command(name='ctf_create', help='Creates a CTF channel inside the active-ctfs category.')
    @commands.has_role('Membros')
    async def create_ctf(
        self,
        ctx,
        name_of_ctf: str = commands.parameter(description="Name of the CTF")
        ):

        guild = ctx.guild
        category_name = 'active-ctfs'
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            category = await guild.create_category(category_name)
        await guild.create_text_channel(name_of_ctf, category=category)
        print(f'CTF channel {name_of_ctf} created in category {category_name}.')


    # Function to create a thread inside a CTF channel with given title ([CATEGORY] Title and the first message being the description)
    @commands.command(name='ctf_chal', help='Creates a challenge inside the provided CTF channel.')
    @commands.has_role('Membros')
    async def create_ctf_chal(
        self,
        ctx, 
        name_of_ctf: str = commands.parameter(description="Name of the CTF channel"),
        category: str = commands.parameter(description="Challenge category (e.g., Web, Crypto, PWN)"),
        title: str = commands.parameter(description="Challenge title"),
        description: str = commands.parameter(description="Challenge description")
        ):

        guild = ctx.guild
        category_name = 'active-ctfs'
        category_channel = discord.utils.get(guild.categories, name=category_name)
        if category_channel is None:
            await ctx.send(f'Category {category_name} does not exist.')
            return
        ctf_channel = discord.utils.get(category_channel.channels, name=name_of_ctf)
        if ctf_channel is None:
            await ctx.send(f'CTF channel {name_of_ctf} does not exist.')
            return
        thread_name = f'[{category}] {title}'
        thread = await ctf_channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
        await thread.send(description)
        print(f'Thread {thread_name} created in CTF channel {name_of_ctf} with description: {description}.')
    

    @commands.command(name='ctf_archive', help='Archives a CTF channel by moving it to archived-ctfs category.')
    @commands.has_role('Membros')
    async def archive_ctf(
        self,
        ctx,
        name_of_ctf: str = commands.parameter(description="Name of the CTF to archive")
        ):
        guild = ctx.guild
        active_category_name = 'active-ctfs'
        archived_category_name = 'archived-ctfs'

        #Get active_ctfs category
        active_category = discord.utils.get(guild.categories, name=active_category_name)
        if active_category is None:
            await ctx.send(f'Category {active_category_name} does not exist.')
            return
        # Find the CTF channel in active-ctfs
        ctf_channel = discord.utils.get(active_category.channels, name=name_of_ctf)
        if ctf_channel is None:
            await ctx.send(f'CTF channel {name_of_ctf} does not exist in {active_category_name}.')
            return
        
        # Get or create archived-ctfs category
        archived_category = discord.utils.get(guild.categories, name=archived_category_name)
        if archived_category is None:
            archived_category = await guild.create_category(archived_category_name)
        
        await ctf_channel.edit(category=archived_category)
        print(f'CTF channel {name_of_ctf} moved to {archived_category_name}.')
        
class CTFTimeCommands(commands.Cog, name="CTFTime Commands"):
    def __init__(self, bot):
        self.bot = bot

    #Function to get top 10 CTF teams from CTFTime for a given country code
    @commands.command(name='ctftime_top_portugal', help='Gets the top 10 CTF teams from Portugal.')
    @commands.has_role('Membros')
    async def ctftime_top_portugal(self, ctx):
        try:
            url = 'https://ctftime.org/api/v1/top-by-country/pt/'
            response = requests.get(url)
            
            if response.status_code != 200:
                await ctx.send('Failed to retrieve data from CTFTime.')
                return
            
            teams = response.json()
            
            # The API returns a list of teams directly
            if not teams or not isinstance(teams, list):
                await ctx.send('No team data available for Portugal.')
                return
            
            # Create embed
            embed = discord.Embed(
                title='🇵🇹 Top CTF Teams from Portugal',
                color=discord.Color.green()
            )
            
            # Add teams to embed
            team_list = []
            for team in teams[:10]:
                country_place = team.get('country_place', '?')
                team_name = team.get('team_name', 'Unknown')
                points = team.get('points', 0)
                place = team.get('place', '?')
                events = team.get('events', 0)
                team_list.append(
                    f"**{country_place}.** {team_name}\n"
                    f"   └ {points:.2f} pts | Global: #{place} | Events: {events}"
                )
            
            embed.description = '\n'.join(team_list)
            embed.set_footer(text='Data from CTFTime API • Current Year Rankings')
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f'Error retrieving top teams: {e}')
    
    #Function to get information about our team from CTFTime
    @commands.command(name='ctftime_team_info', help='Gets details of our CTF team from CTFTime.')
    @commands.has_role('Membros')
    async def ctftime_team_info(self, ctx):
        try:
            url = 'https://ctftime.org/api/v1/teams/412730/'
            response = requests.get(url)
            
            if response.status_code != 200:
                await ctx.send('Failed to retrieve data from CTFTime.')
                return
            
            team = response.json()
            
            # Create embed
            embed = discord.Embed(
                title=team.get('name', 'Unknown Team'),
                url=f"https://ctftime.org/team/{team.get('id', '')}",
                color=discord.Color.orange()
            )
            
            # Add logo if available
            if team.get('logo'):
                embed.set_thumbnail(url=team['logo'])
            
            # Add team details
            embed.add_field(name='🌍 Country', value=team.get('country', 'N/A'), inline=True)
            
            # Handle rating - it's a nested dict with years containing country_place
            rating = team.get('rating', {})
            if isinstance(rating, dict) and rating:
                # Get the most recent year's rating
                years_with_data = [year for year in rating.keys() if rating[year]]
                if years_with_data:
                    latest_year = max(years_with_data)
                    country_place = rating[latest_year].get('country_place', 'N/A')
                    rating_value = f"#{country_place} in PT ({latest_year})"
                else:
                    rating_value = 'N/A'
            else:
                rating_value = 'N/A'
            embed.add_field(name='⭐ Country Ranking', value=rating_value, inline=True)
            
            # Add academic and university info
            if team.get('academic'):
                university = team.get('university', 'N/A')
                embed.add_field(name='🎓 University', value=university, inline=False)
                
                university_website = team.get('university_website', '')
                if university_website:
                    embed.add_field(name='🔗 University Website', value=university_website, inline=False)
            
            # Add aliases if available
            aliases = team.get('aliases', [])
            primary_alias = team.get('primary_alias', '')
            
            if primary_alias or aliases:
                alias_text = primary_alias if primary_alias else ', '.join(aliases) if aliases else 'None'
                embed.add_field(name='📝 Aliases', value=alias_text, inline=False)
            
            # Add historical rankings summary
            if isinstance(rating, dict) and rating:
                years_with_data = [(year, rating[year].get('country_place')) 
                                  for year in sorted(rating.keys(), reverse=True) 
                                  if rating[year] and rating[year].get('country_place')]
                
                if years_with_data:
                    history = '\n'.join([f"{year}: #{place} in PT" 
                                       for year, place in years_with_data[:5]])
                    embed.add_field(name='📊 Recent Rankings', value=history, inline=False)
            
            embed.set_footer(text='Data from CTFTime API')
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f'Error retrieving team information: {e}')

# Log when bot connects to Discord with time and date
@bot.event
async def on_ready():
    await bot.add_cog(CTFCommands(bot))
    await bot.add_cog(AdminCommands(bot))
    await bot.add_cog(CTFTimeCommands(bot))
    current_time = time.gmtime()
    year = current_time.tm_year
    month = current_time.tm_mon
    day = current_time.tm_mday
    hour = current_time.tm_hour
    minute = current_time.tm_min
    second = current_time.tm_sec
    print(f'{bot.user.name} has connected to Discord - {year}/{month}/{day} - {hour}:{minute}:{second}')


bot.run(TOKEN)