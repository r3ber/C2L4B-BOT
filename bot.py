import discord
import os
from dotenv import load_dotenv
import time
from discord.ext import commands
import subprocess
import sys
import requests
import json
from pathlib import Path

load_dotenv()
TOKEN = os.getenv("token")
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("announchannel"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

class AdminCommands(commands.Cog, name="Admin Commands"):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='sync', help='Syncs slash commands with Discord (Admin only)')
    @commands.has_role('admin') # Ou o role que uses para admin
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
    
    @commands.hybrid_command(name='reload', help='Reloads all Cogs (Admin only)')
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
    
    @commands.hybrid_command(name='restart', help='Completely restarts the bot (Admin only)')
    @commands.has_role('admin')
    async def restart_bot(self, ctx):
        await ctx.send('Restarting bot...')
        os.execv(sys.executable, ['python3'] + sys.argv)


class CTFCommands(commands.Cog, name="CTF Management Commands"):
    def __init__(self, bot):
        self.bot = bot

    # Function to create a CTF (creates a channel in active-ctfs category with the name of the CTF)
    @commands.hybrid_command(name='ctf_create', help='Creates a CTF channel inside the active-ctfs category.')
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
    @commands.hybrid_command(name='ctf_chal', help='Creates a challenge inside the provided CTF channel.')
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
    

    @commands.hybrid_command(name='ctf_archive', help='Archives a CTF channel by moving it to archived-ctfs category.')
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
        
    @commands.hybrid_command(name='solved', help='Marks the current challenge thread as solved.')
    @commands.has_role('Membros')
    async def mark_solved(self, ctx):
        """Marks the current thread as solved by adding [SOLVED] to the title."""
        # Check if the command is being used inside a thread
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send('This command can only be used inside a challenge thread.')
            return
        
        thread = ctx.channel
        current_name = thread.name
        
        # Check if already marked as solved
        if '[SOLVED]' in current_name.upper():
            await ctx.send('This challenge is already marked as solved.')
            return
        
        # Add [SOLVED] to the end of the thread name
        new_name = f'{current_name} [SOLVED]'
        
        # Discord thread names have a 100 character limit
        if len(new_name) > 100:
            new_name = new_name[:100]
        
        await thread.edit(name=new_name)
        await ctx.send(f'Challenge marked as solved!')

    @commands.hybrid_command(name='unsolved', help='Removes the solved mark from the current challenge thread.')
    @commands.has_role('Membros')
    async def mark_unsolved(self, ctx):
        """Removes the [SOLVED] mark from the current thread."""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send('This command can only be used inside a challenge thread.')
            return
        
        thread = ctx.channel
        current_name = thread.name
        
        # Check if it has the solved mark
        if '[SOLVED]' not in current_name.upper():
            await ctx.send('This challenge is not marked as solved.')
            return
        
        # Remove [SOLVED] from the name (case insensitive)
        import re
        new_name = re.sub(r'\s*\[SOLVED\]', '', current_name, flags=re.IGNORECASE).strip()
        
        await thread.edit(name=new_name)
        await ctx.send(f'Solved mark removed from challenge.')

class CTFTimeCommands(commands.Cog, name="CTFTime Commands"):
    def __init__(self, bot):
        self.bot = bot

    #Function to get top 10 CTF teams from CTFTime for a given country code
    @commands.hybrid_command(name='ctftime_top_portugal', help='Gets the top 10 CTF teams from Portugal.')
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
    @commands.hybrid_command(name='ctftime_team_info', help='Gets details of our CTF team from CTFTime.')
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


