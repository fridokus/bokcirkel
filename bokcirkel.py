#!/usr/bin/python3

import discord
import logging
import psycopg2
from discord.ext import commands

DB_HOST = "127.0.0.1"
DB_USER = "botuser"
DB_PASSWORD = "123"
DB_NAME = "bokcirkel"

LOG_FILE = "/var/log/bokcirkel.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")
    print(f"Logged in as {bot.user}")

bot.remove_command("help")
@bot.command(name="help", help="Displays available commands")
async def custom_help(ctx):
    """Displays available commands with emojis"""
    embed = discord.Embed(title="📖 Bokcirkel Commands", color=discord.Color.blue())
    for command in bot.commands:
        if   command.name == "help":          emoji = "❓"
        elif command.name == "addtext":       emoji = "📝"
        elif command.name == "listtexts":     emoji = "📜"
        elif command.name in ["book", "bok"]: emoji = "📚"
        elif command.name == "snack":         emoji = "🍉"
        elif command.name == "source":        emoji = "🔗"
        else:                                 emoji = "⚡"
        embed.add_field(name=f"{emoji} **!{command.name}**", value=command.help or "No description", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def addtext(ctx, *, text: str):
    """Adds a text string to the database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO texts (user_id, username, text) VALUES (%s, %s, %s)",
                    (ctx.author.id, ctx.author.name, text))
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"{ctx.author} added text: {text}")
        await ctx.send("✅ Text added!")
    except Exception as e:
        logging.error(f"Error adding text: {e}")
        await ctx.send("❌ Failed to add text.")

@bot.command()
async def listtexts(ctx):
    """Lists all stored text strings"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username, text, timestamp FROM texts ORDER BY timestamp DESC LIMIT 10")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            await ctx.send("📭 No texts stored yet.")
        else:
            response = "📜 **Stored Texts:**\n" + "\n".join(
                [f"📌 {r[0]}: {r[1]} (*{r[2].strftime('%Y-%m-%d %H:%M:%S')}*)" for r in rows]
            )
            await ctx.send(response)
    except Exception as e:
        logging.error(f"Error listing texts: {e}")
        await ctx.send("❌ Failed to retrieve texts.")

@bot.command()
async def source(ctx):
    """Get link to source code of this bot"""
    logging.info(f"{ctx.author} used !source")
    await ctx.send("🔗 Source code: https://github.com/fridokus/bokcirkel 📜")

def get_setting(key):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST
        )
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = %s;", (key,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logging.error(f"Database fetch error: {e}")
        return None

def set_setting(key, value):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST
        )
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
            """,
            (key, value),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Database update error: {e}")
        return False

@bot.command()
async def book(ctx):
    """Show current book"""
    logging.info(f"{ctx.author} used !book")
    book_text = get_setting("book") or "📚 Vilhelm Moberg: Utvandrarna 🇸🇪"
    await ctx.send(book_text)

@bot.command()
async def setbook(ctx, *, text: str):
    """Set the current book (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You must be an **admin** to set the book!")
        return

    if set_setting("book", text):
        await ctx.send(f"✅ **Current book updated to:** {text}")
    else:
        await ctx.send("⚠️ **Failed to update book.** Check logs.")

@bot.command()
async def snack(ctx):
    """Shows target chapter for the next meeting"""
    logging.info(f"{ctx.author} used !snack")
    snack_text = get_setting("snack") or "📖 Hela boken 🍉"
    await ctx.send(snack_text)

@bot.command()
async def setsnack(ctx, *, text: str):
    """Set the next meeting's target chapter (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You must be an **admin** to set the snack text!")
        return

    if set_setting("snack", text):
        await ctx.send(f"✅ **Next meeting's chapter set to:** {text}")

@bot.command(name="cleardb", help="⚠️ Deletes all stored text entries (Owner only!)")
async def cleardb(ctx):
    """Deletes all stored text entries. Only the server owner can run this."""
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.send("❌ You must be the **server owner** to use this command!")
        return

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM texts;")
        conn.commit()
        cur.close()
        conn.close()

        await ctx.send("✅ **All text entries have been deleted!**")
        logging.info(f"{ctx.author} cleared the text database.")
    except Exception as e:
        logging.error(f"Database clear failed: {e}")
        await ctx.send("⚠️ **Failed to clear the database.** Check logs for details.")

def main():
    try:
        with open('.token', 'r') as f:
            token = f.read().strip()
        logging.info("Starting bot...")
        bot.run(token)
    except Exception as e:
        logging.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    main()
