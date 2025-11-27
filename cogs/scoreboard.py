import discord
from discord.ext import commands
import json
from pathlib import Path



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
