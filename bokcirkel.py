#!/usr/bin/python3

import discord
import logging
from discord.ext import commands

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

@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")
    print(f"Logged in as {bot.user}")

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
