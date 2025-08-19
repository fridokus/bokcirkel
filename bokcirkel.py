#!/usr/bin/python3

import logging
import discord
import sys

from src.bot import Bot

LOG_FILE = "/var/log/bokcirkel.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Nice for local debugging
# logging.basicConfig(
#     stream=sys.stdout,
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )

def main():
    try:
        with open('.token', 'r') as f:
            token = f.read().strip()
        logging.info("Starting bot...")

        intents = discord.Intents.all()
        bot = Bot(intents=intents)
        bot.run(token)

    except Exception as e:
        logging.exception("Bot error")

if __name__ == "__main__":
    main()
