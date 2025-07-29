#!/usr/bin/python3

import logging
import db
import discord

from bot import Bot

LOG_FILE = "/var/log/bokcirkel.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    try:
        with open('.token', 'r') as f:
            token = f.read().strip()
        logging.info("Starting bot...")

        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        bot = Bot(db=db.Database(), intents=intents)
        bot.run(token)

    except Exception as e:
        logging.error(f"Error bot: {e}")

if __name__ == "__main__":
    main()
