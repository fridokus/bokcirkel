#!/usr/bin/python3

import logging
import db

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

        bot = Bot(db=db.Database())
        bot.run(token)

    except Exception as e:
        logging.error(f"Error bot: {e}")

if __name__ == "__main__":
    main()
