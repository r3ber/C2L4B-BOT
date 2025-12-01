import discord
from discord.ext import commands
import google.generativeai as genai
from config import GEMINI_API_KEY

class AIAssistantCommands(commands.Cog, name="AI Assistant Commands"):
    def __init__(self,bot):
        self.bot = bot
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')

    @commands.hybrid_command(name='writeup_assist', help='AI assistant for formatting writeups')
    @commands.has_role('Membros')
    async def writeup_assist(self, ctx, *, content: str):
        """Help format and structure a CTF writeup."""
        
        prompt = f"""You are a CTF writeup assistant. Format this writeup professionally:

{content}

Structure it with:
1. Challenge Overview
2. Reconnaissance
3. Exploitation
4. Flag
5. Lessons Learned

Use Markdown formatting. Be concise and technical."""
        
        await ctx.send("A gerar o teu write-up maroto hehe...")

        try:
            response = self.model.generate_content(prompt)
            
            # Split long responses
            if len(response.text) > 1900:
                chunks = [response.text[i:i+1900] for i in range(0, len(response.text), 1900)]
                for chunk in chunks:
                    await ctx.send(f"```markdown\n{chunk}\n```")
            else:
                await ctx.send(f"```markdown\n{response.text}\n```")
                
        except Exception as e:
            await ctx.send(f"Error generating writeup: {e}")

async def setup(bot):
    await bot.add_cog(AIAssistantCommands(bot))