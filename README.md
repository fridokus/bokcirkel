# Bokcirkel

## Introduction

Bokcirkel is a Discord bot designed to help manage and organize book clubs. It integrates with Discord servers to facilitate book discussions and scheduling, while using PostgreSQL for persistent data storage. This project is intended for anyone who wants to run a book club community on Discord with automated features.


## Deployment/Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/fridokus/bokcirkel.git
   cd bokcirkel
   ```

2. **Set up a Python virtual environment (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a Discord developer application**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications/)
   - Create a new application and add a bot to it.
   - Copy the bot token.
   - Save the token in a file named `.token` in the project root (same directory as `bokcirkel.py`). The file should contain only the token string.

5. **Invite the bot to your Discord server**
   - In the Developer Portal, under OAuth2 > URL Generator, select `bot` scope and assign necessary permissions.
   - Copy the generated URL and use it to invite the bot to your server.

6. **Install and configure PostgreSQL**
   - Install PostgreSQL:
     ```bash
     sudo apt-get install postgresql postgresql-contrib
     ```
   - Start the PostgreSQL service:
     ```bash
     sudo service postgresql start
     ```
   - Create a new PostgreSQL user and database (replace `bokcirkeluser` and `bokcirkelpass` with your desired credentials):
     ```bash
     sudo -u postgres createuser bokcirkeluser --pwprompt
     sudo -u postgres createdb bokcirkel_db --owner=bokcirkeluser
     ```
   - Update the database credentials in `bokcirkel.py` if you use different values.

7. **Run the bot**
   ```bash
   python bokcirkel.py
   ```

The bot should now connect to Discord and interact with your server as configured.

By default the bot outputs logs to "/var/log/bokcirkel.log"
  
## Credits

This project was created by Fridokus (Oskar Fridell).

