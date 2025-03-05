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
        if command.name == "help":                     emoji = "❓"
        elif command.name in ["addtext", "listtexts"]: emoji = "📝"
        elif command.name in ["book", "bok"]:          emoji = "📚"
        elif command.name == "snack":                  emoji = "🍉"
        elif command.name == "source":                 emoji = "🔗"
        else:                                          emoji = "⚡"
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
async def snack(ctx):
    logging.info(f"{ctx.author} used !snack")
    await ctx.send("📖 Hela boken 🍉")

@bot.command()
async def source(ctx):
    logging.info(f"{ctx.author} used !source")
    await ctx.send("🔗 Source code: https://github.com/fridokus/bokcirkel 📜")

@bot.command()
async def book(ctx):
    logging.info(f"{ctx.author} used !book")
    await ctx.send("📚 Vilhelm Moberg: Utvandrarna 🇸🇪")

@bot.command()
async def bok(ctx):
    logging.info(f"{ctx.author} used !bok")
    await book(ctx)

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
