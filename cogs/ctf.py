import discord
from discord.ext import commands
import requests
from datetime import datetime
import re
import aiohttp
from config import ANNOUNCEMENT_CHANNEL_ID
from datetime import datetime, timezone
from urllib.parse import quote

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
    
    def generate_google_calendar_link(self, title: str, start_time: datetime, end_time: datetime, description: str, location: str) -> str:
        """Generate a Google Calendar event link."""
        
        #convert to google calendar format
        start_str = start_time.strftime('%Y%m%dT%H%M%SZ')
        end_str = end_time.strftime('%Y%m%dT%H%M%SZ')

        title_encoded = quote(title)
        desc_encoded = quote(description[:1000])
        location_encoded = quote(location)
        
        url = f"https://calendar.google.com/calendar/render?action=TEMPLATE"
        url += f"&text={title_encoded}"
        url += f"&dates={start_str}/{end_str}"
        url += f"&details={desc_encoded}"
        if location:
            url += f"&location={location_encoded}"
        
        return url
    
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

            #generate google calendar link
            gcal_description = f"CTF Event\n\n{description[:500] if description else ''}\n\nCTFTime: {ctftime_url_clean}"
            if url:
                gcal_description += f"\nWebsite: {url}"

            gcal_link = self.generate_google_calendar_link(
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=gcal_description,
                location=url if url else ctftime_url_clean
            )

            embed.add_field(
                name="Add to Google Calendar",
                value=f"[Add to Google Calendar]({gcal_link})",
                inline=False
            )
            
            embed.set_footer(text=f"Event ID: {scheduled_event.id}")
            
            await ctx.send(f'Event scheduled successfully!', embed=embed)
            print(f'Scheduled event "{title}" created by {ctx.author.display_name}')

            
        except discord.Forbidden:
            await ctx.send('Bot does not have permission to create scheduled events.')
        except discord.HTTPException as e:
            await ctx.send(f'Failed to create event: {e}')

    @commands.hybrid_command(name='export_event', help='Export a Discord scheduled event to Google Calendar.')
    @commands.has_role('Membros')
    async def export_event(
        self,
        ctx,
        event_id: str = commands.parameter(description="Discord event ID (found in event details)")
    ):
        """Export an existing Discord scheduled event to Google Calendar."""
        try:
            event = await ctx.guild.fetch_scheduled_event(int(event_id))
        except (ValueError, discord.NotFound):
            await ctx.send('Event not found. Make sure you provided a valid event ID.')
            return
        except discord.HTTPException as e:
            await ctx.send(f'Failed to fetch event: {e}')
            return
        
        # Build description
        description = event.description or "CTF Event scheduled via Discord"
        if event.location:
            description += f"\n\nLocation: {event.location}"
        
        # Generate Google Calendar link
        gcal_link = self.generate_google_calendar_link(
            title=event.name,
            start_time=event.start_time,
            end_time=event.end_time,
            description=description,
            location=event.location or ""
        )
        
        embed = discord.Embed(
            title=f"📅 Export: {event.name}",
            description=f"Click the link below to add this event to your Google Calendar",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Start",
            value=f"<t:{int(event.start_time.timestamp())}:F>",
            inline=True
        )
        embed.add_field(
            name="End",
            value=f"<t:{int(event.end_time.timestamp())}:F>",
            inline=True
        )
        
        embed.add_field(
            name="Add to Google Calendar",
            value=f"[Click here to add]({gcal_link})",
            inline=False
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CTFCommands(bot))