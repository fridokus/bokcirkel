import asyncio
import logging
from blinker import signal
from functools import wraps
from typing import Optional

import discord
from discord.ext import commands
from sqlalchemy.orm import Session

from ..apis import library 
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
    # Debugging command for local development
    # @commands.command()
    # async def deleteallchannels(self, ctx ):
    #     """Delete all channels in the server (admin only)."""
    #     if ctx.guild is None:
    #         return Err("This command must be used in a server.")
    #     if not ctx.author.guild_permissions.administrator:
    #         return Err("You must be an administrator to use this command.")
    #     for channel in ctx.guild.channels:
    #         try:
    #             asyncio.create_task(channel.delete())
    #         except Exception:
    #             logging.exception(f"Failed to delete channel {channel.id}")
    #     return Ok(discord.Embed(
    #         title="Channels Deleted",
    #         description="All channels have been deleted.",
    #         color=discord.Color.green()
    #     ))

    def __init__(self, bot: commands.Bot, engine):
        self.bot = bot
        self.engine = engine
        self.service = BookCircleService(engine)
        self.books_finished = signal("books_finished")
        self.caught_up = signal("caught_up")
        self.read_signal = signal("read")
        self.shame_signal = signal("shame")
        self.shamee_signal = signal("shamee")
        self.note_signal = signal("notes")
        self.quote_signal = signal("quotes")
        self.review_signal = signal("reviews")
        self.roles = {
            r.name for r in BookClubReaderRole if r != BookClubReaderRole.NONE
        }
        super().__init__()

    @commands.command()
    @send_embed
    async def read(self, ctx: commands.Context, *, progress: str):
        """Set your reading progress (e.g., page, chapter, percent)."""
        match r := self.service.set_progress(ctx.channel.id, ctx.author.id, progress):
            case Ok():
                await self.read_signal.send_async(None, ctx=ctx, user_id=ctx.author.id)
        return r

    async def background_shame_task(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(12 * 60 * 60)  # 12 hours
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
                                and r.state != BookClubReaderState.COMPLETED
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
                r for r in club.readers if r.state != BookClubReaderState.CAUGHT_UP and 
                r.state != BookClubReaderState.COMPLETED
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
            await self.shame_signal.send_async(None, ctx=ctx, user_id=ctx.author.id)
            mentions = []
            for reader in not_caught_up:
                user = reader.user
                mentions.append(f"<@{user.id}>")
                await self.shamee_signal.send_async(None, ctx=ctx, user_id=user.id)
            await ctx.send(
                embed=discord.Embed(
                    title="⏰ Shame!",
                    description=f"The following readers have not caught up: {', '.join(mentions)}",
                    color=discord.Color.red(),
                )
            )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Event handler for when the bot is ready."""
        logging.info("BookCircle Cog is ready.")
        
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
        embed = discord.Embed(title="Book Club Roles", color=discord.Color.blue())
        for role in BookClubReaderRole:
            if role == BookClubReaderRole.NONE:
                continue
            name = role.name.title().replace("_", " ")
            desc = f"{role.emoji} {role.description}"
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
    async def syncroles(self, ctx: commands.Context):
        """Synchronize the roles based on this book club (admin only)."""
        await self.__synchronize_roles(ctx)

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

    @commands.command(name="roles")
    @send_embed
    async def roles_command(self, ctx: commands.Context):
        """Show all current roles for members in this book club."""
        return self.service.list_roles(ctx.channel.id)

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
        description="A new book club has been created. Update the book with `!book <title> <author>`. Join the club with `!join`. You can also start a poll of suggested books with `!poll <seconds>`.\n\n-# Use `!note <text>` to share notes and `!quote <text>` to share quotes.",
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
    async def setbook(
        self,
        ctx: commands.Context,
        title: Optional[str] = None,
        author: Optional[str] = None,
    ):
        """Update book information (title/author) by book ID."""
        match r := self.service.create_or_update_book(ctx.channel.id, title, author):
            case Ok():
                if isinstance(ctx.channel, discord.TextChannel):
                    embed = discord.Embed(title="📚 Rename Channel", description="Would you like to rename the channel? (yes/no)", color=discord.Color.blue())
                    await ctx.send(embed=embed)

                    msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30.0)
                    if msg.content.lower() not in set(["y", "yes"]):
                        return r

                    await ctx.channel.edit(name=f"📚 {title or 'bokcirkel'}")
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
        match self.service.set_target(ctx.channel.id, BookState.READING, target):
            case Ok():
                embed = discord.Embed(title="🎯 Target Set", description=f"New target set to: {target}. Type !caughtup when you have reached the target.", color=discord.Color.green())
                await ctx.send(embed=embed)
            case Err():
                return Err("Failed to set target.")

    @commands.command()
    @send_embed
    async def finish(self, ctx: commands.Context):
        """The book is finished."""
        match r := self.service.set_target(ctx.channel.id, BookState.COMPLETED, "Done"):
            case Ok(club_id):
                await ctx.send(
                    embed=discord.Embed(
                        title="📚 Book Finished",
                        description="The book has been marked as finished. Congratulations! Leave a review with `!review <rating> <text>`",
                        color=discord.Color.green(),
                    )
                )
                await self.books_finished.send_async(None, ctx=ctx, book_club_id=club_id)
                return

        return r

    @commands.command()
    @send_embed
    async def review(self, ctx: commands.Context, rating: int, *, text: str):
        """Add a review for the current book as the current user."""
        match r := self.service.add_review(ctx.channel.id, ctx.author, text, rating):
            case Ok():
                await self.review_signal.send_async(None, ctx=ctx, user_id=ctx.author.id)
        return r

    @commands.command()
    @send_embed
    async def quote(self, ctx: commands.Context, *, text: str):
        """Add a quote for the current book as the current user."""
        user_id = ctx.author.id
        match r := self.service.add_quote(ctx.channel.id, user_id, text):
            case Ok():
                await self.quote_signal.send_async(None, ctx=ctx, user_id=user_id)
        return r

    @commands.command()
    @send_embed
    async def note(self, ctx: commands.Context, *, text: str):
        """Add a note for the current book as the current user."""
        channel_id = ctx.channel.id
        match r := self.service.add_note(channel_id, ctx.author, text):
            case Ok():
                await self.note_signal.send_async(None, ctx=ctx, user_id=ctx.author.id)
        return r

    @commands.command()
    @send_embed
    async def caughtup(self, ctx: commands.Context):
        """You have caught up to the current target."""
        match r := self.service.caught_up(ctx.channel.id, ctx.author.id):
            case Ok():
                await self.caught_up.send_async(None, ctx=ctx, user_id=ctx.author.id)
        return r

    @commands.command()
    @send_embed
    async def role(self, ctx: commands.Context, role: str):
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

    @commands.command()
    @send_embed
    async def suggest(
        self, ctx: commands.Context, title: str, *, author: Optional[str] = None
    ):
        """Suggest a book for the club."""
        return self.service.suggest_book(ctx.author.id, title, author)

    @commands.command()
    @send_embed
    async def suggested(self, ctx: commands.Context) -> Result[discord.Embed]:
        """Show all suggested books."""
        match r := self.service.get_suggested_books():
            case Ok(suggestions):
                embed = discord.Embed(title="📚 Suggested Books")
                for suggestion in suggestions:
                    embed.add_field(
                        name=suggestion.title,
                        value=f"by {suggestion.author or 'Unknown'}",
                        inline=False,
                    )
                return Ok(embed)
        return r

    @commands.command()
    @send_embed
    async def book(self, ctx: commands.Context, *, query: str):
        """Show information about a specific book."""
        book_info =  library.fetch_book(query)
        if book_info is None:
            return Err("Failed to fetch book information. Use !setbook to manually pick the book")

        embed = discord.Embed(
            title=f"{book_info.title}",
            description=f"by {book_info.author or 'Unknown'}\nYear: {book_info.year or 'N/A'}\nPages: {book_info.pages or 'N/A'}\nRating: {f'{book_info.rating:.2f}' or 'N/A'}",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

        embed = discord.Embed(title="📚 Read Book", description="Would you like to read this book as a club? (yes/no)", color=discord.Color.blue())
        await ctx.send(embed=embed)

        same_person = lambda message: message.author == ctx.author and message.channel == ctx.channel
        msg = await self.bot.wait_for('message', check=same_person, timeout=30.0)

        if msg.content.lower() not in set(["y", "yes"]):
            await ctx.send("Book will not be applied to the club.")
            return

        match r := self.service.create_or_update_book(ctx.channel.id, book_info.title, book_info.author, book_info.year, book_info.pages, book_info.rating):
            case Ok():
                if isinstance(ctx.channel, discord.TextChannel):
                    embed = discord.Embed(title="📚 Rename Channel", description="Would you like to rename the channel? (yes/no)", color=discord.Color.blue())
                    await ctx.send(embed=embed)

                    msg = await self.bot.wait_for('message', check=same_person, timeout=30.0)

                    if msg.content.lower() not in set(["y", "yes"]):
                        return r
                    await ctx.channel.edit(name=f"📚 {book_info.title or 'bokcirkel'}")
        return r


    @commands.command()
    async def poll(self, ctx: commands.Context, seconds: int = 30):
        """Start a poll of all suggested books. Winner is removed from suggestions. `!poll <seconds>`"""
        ## Limit is 10 by default. Which matches the number of emojis
        if seconds > 3600 * 24:
            # Limit it to 1 day.
            seconds = 3600 * 24
        result = self.service.get_suggested_books()
        match result:
            case Ok(suggestions):
                if not suggestions:
                    await ctx.send("No books have been suggested.")
                    return
                embed = discord.Embed(
                    title="📊 Book Poll",
                    description="Vote for the next book! React below.",
                )
                emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                book_map = {}
                for i, suggestion in enumerate(suggestions):
                    emoji = emoji_list[i % len(emoji_list)]
                    embed.add_field(
                        name=f"{emoji} {suggestion.title}",
                        value=f"by {suggestion.author or 'Unknown'} (suggested by <@{suggestion.suggester_id}>)",
                        inline=False,
                    )
                    book_map[emoji] = suggestion.id
                poll_message = await ctx.send(embed=embed)
                for emoji in book_map:
                    await poll_message.add_reaction(emoji)
                await ctx.send(
                    f"Poll started! React with your vote. It will end in {seconds} seconds."
                )
                await asyncio.sleep(seconds)  # Poll duration (seconds)
                poll_message = await ctx.channel.fetch_message(poll_message.id)
                counts = {emoji: 0 for emoji in book_map}
                for reaction in poll_message.reactions:
                    if reaction.emoji in book_map:
                        users = [u async for u in reaction.users()]
                        counts[reaction.emoji] = len([u for u in users if not u.bot])
                winner_emoji = max(counts, key=counts.get)
                winner_id = book_map[winner_emoji]
                winner = next((s for s in suggestions if s.id == winner_id), None)
                if winner:
                    match self.service.pop_suggested_book(ctx.channel.id, winner.id):
                        case Ok(BookCircleService.BookAppliedToClub()):
                            await ctx.send(
                                f"🏆 The winner is '{winner.title}' by {winner.author or 'Unknown'}!"
                            )
                            # update channel name
                            if isinstance(ctx.channel, discord.TextChannel):
                                await ctx.channel.edit(name=f"📚 {winner.title}")
                else:
                    await ctx.send("No winner could be determined.")
            case Err(msg):
                await ctx.send(f"Error: {msg}")