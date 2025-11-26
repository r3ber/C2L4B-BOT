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
import re
from datetime import datetime, timezone
import aiohttp


load_dotenv()
TOKEN = os.getenv("token")
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("announchannel"))

intents = discord.Intents.default()
intents.message_content = True
intents.guild_scheduled_events = True

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


class CTFCommands(commands.Cog, name="CTF Management Commands"):
    
    def __init__(self, bot):
        self.bot = bot


    def _get_clean_thread_name(self, thread_name: str) -> str:
        """Remove all status prefixes from thread name."""
        # Remove status prefixes
        clean_name = re.sub(r'^\[WIP\]\s*', '', thread_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'^\[SOLVED - MISSING WRITEUP\]\s*', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'^\[SOLVED - WRITEUP DONE\]\s*', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'^\[SOLVED\]\s*', '', clean_name, flags=re.IGNORECASE)
        # Also remove old format suffix
        clean_name = re.sub(r'\s*\[SOLVED\]$', '', clean_name, flags=re.IGNORECASE)
        return clean_name.strip()


    def _get_thread_status(self, thread_name: str) -> str:
        """Get current status of thread."""
        upper_name = thread_name.upper()
        if '[SOLVED - WRITEUP DONE]' in upper_name:
            return 'writeup_done'
        elif '[SOLVED - MISSING WRITEUP]' in upper_name:
            return 'solved'
        elif '[SOLVED]' in upper_name:
            return 'solved'
        elif '[WIP]' in upper_name:
            return 'wip'
        return 'open'


    async def _announce_solve(self, ctx, challenge_name: str, thread):
        """Announce solve in the announcements channel."""
        if not ANNOUNCEMENT_CHANNEL_ID:
            return
        
        try:
            channel = ctx.guild.get_channel(int(ANNOUNCEMENT_CHANNEL_ID))
            if channel:
                ctf_name = thread.parent.name if thread.parent else "Unknown CTF"
                await channel.send(
                    f'**{ctx.author.display_name}** resolveu o desafio '
                    f'**{challenge_name}** no CTF **{ctf_name}**! {thread.mention}'
                )
        except Exception as e:
            print(f'Error announcing solve: {e}')

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
        category = category.upper()
        thread_name = f'[{category}] {title}'
        thread = await ctf_channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
        await thread.send(description)
        await ctx.send(f'Challenge `{thread_name}` created! Use `!wip` when you start working on it.')
        print(f'Thread {thread_name} created in CTF channel {name_of_ctf}.')


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
        
        # Read-only permissions for @everyone
        await ctf_channel.set_permissions(
        ctx.guild.default_role,
        send_messages=False # Impede o role @everyone de enviar mensagens
        )

        await ctf_channel.edit(category=archived_category)
        print(f'CTF channel {name_of_ctf} moved to {archived_category_name}.')
    
    @commands.hybrid_command(name='wip', help='Marks the current challenge as Work In Progress.')
    @commands.has_role('Membros')
    async def mark_wip(self, ctx):
        """Marks the current thread as WIP (Work In Progress)."""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send('This command can only be used inside a challenge thread.')
            return
        
        thread = ctx.channel
        current_name = thread.name
        status = self._get_thread_status(current_name)
        
        if status == 'wip':
            await ctx.send('This challenge is already marked as WIP.')
            return
        
        if status in ['solved', 'writeup_done']:
            await ctx.send('This challenge is already solved. Use `!unsolved` first if you want to change the status.')
            return
        
        clean_name = self._get_clean_thread_name(current_name)
        new_name = f'[WIP] {clean_name}'
        
        if len(new_name) > 100:
            new_name = new_name[:100]
        
        await thread.edit(name=new_name)
        await ctx.send(f'**{ctx.author.display_name}** started working on this challenge!')


    @commands.hybrid_command(name='solved', help='Marks the current challenge thread as solved.')
    @commands.has_role('Membros')
    async def mark_solved(self, ctx):
        """Marks the current thread as solved (missing writeup)."""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send('This command can only be used inside a challenge thread.')
            return
        
        thread = ctx.channel
        current_name = thread.name
        status = self._get_thread_status(current_name)
        
        if status in ['solved', 'writeup_done']:
            await ctx.send('This challenge is already marked as solved.')
            return
        
        clean_name = self._get_clean_thread_name(current_name)
        new_name = f'[SOLVED - MISSING WRITEUP] {clean_name}'
        
        if len(new_name) > 100:
            new_name = new_name[:100]
        
        await thread.edit(name=new_name)
        
        # Update scoreboard
        scoreboard_cog = self.bot.get_cog('Team Scoreboard')
        msg_extra = ""
        if scoreboard_cog and thread.parent:
            ctf_channel_name = thread.parent.name
            total = scoreboard_cog.register_solve(
                user_id=ctx.author.id,
                user_name=ctx.author.display_name,
                ctf_name=ctf_channel_name
            )
            msg_extra = f' We have **{total}** total solves!'
        
        # Announce solve
        await self._announce_solve(ctx, clean_name, thread)
        
        await ctx.send(f'Challenge marked as solved! Remember to add a writeup later with `!writeup_done`.{msg_extra}')


    @commands.hybrid_command(name='writeup_done', help='Marks that the writeup for this challenge is complete.')
    @commands.has_role('Membros')
    async def mark_writeup_done(self, ctx):
        """Marks that the writeup for the solved challenge is complete."""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send('This command can only be used inside a challenge thread.')
            return
        
        thread = ctx.channel
        current_name = thread.name
        status = self._get_thread_status(current_name)
        
        if status == 'writeup_done':
            await ctx.send('This challenge already has a writeup marked as done.')
            return
        
        if status != 'solved':
            await ctx.send('This challenge must be marked as solved first. Use `!solved`.')
            return
        
        clean_name = self._get_clean_thread_name(current_name)
        new_name = f'[SOLVED - WRITEUP DONE] {clean_name}'
        
        if len(new_name) > 100:
            new_name = new_name[:100]
        
        await thread.edit(name=new_name)
        await ctx.send(f'Writeup marked as complete!')


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
        new_name = current_name
        for tag in ['[SOLVED - WRITEUP DONE]', '[SOLVED - MISSING WRITEUP]', '[SOLVED]']:
            new_name = new_name.replace(tag, '').strip()
        
        await thread.edit(name=new_name)
        await ctx.send(f'Solved mark removed from challenge.')

    @commands.hybrid_command(name='status', help='Shows the current status of the challenge thread.')
    @commands.has_role('Membros')
    async def show_status(self, ctx):
        """Shows the current status of the challenge thread."""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send('This command can only be used inside a challenge thread.')
            return
        
        thread = ctx.channel
        status = self._get_thread_status(thread.name)
        
        status_messages = {
            'open': 'Open - No one is working on this yet. Use `!wip` to start.',
            'wip': 'Work In Progress - Someone is working on this.',
            'solved': 'Solved - Missing Writeup. Use `!writeup_done` when writeup is ready.',
            'writeup_done': 'Solved - Writeup Done. Challenge complete!'
        }
        
        await ctx.send(f'**Status:** {status_messages.get(status, "Unknown")}')

    def _parse_ctftime_url(self, url: str) -> int | None:
        """Extract event ID from CTFTime URL or API URL."""
        # Match patterns like:
        # https://ctftime.org/api/v1/events/2869/
        # https://ctftime.org/event/2869/
        # https://ctftime.org/event/2869
        patterns = [
            r'ctftime\.org/api/v1/events/(\d+)',
            r'ctftime\.org/event/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return int(match.group(1))
        
        # If it's just a number
        if url.isdigit():
            return int(url)
        
        return None

    def _parse_ctftime_datetime(self, datetime_str: str) -> datetime:
        """Parse CTFTime datetime string to datetime object in UTC."""
        # CTFTime format: "2025-11-28T20:00:00+00:00"
        return datetime.fromisoformat(datetime_str.replace('+00:00', '+00:00'))

    def _format_duration(self, duration: dict) -> str:
        """Format duration dict to readable string."""
        days = duration.get('days', 0)
        hours = duration.get('hours', 0)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        
        return ' '.join(parts) if parts else 'Unknown'

    async def _fetch_json(self, url):
        """Fetch JSON data asynchronously to avoid blocking the bot."""
        async with aiohttp.ClientSession() as session:
            headers = {'User-Agent': 'C2L4B-BOT/1.0'}
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None, response.status
                try:
                    return await response.json(), 200
                except:
                    return None, 500

    @commands.hybrid_command(name='schedule', help='Creates a Discord event from a CTFTime event URL.')
    @commands.has_role('Membros')
    async def schedule_ctf(
        self,
        ctx,
        ctftime_url: str = commands.parameter(description="CTFTime event URL or API URL (e.g., https://ctftime.org/event/2869/)")
    ):
        """Creates a Discord scheduled event from CTFTime event data."""
        
        # Parse the event ID from URL
        event_id = self._parse_ctftime_url(ctftime_url)
        if not event_id:
            await ctx.send('Invalid CTFTime URL. Use format: `https://ctftime.org/event/EVENT_ID/`')
            return
        
        # Fetch event data from CTFTime API
        api_url = f'https://ctftime.org/api/v1/events/{event_id}/'
        
        event_data, status = await self._fetch_json(api_url)
        if status == 404:
            await ctx.send(f'Event {event_id} not found.')
            return
        if not event_data:
            await ctx.send(f'Failed to fetch data. Status: {status}')
            return
        # Extract event information
        title = event_data.get('title', 'Unknown CTF')
        start_str = event_data.get('start')
        finish_str = event_data.get('finish')
        description = event_data.get('description', '')
        logo_url = event_data.get('logo', '')
        ctf_format = event_data.get('format', 'Unknown')
        weight = event_data.get('weight', 0)
        url = event_data.get('url', '')
        ctftime_url_clean = event_data.get('ctftime_url', f'https://ctftime.org/event/{event_id}/')
        restrictions = event_data.get('restrictions', 'Unknown')
        prizes = event_data.get('prizes', '')
        duration = event_data.get('duration', {})
        organizers = event_data.get('organizers', [])
        onsite = event_data.get('onsite', False)
        location = event_data.get('location', '')
        
        if not start_str or not finish_str:
            await ctx.send('Event is missing start or end time.')
            return
        
        # Parse datetimes
        try:
            start_time = self._parse_ctftime_datetime(start_str)
            end_time = self._parse_ctftime_datetime(finish_str)
        except ValueError as e:
            await ctx.send(f'Failed to parse event times: {e}')
            return
        
        # Check if event is in the past
        if end_time < datetime.now(timezone.utc):
            await ctx.send('This event has already ended.')
            return
        
        # Build event description
        desc_parts = []
        
        # Add organizers
        if organizers:
            org_names = ', '.join([org.get('name', 'Unknown') for org in organizers])
            desc_parts.append(f"Organizers: {org_names}")
        
        # Add format and weight
        desc_parts.append(f"Format: {ctf_format}")
        desc_parts.append(f"Weight: {weight}")
        desc_parts.append(f"Duration: {self._format_duration(duration)}")
        desc_parts.append(f"Restrictions: {restrictions}")
        
        # Add location if onsite
        if onsite and location:
            desc_parts.append(f"Location: {location}")
        
        # Add prizes if available
        if prizes:
            desc_parts.append(f"Prizes: {prizes}")
        
        # Add links
        desc_parts.append("")
        if url:
            desc_parts.append(f"CTF Website: {url}")
        desc_parts.append(f"CTFTime: {ctftime_url_clean}")
        
        # Add original description (truncated if needed)
        if description:
            # Clean up description (remove Discord links, etc.)
            clean_desc = description.replace('\r\n', '\n').strip()
            if len(clean_desc) > 500:
                clean_desc = clean_desc[:497] + '...'
            desc_parts.append("")
            desc_parts.append(clean_desc)
        
        event_description = '\n'.join(desc_parts)
        
        # Discord event description limit is 1000 characters
        if len(event_description) > 1000:
            event_description = event_description[:997] + '...'
        
        image_data = None
        if logo_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(logo_url) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
            except:
                pass

        # Create the Discord scheduled event
        try:
            event_kwargs = {
                'name': title,
                'description': event_description,
                'start_time': start_time,
                'end_time': end_time,
                'entity_type': discord.EntityType.external,
                'location': url if url else ctftime_url_clean,
                'privacy_level': discord.PrivacyLevel.guild_only,
            }
            # Only add image if we successfully downloaded it
            if image_data:
                event_kwargs['image'] = image_data
            
            scheduled_event = await ctx.guild.create_scheduled_event(**event_kwargs)
            
            # Create confirmation embed
            embed = discord.Embed(
                title=f"Event Created: {title}",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Start",
                value=f"<t:{int(start_time.timestamp())}:F>",
                inline=True
            )
            embed.add_field(
                name="End",
                value=f"<t:{int(end_time.timestamp())}:F>",
                inline=True
            )
            embed.add_field(
                name="Duration",
                value=self._format_duration(duration),
                inline=True
            )
            embed.add_field(
                name="Format",
                value=ctf_format,
                inline=True
            )
            embed.add_field(
                name="Weight",
                value=str(weight),
                inline=True
            )
            embed.add_field(
                name="Restrictions",
                value=restrictions,
                inline=True
            )
            
            embed.add_field(
                name="Links",
                value=f"[CTF Website]({url})\n[CTFTime]({ctftime_url_clean})" if url else f"[CTFTime]({ctftime_url_clean})",
                inline=False
            )
            
            embed.set_footer(text=f"Event ID: {scheduled_event.id}")
            
            await ctx.send(f'Event scheduled successfully!', embed=embed)
            print(f'Scheduled event "{title}" created by {ctx.author.display_name}')
            
        except discord.Forbidden:
            await ctx.send('Bot does not have permission to create scheduled events.')
        except discord.HTTPException as e:
            await ctx.send(f'Failed to create event: {e}')


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

class ScoreboardCommands(commands.Cog, name="Team Scoreboard"):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = Path(__file__).parent / 'scoreboard.json'
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.data_file.exists():
            with open(self.data_file, 'w') as f:
                json.dump({}, f)

    def _load_data(self) -> dict:
        with open(self.data_file, 'r') as f:
            return json.load(f)

    def _save_data(self, data: dict):
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=4)

    def register_solve(self, user_id: int, user_name: str, ctf_name: str) -> int:
        """Register a solve for a user. Returns total solves."""
        data = self._load_data()
        str_id = str(user_id)

        if str_id not in data:
            data[str_id] = {
                "name": user_name,
                "total_solves": 0,
                "ctfs_participated": []
            }

        data[str_id]["name"] = user_name
        data[str_id]["total_solves"] += 1
        
        if ctf_name not in data[str_id]["ctfs_participated"]:
            data[str_id]["ctfs_participated"].append(ctf_name)

        self._save_data(data)
        return data[str_id]["total_solves"]

    @commands.hybrid_command(name='leaderboard', help='Shows the internal team ranking.')
    @commands.has_role('Membros')
    async def show_leaderboard(self, ctx):
        """Shows the team leaderboard."""
        data = self._load_data()
        
        if not data:
            await ctx.send("No stats available yet. Solve some challenges first!")
            return

        sorted_users = sorted(data.items(), key=lambda x: x[1]['total_solves'], reverse=True)

        embed = discord.Embed(
            title="Team Internal Scoreboard",
            color=discord.Color.gold()
        )

        rank_text = ""
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        
        for rank, (uid, stats) in enumerate(sorted_users[:10], start=1):
            prefix = medals.get(rank, f"#{rank}")
            n_ctfs = len(stats['ctfs_participated'])
            flags = stats['total_solves']
            
            rank_text += f"**{prefix}** {stats['name']}\n"
            rank_text += f"   Flags: {flags} | CTFs: {n_ctfs}\n\n"

        embed.description = rank_text if rank_text else "No data available."
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='profile', help='Shows stats for a specific user.')
    @commands.has_role('Membros')
    async def show_profile(self, ctx, member: discord.Member = None):
        """Shows profile stats for a user."""
        target = member or ctx.author
        data = self._load_data()
        str_id = str(target.id)

        if str_id not in data:
            await ctx.send(f"No stats found for {target.display_name}.")
            return

        stats = data[str_id]
        embed = discord.Embed(
            title=f"Stats: {stats['name']}", 
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Total Flags", value=str(stats['total_solves']), inline=True)
        embed.add_field(name="CTFs Joined", value=str(len(stats['ctfs_participated'])), inline=True)
        
        last_ctfs = stats['ctfs_participated'][-5:]
        if last_ctfs:
            embed.add_field(name="Recent Events", value="\n".join(last_ctfs), inline=False)

        await ctx.send(embed=embed)


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
    await bot.add_cog(ScoreboardCommands(bot))
    current_time = time.gmtime()
    year = current_time.tm_year
    month = current_time.tm_mon
    day = current_time.tm_mday
    hour = current_time.tm_hour
    minute = current_time.tm_min
    second = current_time.tm_sec
    print(f'{bot.user.name} has connected to Discord - {year}/{month}/{day} - {hour}:{minute}:{second}')


bot.run(TOKEN)