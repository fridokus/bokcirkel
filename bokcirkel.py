#!/usr/bin/python3

import discord
from discord.ext import commands

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def snack(ctx):
    await ctx.send("Hela boken")

@bot.command()
async def source(ctx):
    await ctx.send("https://github.com/fridokus/bokcirkel")

@bot.command()
async def book(ctx):
    await ctx.send("Vilhelm Moberg: Utvandrarna")

@bot.command()
async def bok(ctx):
    await book(ctx)

def main():
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    with open('.token', 'r') as f:
        token = f.read().strip()
    bot.run(token)

if __name__ == "__main__":
    main()
