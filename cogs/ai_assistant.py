import discord
from discord.ext import commands
import google.generativeai as genai
from config import GEMINI_API_KEY

class AIAssistantCommands(commands.Cog, name="AI Assistant Commands"):
    def __init__(self,bot):
        self.bot = bot
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')