class LibraryCommands(commands.Cog, name="Library Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.library_path = Path(__file__).parent / 'great-library'
    

    def _load_index(self) -> dict:
        """Load the library index."""
        index_path = self.library_path / 'index.json'
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    

    def _find_file(self, name: str) -> Path | None:
        """Find a markdown file in the library by name."""
        for md_file in self.library_path.rglob('*.md'):
            if md_file.stem.lower() == name.lower():
                return md_file
        return None


    def _parse_sections(self, content: str) -> dict[str, str]:
        """Parse markdown content into sections by ## headers."""
        sections = {}
        current_section = 'overview'
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_content:
                    sections[current_section.lower()] = '\n'.join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            elif line.startswith('# '):
                continue
            else:
                current_content.append(line)
        
        if current_content:
            sections[current_section.lower()] = '\n'.join(current_content).strip()
        
        return sections
    

    def _truncate_content(self, content: str, max_length: int = 1900) -> str:
        """Truncate content to fit Discord's message limit."""
        if len(content) <= max_length:
            return content
        return content[:max_length] + '\n\n*... (truncated, use section parameter for specific parts)*'
    
    @commands.hybrid_command(name='lib', help='Search the library. Usage: !lib <name> [section]')
    @commands.has_role('Membros')
    async def library_search(
        self,
        ctx,
        name: str = commands.parameter(description="Name of the entry (e.g., nmap, rsa, assemblyx86)"),
        section: str = commands.parameter(default=None, description="Specific section (e.g., 'basic scans')")
    ):
        """Search for an entry in the library, optionally specifying a section."""
        file_path = self._find_file(name)
        
        if not file_path:
            await ctx.send(f'Entry `{name}` not found in the library.')
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = self._parse_sections(content)
        
        if section:
            section_key = section.lower()
            matching_sections = [k for k in sections.keys() if section_key in k.lower()]
            
            if not matching_sections:
                available = ', '.join(f'`{s}`' for s in sections.keys())
                await ctx.send(f'Section `{section}` not found.\nAvailable sections: {available}')
                return
            
            section_key = matching_sections[0]
            section_content = sections[section_key]
            
            embed = discord.Embed(
                title=f'{name.upper()} - {section_key.title()}',
                description=self._truncate_content(section_content),
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title=f'{name.upper()}',
                color=discord.Color.blue()
            )
            
            if sections:
                first_section = list(sections.values())[0]
                embed.description = self._truncate_content(first_section, 500)
            
            section_list = '\n'.join(f'- `{s}`' for s in sections.keys())
            embed.add_field(
                name='Available Sections',
                value=section_list or 'No sections found',
                inline=False
            )
            embed.set_footer(text=f'Use !lib {name} <section> for specific content')
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='lib_list', help='List all available entries in the library.')
    @commands.has_role('Membros')
    async def library_list(self, ctx):
        """List all entries available in the library."""
        index = self._load_index()
        
        embed = discord.Embed(
            title='Great Library - Available Entries',
            color=discord.Color.gold()
        )
        
        if index.get('categories'):
            for cat_id, cat_data in index['categories'].items():
                entries = cat_data.get('tools', [])
                if entries:
                    entry_list = ', '.join(f'`{e}`' for e in entries)
                    embed.add_field(
                        name=cat_data.get('name', cat_id),
                        value=entry_list,
                        inline=False
                    )
        else:
            entries = [f.stem for f in self.library_path.rglob('*.md')]
            if entries:
                embed.description = ', '.join(f'`{e}`' for e in sorted(entries))
            else:
                embed.description = 'No entries found in the library.'
        
        embed.set_footer(text='Use !lib <name> to view an entry')
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='lib_sections', help='List sections of an entry.')
    @commands.has_role('Membros')
    async def library_sections(
        self,
        ctx,
        name: str = commands.parameter(description="Entry name")
    ):
        """List all sections available for an entry."""
        file_path = self._find_file(name)
        
        if not file_path:
            await ctx.send(f'Entry `{name}` not found.')
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = self._parse_sections(content)
        
        embed = discord.Embed(
            title=f'{name.upper()} - Sections',
            description='\n'.join(f'- `{s}`' for s in sections.keys()),
            color=discord.Color.purple()
        )
        embed.set_footer(text=f'Use !lib {name} <section> to view')
        await ctx.send(embed=embed)


# Log when bot connects to Discord with time and date
@bot.event
async def on_ready():
    await bot.add_cog(CTFCommands(bot))
    await bot.add_cog(AdminCommands(bot))
    await bot.add_cog(CTFTimeCommands(bot))
    await bot.add_cog(LibraryCommands(bot))
    current_time = time.gmtime()
    year = current_time.tm_year
    month = current_time.tm_mon
    day = current_time.tm_mday
    hour = current_time.tm_hour
    minute = current_time.tm_min
    second = current_time.tm_sec
    print(f'{bot.user.name} has connected to Discord - {year}/{month}/{day} - {hour}:{minute}:{second}')


bot.run(TOKEN)