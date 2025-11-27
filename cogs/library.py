import discord
from discord.ext import commands
import json
from pathlib import Path

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