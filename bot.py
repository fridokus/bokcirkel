import discord
import logging
import json

from discord.ext import commands
from db import Database

class BookCircle(commands.Cog):
    def __init__(self, bot, db: Database) -> None:
        self.bot = bot
        self.db = db
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info(f"Logged in as {self.bot.user}")
        print(f"Logged in as {self.bot.user}")

    @commands.command()
    async def help(self, ctx):
        """Displays available commands with emojis"""
        embed = discord.Embed(title="📖 Bokcirkel Commands", color=discord.Color.blue())
        for command in self.bot.commands:
            if   command.name == "help":          emoji = "❓"
            elif command.name == "addtext":       emoji = "📝"
            elif command.name == "listtexts":     emoji = "📜"
            elif command.name in ["book", "bok"]: emoji = "📚"
            elif command.name == "snack":         emoji = "🍉"
            elif command.name == "source":        emoji = "🔗"
            elif command.name == "rotate":        emoji = "🔄"
            elif command.name == "roles":         emoji = "🎭"
            elif command.name == "initroles":     emoji = "👶"
            elif command.name == "switchrole":    emoji = "🔀"
            else:                                 emoji = "⚡"
            embed.add_field(name=f"{emoji} **!{command.name}**", value=command.help or "No description", inline=False)
        await ctx.send(embed=embed)


    @commands.command()    
    async def addtext(self, ctx, *, text: str):
        """Adds a text string to the database"""
        self.db.add_text(ctx.author.id, ctx.author.name, text)
        await ctx.send("✅ Text added!")

    @addtext.error
    async def addtext_error(self, ctx, error):
        logging.error(f"Error adding text: {e}")
        await ctx.send("❌ Failed to add text.")

    @commands.command()
    async def listtexts(self, ctx):
        """Lists all stored text strings"""
        texts = self.db.texts()
        if not texts:
            await ctx.send("📭 No texts stored yet.")
        else:
            response = "📜 **Stored Texts:**\n" + "\n".join(
                [f"📌 {r[0]}: {r[1]} (*{r[2].strftime('%Y-%m-%d %H:%M:%S')}*)" for r in texts[::-1]]
            )
            await ctx.send(response)

    @listtexts.error
    async def listtexts_error(self, ctx, error):
        logging.error(f"Error listing texts: {error}")
        await ctx.send("❌ Failed to list texts.")


    @commands.command()
    async def source(self, ctx):
        """Get link to source code of this bot"""
        logging.info(f"{ctx.author} used !source")
        await ctx.send("🔗 Source code: https://github.com/fridokus/bokcirkel 📜")

    @commands.command()
    async def book(self, ctx):
        """Show current book"""
        logging.info(f"{ctx.author} used !book")
        book_text = self.db.get_book()
        await ctx.send(book_text)

    @book.error
    async def book_error(self, ctx, error):
        logging.error(f"Error retrieving book: {error}")
        await ctx.send("❌ Failed to retrieve book.")

    @commands.command()
    async def setbook(self, ctx, *, text: str):
        """Set the current book (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ You must be an **admin** to set the book!")
            return
        self.db.set_book(text)
        await ctx.send(f"✅ **Current book updated to:** {text}")

    @setbook.error
    async def setbook_error(self, ctx, error):
        logging.error(f"Error setting book: {error}")
        await ctx.send("❌ **Failed to update book.** Check logs for details.")

    @commands.command()
    async def snack(self, ctx):
        """Shows target chapter for the next meeting"""
        logging.info(f"{ctx.author} used !snack")
        snack_text = self.db.get_setting("snack") or "📖 Hela boken 🍉"
        await ctx.send(snack_text)

    @snack.error
    async def snack_error(self, ctx, error):
        logging.error(f"Error retrieving snack text: {error}")
        await ctx.send("❌ Failed to retrieve snack text.")

    @commands.command()
    async def setsnack(self, ctx, *, text: str):
        """Set the next meeting's target chapter (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ You must be an **admin** to set the snack text!")
            return

        self.db.set_setting("snack", text)
        await ctx.send(f"✅ **Next meeting's chapter set to:** {text}")

    @setsnack.error
    async def setsnack_error(self, ctx, error):
        logging.error(f"Error setting snack text: {error}")
        await ctx.send("❌ **Failed to update snack text.** Check logs for details.")

    @commands.command()
    async def cleardb(self, ctx):
        """Deletes all stored text entries. Only the server owner can run this."""
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ You must be the **server owner** to use this command!")
            return

        self.db.clear_texts()
        await ctx.send("✅ **All text entries have been deleted!**")
        logging.info(f"{ctx.author} cleared the text database.")

    @cleardb.error
    async def cleardb_error(self, ctx, error):
        logging.error(f"Database clear failed: {e}")
        await ctx.send("⚠️ **Failed to clear the database.** Check logs for details.")

    async def load_roles(self, ctx):
        """Helper function to get roles JSON from the database."""
        try: 
            json_roles = self.db.get_setting("roles")
        except Exception :
            await ctx.send("❌ Misslyckades med att hämta roller. Kontrollera loggarna.")
            return
        if not json_roles:
            await ctx.send("❌ Roller saknas! Initialisera roller först.")
            return

        return json.loads(json_roles)

    @commands.command()
    async def initroles(self, ctx):
        """Initialize the roles (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Endast admin kan initialisera rollerna.")
            return

        roles = [
                {"role": "Facilitator", "name": "Oskar", "emoji": "🎤"},
                {"role": "Djävulens advokat", "name": "Jan", "emoji": "😈"},
                {"role": "Citatväljaren", "name": "Anton", "emoji": "💬"},
                {"role": "Summeraren", "name": "Linnea", "emoji": "📝"},
                {"role": "Temaspanaren", "name": "Bell", "emoji": "🎭"},
                {"role": "Länkaren", "name": "Armin", "emoji": "🔗"},
                {"role": "Detaljspanaren", "name": "Dennis", "emoji": "🕵️"},
            ]

        self.db.set_setting("roles", json.dumps(roles))
        await ctx.send("✅ Roller initialiserade! Använd `!roles` för att se dem.")

    @initroles.error
    async def initroles_error(self, ctx, error):
        logging.error(f"Error initializing roles: {error}")
        await ctx.send("❌ Misslyckades med att initialisera roller. Kontrollera loggarna.")

    @commands.command()
    async def rotate(self, ctx):
        """Rotate the roles (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Endast admin kan rotera rollerna.")
            return

        roles = await self.load_roles(ctx)

        names = [r["name"] for r in roles]
        names = names[1:] + names[:1]
        for i, role in enumerate(roles):
            role["name"] = names[i]
        try:
            self.db.set_setting("roles", json.dumps(roles))
            await ctx.send("✅ Roller roterade! Använd `!roles` för att se dem.")
        except Exception:
            await ctx.send("⚠️ Misslyckades med att spara roterade roller.")
    
    @commands.command()
    async def roles(self, ctx):
        """Displays current roles"""
        roles = await self.load_roles(ctx)
        if not roles:
            return

        lines = ["📚 **Roller för nästa bokträff:**"]
        for role in roles:
            lines.append(f"{role['emoji']} {role['name']} - {role['role']}")
        await ctx.send("\n".join(lines))

    @commands.command()
    async def switchrole(self, ctx, role_name: str, new_name: str):
        """Switch the person assigned to a role."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Endast admin kan ändra roller.")
            return

        roles = await self.load_roles(ctx)
        if not roles:
            return

        for role in roles:
            if role["role"].lower() == role_name.lower():
                role["name"] = new_name
                if self.db.set_setting("roles", json.dumps(roles)):
                    await ctx.send(f"✅ Ändrade `{role_name}` till `{new_name}`.")
                else:
                    await ctx.send("⚠️ Misslyckades med att spara ändringen.")
                return

        await ctx.send(f"❌ Hittade ingen roll med namnet `{role_name}`.")



class Bot(commands.Bot):
    def __init__(self, db: Database, intents: discord.Intents):
        self.db = db
        super().__init__(command_prefix="!", intents=intents)
        self.remove_command("help")

    async def setup_hook(self):
        await self.add_cog(BookCircle(self, self.db))