import discord

from discord.ext import commands
from sqlalchemy import create_engine
from . import models
from .books.cog import BookCircle
from .achievements.cog import Achievements
from .genai.cog import GenAI


from sqlalchemy.event import listens_for
from sqlalchemy.engine import Engine
from discord.ext import commands


@listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


class Help(commands.Cog):
    @commands.command()
    async def help(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Book Circle Help",
            description="A quick guide to the main workflows and commands.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Getting Started",
            value="Join a book club channel or use `!club` to create a new one. Use `!read <progress>` to set your reading progress and `!caughtup` when you reach the current target.",
            inline=False,
        )
        embed.add_field(
            name="Suggesting & Reviewing Books",
            value="Suggest new books with `!suggest` and review finished books with `!review`. Track your reading journey!",
            inline=False,
        )
        embed.add_field(
            name="Notes and Quotes",
            value="Take notes on your reading and share quotes with `!note` and `!quote` commands. Read notes and quotes with `!notes` and `!quotes`.",
            inline=False,
        )
        embed.add_field(
            name="Achievements",
            value="Earn achievements for reading, catching up, writing notes, quotes, reviews, and more. Use `!achievements` to see your progress.",
            inline=False,
        )
        embed.add_field(
            name="Shame & Streaks",
            value="Stay on track! If you fall behind, you might get shamed. Keep up streaks for special rewards.",
            inline=False,
        )
        embed.add_field(
            name="Other Commands",
            value="Use `!help` to see this message again. Use `!info` learn more about the current book club",
            inline=False,
        )
        # Show admin commands only to admins in a guild
        if (
            isinstance(ctx.author, discord.Member)
            and ctx.author.guild_permissions.administrator
        ):
            embed.add_field(
                name="Admin Commands",
                value="- !shuffleroles: Shuffle member roles randomly.\n- !add @user: Add a new member to the book club.\n- !kick @user: Remove a member from the book club.",
                inline=False,
            )
        await ctx.send(embed=embed)


class Bot(commands.Bot):
    """
    Custom Bot class for Book Circle, attaches the database and loads the Cog.
    """

    def __init__(self, intents: discord.Intents) -> None:
        engine = create_engine("sqlite:///app.db", echo=False)
        models.Base.metadata.create_all(engine)
        self._cogs = [
            Help(),
            BookCircle(self, engine),
            Achievements(self, engine),
            GenAI(self, engine),
        ]
        super().__init__(command_prefix="!", intents=intents)
        self.remove_command("help")

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(
                embed=discord.Embed(
                    title="Command not found",
                    description=f"{error}. Type !help for a list of commands",
                    color=discord.Color.red(),
                )
            )

    async def setup_hook(self) -> None:
        for cog in self._cogs:
            await self.add_cog(cog)
