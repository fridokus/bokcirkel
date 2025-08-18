#!/usr/bin/python3

import logging
from db import db,updatedb
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
        database = db.Database()
        updatedb.execute_sql_from_file(database.conn)
        with open('.token', 'r') as f:
            token = f.read().strip()
        logging.info("Starting bot...")
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        bot = Bot(db=database, intents=intents)
        bot.run(token)

    except Exception as e:
        logging.error(f"Error bot: {e}")

if __name__ == "__main__":
    main()
