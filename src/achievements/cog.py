import asyncio
import logging

import discord
from discord.ext import commands

from . import listener
from .service import AchievementService, load_achievements_from_json


class Achievements(commands.Cog):
    def __init__(self, bot, engine):
        self.bot = bot
        self.engine = engine
        self.achievement_service = AchievementService(engine)

        # Start the listener.
        self.listener_collection = listener.ListenerCollection(engine)
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Achievements Cog is ready.")
        # Load achievement definitions from JSON files
        
        try:
            asyncio.create_task(
                asyncio.to_thread(load_achievements_from_json, self.engine)
            )
        except Exception:
            logging.exception("Failed to schedule achievements startup tasks")


    @commands.command()
    async def achievements(self, ctx):
        """List your achievements."""
        user_id = ctx.author.id
        achievements = self.achievement_service.get_user_achievements(user_id)
        if not achievements:
            await ctx.send("You have no achievements yet.")
            return
        embed = discord.Embed(title="Your Achievements", color=discord.Color.green())
        for ach in achievements:
            embed.add_field(name=ach.name, value=ach.description, inline=False)
        await ctx.send(embed=embed)
