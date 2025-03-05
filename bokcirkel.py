#!/usr/bin/python3

import discord
from discord.ext import commands

# Set up the bot with a command prefix
intents = discord.Intents.default()
intents.messages = True  # Ensure the bot can read messages
intents.message_content = True  # Ensure the bot can read messages
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def snack(ctx):
    await ctx.send("Hela boken")

@bot.command()
async def book(ctx):
    await ctx.send("Vilhelm Moberg: Utvandrarna")

@bot.command()
async def bok(ctx):
    await book(ctx)

# Run the bot
with open('.token', 'r') as f:
    token = f.read().strip()

bot.run(token)
