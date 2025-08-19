import discord
import asyncio
import logging

from functools import wraps
from typing import Optional
from discord.ext import commands
from sqlalchemy.orm import Session

from ..result_types import *
from .model import BookClub, BookClubReaderRole, BookClubReaderState, BookState
from .rotate_roles import rotate_roles
from .service import BookCircleService


def send_embed(func):
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        match await func(self, ctx, *args, **kwargs):
            case Ok(embed):
                await ctx.send(embed=embed)
            case Err(msg):
                await ctx.send(
                    embed=discord.Embed(
                        title="Error", description=f"{msg}", color=discord.Color.red()
                    )
                )

    return wrapper



class BookCircle(commands.Cog):
    async def background_shame_task(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    try:
                        with Session(self.engine) as session:
                            club = session.get(BookClub, channel.id)
                            if not club:
                                continue
                            not_caught_up = [
                                r
                                for r in club.readers
                                if r.state != BookClubReaderState.CAUGHT_UP
                            ]
                            if not not_caught_up:
                                continue
                            mentions = [f"<@{r.user.id}>" for r in not_caught_up]
                            await channel.send(
                                embed=discord.Embed(
                                    title="⏰ Shame!",
                                    description=f"The following readers have not caught up: {', '.join(mentions)}",
                                    color=discord.Color.red(),
                                )
                            )
                    except Exception:
                        logging.exception(
                            f"Error in shame background task for channel {channel.id}"
                        )
            await asyncio.sleep(12 * 60 * 60)  # 12 hours

    @commands.command()
    async def shame(self, ctx: commands.Context):
        """Mention everyone who has not caught up to the current target."""
        with Session(self.engine) as session:
            club = session.get(BookClub, ctx.channel.id)
            if not club:
                await ctx.send(
                    embed=discord.Embed(
                        title="Error",
                        description="Book club not found.",
                        color=discord.Color.red(),
                    )
                )
                return
            not_caught_up = [
                r for r in club.readers if r.state != BookClubReaderState.CAUGHT_UP
            ]
            if not not_caught_up:
                await ctx.send(
                    embed=discord.Embed(
                        title="🎉 Everyone is caught up!",
                        description="Great job, everyone!",
                        color=discord.Color.green(),
                    )
                )
                return
            mentions = []
            for reader in not_caught_up:
                user = reader.user
                mentions.append(f"<@{user.id}>")
            await ctx.send(
                embed=discord.Embed(
                    title="⏰ Shame!",
                    description=f"The following readers have not caught up: {', '.join(mentions)}",
                    color=discord.Color.red(),
                )
            )

    def __init__(self, bot: commands.Bot, engine):
        self.bot = bot
        self.engine = engine
        self.service = BookCircleService(engine)
        self.roles = {
            r.name for r in BookClubReaderRole if r != BookClubReaderRole.NONE
        }
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Event handler for when the bot is ready."""
        self.bot.loop.create_task(self.background_shame_task())

        for guild in self.bot.guilds:
            existing = {role.name for role in guild.roles}
            for role in self.roles - existing:
                await guild.create_role(
                    name=role, hoist=True, color=discord.Color.random()
                )

    def __roles_from_guild(self, guild: discord.Guild) -> dict[str, discord.Role]:
        """Create a mapping from name to guild role."""
        return {role.name: role for role in guild.roles if role.name in self.roles}

    @commands.command()
    @send_embed
    @commands.has_permissions(administrator=True)
    async def rotateroles(self, ctx: commands.Context):
        """Rotate roles among all readers in this book club (admin only)."""
        match r := rotate_roles(self.engine, ctx.channel.id):
            case Ok():
                await self.__synchronize_roles(ctx)
        return r

    @commands.command()
    async def roleinfo(self, ctx: commands.Context):
        """Show information about the possible roles in this book club."""
        role_descriptions = {
            BookClubReaderRole.FACILITATOR: "🧑‍💼 Leads the discussion and keeps the group on track.",
            BookClubReaderRole.SUMMARIZER: "📝 Summarizes the chapters or sections read.",
            BookClubReaderRole.QUOTE_PICKER: "💬 Selects and shares memorable quotes.",
            BookClubReaderRole.THEME_SPOTTER: "🔎 Identifies and discusses themes in the book.",
            BookClubReaderRole.LINK_FINDER: "🔗 Finds and shares relevant links or resources.",
            BookClubReaderRole.DEVILS_ADVOCATE: "😈 Challenges ideas and encourages debate.",
            BookClubReaderRole.DETAIL_SPOTTER: "🧐 Notices and brings up interesting details.",
            BookClubReaderRole.MOOD_SPOTTER: "🎭 Comments on the mood, tone, and atmosphere.",
        }
        embed = discord.Embed(title="Book Club Roles", color=discord.Color.blue())
        for role in BookClubReaderRole:
            if role == BookClubReaderRole.NONE:
                continue
            name = role.name.title().replace("_", " ")
            desc = role_descriptions.get(role, role.value)
            embed.add_field(name=name, value=desc, inline=False)
        await ctx.send(embed=embed)

    async def __synchronize_roles(self, ctx):
        """Synchronize roles for all members in the book club."""
        guild = ctx.guild
        if guild is None:
            await ctx.send("This command must be used in a server.")
            return

        # Map role names to discord.Role objects
        role_objs = self.__roles_from_guild(guild)

        # Get all BookClubReader roles from the database for this club
        club_id = ctx.channel.id
        with Session(self.engine) as session:
            club = session.get(BookClub, club_id)
            if not club:
                await ctx.send("Book club not found.")
                return
            user_roles = {r.user_id: r.role.value.upper() for r in club.readers}

        logging.info(
            f"Synchronizing roles for book club {club_id} with {len(ctx.channel.members)} members."
        )
        try:
            for member in ctx.channel.members:
                if member.bot:
                    continue
                # Remove all book club roles
                to_remove = [role_objs[name] for name in self.roles]
                # Add the correct role if assigned
                role_name = user_roles.get(member.id)
                if role_name and role_name in role_objs:
                    await member.edit(
                        roles=[role for role in member.roles if role not in to_remove]
                        + [role_objs[role_name]]
                    )
        except Exception as e:
            logging.error(f"Error synchronizing roles: {e}")

    @commands.command()
    @send_embed
    @commands.has_permissions(administrator=True)
    async def shuffleroles(self, ctx: commands.Context):
        """Randomly assign roles to all readers in this book club (admin only)."""
        match r := self.service.shuffle_roles(ctx.channel.id):
            case Ok():
                logging.info(f"Roles shuffled in channel {ctx.channel.id}")
                await self.__synchronize_roles(ctx)
        return r

    @commands.command()
    @send_embed
    async def mybooks(self, ctx: commands.Context) -> Result[discord.Embed]:
        """Show all books you have read in any book club."""
        return self.service.get_books_for_user(ctx.author)

    @commands.command()
    @send_embed
    async def reviews(self, ctx: commands.Context):
        """Show all reviews for the current book club."""
        return self.service.get_reviews(ctx.channel.id)

    @commands.command()
    @send_embed
    async def notes(self, ctx: commands.Context):
        """Show all notes for the current book club."""
        return self.service.get_notes(ctx.channel.id)

    @commands.command()
    @send_embed
    async def quotes(self, ctx: commands.Context):
        """Show all quotes for the current book club."""
        return self.service.get_quotes(ctx.channel.id)

    @commands.command()
    @send_embed
    @commands.has_permissions(administrator=True)
    async def add(self, ctx: commands.Context):
        """Add a member to the book club in this channel (admin only)."""
        if not ctx.message.mentions:
            return Err("You must mention a user to add them.")
        return self.service.join_club(ctx.channel.id, ctx.message.mentions[0])

    @commands.command()
    @send_embed
    async def join(self, ctx: commands.Context):
        """Join the book club in this channel."""
        return self.service.join_club(ctx.channel.id, ctx.author)

    @commands.command()
    @send_embed
    async def leave(self, ctx: commands.Context):
        """Leave the book club in this channel."""
        return self.service.leave_club(ctx.channel.id, ctx.author)

    @commands.command()
    @send_embed
    @commands.has_permissions(administrator=True)
    async def kick(self, ctx: commands.Context):
        """Kick a member from the book club in this channel (admin only)."""
        if not ctx.message.mentions:
            return Err("You must mention a user to kick them.")
        return self.service.kick_member(ctx.channel.id, ctx.message.mentions[0])

    _book_club_message_embed = discord.Embed(
        title="🎉 Book Club Created",
        description="A new book club has been created. Update the book with `!book <title> <author>`. Join the club with `!join`.",
        color=discord.Color.green(),
    )

    @commands.command()
    @send_embed
    async def club(self, ctx: commands.Context):
        """Create a channel and an associated book circle."""
        if ctx.guild is None:
            return Err("This command must be used in a server.")
        channel = await ctx.guild.create_text_channel("bokcirkel")
        result = self.service.create_club(channel.id)
        match result:
            case Ok():
                await channel.send(embed=self._book_club_message_embed)
        return result

    @commands.command()
    @send_embed
    @commands.has_permissions(administrator=True)
    async def book(
        self,
        ctx: commands.Context,
        title: Optional[str] = None,
        author: Optional[str] = None,
    ):
        """Update book information (title/author) by book ID."""
        match r := self.service.create_or_update_book(ctx.channel.id, title, author):
            case Ok():
                if isinstance(ctx.channel, discord.TextChannel):
                    await ctx.channel.edit(name=title or "bokcirkel")
                return r
            case Err():
                return r

    @commands.command()
    @send_embed
    async def info(self, ctx: commands.Context):
        """Show the current status of the book club in this channel."""
        # Use channel ID as book club ID
        return self.service.get_status(ctx.channel.id)

    @commands.command()
    @send_embed
    async def target(self, ctx: commands.Context, *, target: Optional[str]):
        """Set the target for the current book club."""
        return self.service.set_target(ctx.channel.id, BookState.READING, target)

    @commands.command()
    @send_embed
    async def finish(self, ctx: commands.Context):
        """The book is finished."""
        match r := self.service.set_target(ctx.channel.id, BookState.COMPLETED, "Done"):
            case Ok():
                await ctx.send(
                    embed=discord.Embed(
                        title="📚 Book Finished",
                        description="The book has been marked as finished. Congratulations! Leave a review with `!review <rating> <text>`",
                        color=discord.Color.green(),
                    )
                )
                return

        return r

    @commands.command()
    @send_embed
    async def review(self, ctx: commands.Context, rating: int, *, text: str):
        """Add a review for the current book as the current user."""
        return self.service.add_review(ctx.channel.id, ctx.author, text, rating)

    @commands.command()
    @send_embed
    async def quote(self, ctx: commands.Context, *, text: str):
        """Add a quote for the current book as the current user."""
        user_id = ctx.author.id
        return self.service.add_quote(ctx.channel.id, user_id, text)

    @commands.command()
    @send_embed
    async def note(self, ctx: commands.Context, *, text: str):
        """Add a note for the current book as the current user."""
        channel_id = ctx.channel.id
        return self.service.add_note(channel_id, ctx.author, text)

    @commands.command()
    @send_embed
    async def caughtup(self, ctx: commands.Context):
        """You have caught up to the current target."""
        return self.service.set_reader_state(
            ctx.channel.id, ctx.author.id, BookClubReaderState.CAUGHT_UP
        )

    @commands.command()
    @send_embed
    async def setrole(self, ctx: commands.Context, role: str):
        """Manually set your reader role."""

        try:
            role_enum = BookClubReaderRole[role.upper()]
        except KeyError:
            return Err(
                f"Invalid role. Valid roles: {[r.name for r in BookClubReaderRole]}"
            )
        match r := self.service.set_reader_role(ctx.channel.id, ctx.author, role_enum):
            case Ok():
                if ctx.guild is None or not isinstance(ctx.author, discord.Member):
                    return r
                guild_roles = self.__roles_from_guild(ctx.guild)
                await ctx.author.edit(
                    roles=[
                        role for role in ctx.author.roles if role.name not in self.roles
                    ]
                    + [guild_roles[role_enum.name]]
                )
        return r
