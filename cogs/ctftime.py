import discord
from discord.ext import commands
import requests
from datetime import datetime

from config import TEAM_ID

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


async def setup(bot):
    await bot.add_cog(CTFTimeCommands(bot))