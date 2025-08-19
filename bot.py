import discord
import json
import library
import logging

from functools import wraps
from typing import Optional
from discord.ext import commands
from db.db import Database

def command_feedback(success_msg: Optional[str] = None, failure_msg: str = "An error occurred."):
    """
    Decorator for command methods to handle exceptions and send feedback messages.
    Sends success_msg on success, failure_msg on exception.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            try:
                result = await func(self, ctx, *args, **kwargs)
                if success_msg:
                    await ctx.send(success_msg)
                return result
            except Exception:
                logging.exception("Error in {func.__name__}")
                await ctx.send(embed=discord.Embed(
                    title="Error",
                    description=f"{failure_msg}",
                    color=discord.Color.red()
                ))
        return wrapper
    return decorator

class BookCircle(commands.Cog):
    """
    Discord Cog for Book Circle bot commands and event handlers.
    """
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Event handler for when the bot is ready."""
        logging.info("Logged in as {self.bot.user}")
        print(f"Logged in as {self.bot.user}")

    @commands.command()
    async def help(self, ctx: commands.Context) -> None:
        """Displays available commands with emojis."""
        COMMAND_EMOJIS = {
            "help": "❓",
            "addtext": "📝",
            "listtexts": "📜",
            "book": "📚",
            "bookinfo": "📚",
            "snack": "🍉",
            "source": "🔗",
            "rotate": "🔄",
            "roles": "🎭",
            "initroles": "👶",
            "switchrole": "🔀",
            "progress": "📈",
            "setprogress": "🗂️",
        }
        embed = discord.Embed(title="📖 Book Circle Commands", color=discord.Color.blue())
        for command in self.bot.commands:
            emoji = COMMAND_EMOJIS.get(command.name, "⚡")
            embed.add_field(name=f"{emoji} **!{command.name}**", value=command.help or "No description", inline=False)
        await ctx.send(embed=embed)


    @commands.command()
    @command_feedback(success_msg="✅ Text added!", failure_msg="❌ Failed to add text.")
    async def addtext(self, ctx: commands.Context, *, text: str) -> None:
        """Adds a text string to the database."""
        self.db.add_text(ctx.author.id, ctx.author.name, text)

    @commands.command()
    async def listtexts(self, ctx: commands.Context) -> None:
        """Lists all stored text strings."""
        try:
            texts = self.db.texts()
            if not texts:
                await ctx.send("📭 No texts stored yet.")
            else:
                response = "📜 **Stored Texts:**\n" + "\n".join(
                    [f"📌 {r[0]}: {r[1]} (*{r[2].strftime('%Y-%m-%d %H:%M:%S')}*)" for r in texts[::-1]]
                )
                await ctx.send(response)
        except Exception:
            logging.exception("Error listing texts")
            await ctx.send("❌ Failed to retrieve texts.")


    @commands.command()
    async def source(self, ctx: commands.Context) -> None:
        """Get link to source code of this bot."""
        logging.info(f"{ctx.author} used !source")
        await ctx.send("🔗 Source code: https://github.com/fridokus/bokcirkel 📜")

    @commands.command()
    async def bookinfo(self, ctx: commands.Context, *, text: str) -> None:
        """Look up a book."""
        logging.info(f"{ctx.author} used !bookinfo")
        try:
            book_info = library.fetch_book(text)
            await ctx.send(f"📚 **Book Information:**\n{book_info}")
        except Exception:
            logging.exception("Error retrieving book")
            await ctx.send("❌ Failed to retrieve book.")


    @commands.command()
    async def book(self, ctx: commands.Context) -> None:
        """Show current book."""
        logging.info(f"{ctx.author} used !book")
        try:
            book_text = self.db.get_book()
            await ctx.send(book_text)
        except Exception:
            logging.exception("Error retrieving book text")
            await ctx.send("❌ Failed to retrieve book text.")

    @commands.command()
    @command_feedback(success_msg=None, failure_msg="❌ **Failed to update book.** Check logs for details.")
    async def setbook(self, ctx: commands.Context, *, text: str) -> None:
        """Set the current book (Admin only)."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ You must be an **admin** to set the book!")
            return
        self.db.set_book(text)
        await ctx.send(f"✅ **Current book updated to:** {text}")

    @commands.command()
    async def snack(self, ctx: commands.Context) -> None:
        """Show target chapter for the next meeting."""
        logging.info(f"{ctx.author} used !snack")
        try:
            snack_text = self.db.get_setting("snack") or "📖 The whole book 🍉"
            await ctx.send(snack_text)
        except Exception:
            logging.exception("Error retrieving snack text")
            await ctx.send("❌ Failed to retrieve snack text.")

    @commands.command()
    @command_feedback(success_msg=None, failure_msg="❌ **Failed to update snack text.** Check logs for details.")
    async def setsnack(self, ctx: commands.Context, *, text: str) -> None:
        """Set the next meeting's target chapter (Admin only)."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ You must be an **admin** to set the snack text!")
            return
        self.db.set_setting("snack", text)
        await ctx.send(f"✅ **Next meeting's chapter set to:** {text}")

    @commands.command()
    @command_feedback(success_msg="✅ **All text entries have been deleted!**", failure_msg="⚠️ **Failed to clear the database.** Check logs for details.")
    async def cleardb(self, ctx: commands.Context) -> None:
        """Deletes all stored text entries. Only the server owner can run this."""
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ You must be the **server owner** to use this command!")
            return
        self.db.clear_texts()
        logging.info(f"{ctx.author} cleared the text database.")

    async def load_roles(self, ctx: commands.Context) -> Optional[list]:
        """Helper function to get roles JSON from the database."""
        try:
            json_roles = self.db.get_setting("roles")
        except Exception:
            logging.exception("Error fetching roles")
            await ctx.send("❌ Failed to fetch roles. Check logs.")
            return None
        if not json_roles:
            await ctx.send("❌ Roles are missing! Initialize roles first.")
            return None
        return json.loads(json_roles)

    @commands.command()
    @command_feedback(success_msg="✅ Roles initialized! Use `!roles` to see them.", failure_msg="⚠️ Failed to save rotated roles.")
    async def initroles(self, ctx: commands.Context) -> None:
        """Initialize the roles (Admin only)."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Only admin can initialize the roles.")
            return
        roles = [
            {"role": "Facilitator", "name": "Oskar", "emoji": "🎤"},
            {"role": "Devil's Advocate", "name": "Jan", "emoji": "😈"},
            {"role": "Quote Picker", "name": "Anton", "emoji": "💬"},
            {"role": "Summarizer", "name": "Linnea", "emoji": "📝"},
            {"role": "Theme Spotter", "name": "Bell", "emoji": "🎭"},
            {"role": "Linker", "name": "Armin", "emoji": "🔗"},
            {"role": "Detail Spotter", "name": "Dennis", "emoji": "🕵️"},
        ]
        self.db.set_setting("roles", json.dumps(roles))

    @commands.command()
    @command_feedback(success_msg=None, failure_msg="⚠️ Failed to save rotated roles.")
    async def rotate(self, ctx: commands.Context) -> None:
        """Rotate the roles (Admin only)."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Only admin can rotate the roles.")
            return
        roles = await self.load_roles(ctx)
        if not roles:
            return
        names = [r["name"] for r in roles]
        names = names[1:] + names[:1]
        for i, role in enumerate(roles):
            role["name"] = names[i]
        self.db.set_setting("roles", json.dumps(roles))
        await ctx.send("✅ Roles rotated! Use `!roles` to see them.")
    
    @commands.command()
    async def roles(self, ctx: commands.Context) -> None:
        """Displays current roles."""
        roles = await self.load_roles(ctx)
        if not roles:
            return

        lines = ["📚 **Roles for the next book meeting:**"]
        for role in roles:
            lines.append(f"{role['emoji']} {role['name']} - {role['role']}")
        await ctx.send("\n".join(lines))

    @commands.command()
    @command_feedback(success_msg=None, failure_msg="⚠️ Failed to save the change.")
    async def switchrole(self, ctx: commands.Context, role_name: str, new_name: str) -> None:
        """Switch the person assigned to a role."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Only admin can change roles.")
            return
        roles = await self.load_roles(ctx)
        if not roles:
            return
        for role in roles:
            if role["role"].lower() == role_name.lower():
                role["name"] = new_name
                self.db.set_setting("roles", json.dumps(roles))
                await ctx.send(f"✅ Changed `{role_name}` to `{new_name}`.")
                return
        await ctx.send(f"❌ No role found with the name `{role_name}`.")


    @commands.command()
    @command_feedback(failure_msg="❌ Failed to set your progress. Check logs for details.")
    async def setprogress(self, ctx, *, progress: str = "") -> None:
        """Set or clear your book reading progress."""
        self.db.set_user_progress(ctx.author.id, ctx.author.name, progress)
        msg = "✅ Your progress has been cleared." if not progress else f"✅ Your progress has been set to: {progress}"
        await ctx.send(msg)


    @commands.command()
    async def progress(self, ctx) -> None:
        """Show everyone's reading progress."""
        try:
            progresses = self.db.get_user_progress()
            if not progresses:
                await ctx.send("📭 No progress set yet.")
                return
            lines = [f"📖 **{name}**: {progress if progress else 'No progress set.'}" for name, progress in progresses]
            await ctx.send("\n".join(lines))
        except Exception:
            logging.exception("Error retrieving user progress")
            await ctx.send("❌ Failed to retrieve user progress. Check logs for details.")


class Bot(commands.Bot):
    """
    Custom Bot class for Book Circle, attaches the database and loads the Cog.
    """
    def __init__(self, db: Database, intents: discord.Intents) -> None:
        self.db = db
        super().__init__(command_prefix="!", intents=intents)
        self.remove_command("help")

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(embed=discord.Embed(
                title="Command not found",
                description=f"{error}. Type !help for a list of commands",
                color=discord.Color.red()
            ))

    async def setup_hook(self) -> None:
        await self.add_cog(BookCircle(self, self.db))