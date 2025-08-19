import discord

from discord.ext import commands
from sqlalchemy import create_engine
from . import models
from .books.cog import BookCircle


from sqlalchemy.event import listens_for
from sqlalchemy.engine import Engine
from discord.ext import commands


@listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


class Bot(commands.Bot):
    """
    Custom Bot class for Book Circle, attaches the database and loads the Cog.
    """
    def __init__(self, intents: discord.Intents) -> None:
        engine = create_engine("sqlite:///app.db", echo=True)
        models.Base.metadata.create_all(engine)
        self._cogs = [BookCircle(self, engine)]
        super().__init__(command_prefix="!", intents=intents)

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(embed=discord.Embed(
                title="Command not found",
                description=f"{error}. Type !help for a list of commands",
                color=discord.Color.red()
            ))

    async def setup_hook(self) -> None:
        for cog in self._cogs:
            await self.add_cog(cog)
