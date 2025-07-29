import discord
import discord.ext.test as dpytest
import pytest
import pytest_asyncio

from bot import Bot
from db import Database
from pathlib import Path
from pytest_postgresql import factories

postgresql_proc = factories.postgresql_proc(load=[Path("bokcirkel_schema.sql")])
postgresql = factories.postgresql(
    "postgresql_proc",
)


@pytest_asyncio.fixture(autouse=True)
async def fix_bot(postgresql):
    intents = discord.Intents.default()
    intents.members = True
    intents.messages = True
    intents.message_content = True

    bot = Bot(Database(postgresql), intents)

    await bot.setup_hook()  # Ensure the bot is set up correctly
    await bot._async_setup_hook() 

    dpytest.configure(bot, members=2)
    rc = dpytest.get_config()

    # Create an admin role and assign it to member 1.
    admin_role = await bot.guilds[0].create_role(name='administrator', permissions=discord.Permissions(administrator=True))
    await dpytest.add_role(rc.members[1], admin_role)

    yield bot
    await dpytest.empty_queue()

@pytest.mark.asyncio
async def test_help():
    await dpytest.message("!help")

    assert dpytest.verify().message()


@pytest.mark.asyncio
async def test_book():
    await dpytest.message("!book")

    assert dpytest.verify().message().contains().content("Vilhelm")


@pytest.mark.asyncio
async def test_setbook():
    await dpytest.message("!setbook Oskar")

    assert dpytest.verify().message().contains().content("You must be") 

@pytest.mark.asyncio
async def test_setbook_sets():
    await dpytest.message("!book")
    assert not dpytest.verify().message().contains().content("Oskar") 

    await dpytest.message("!setbook Oskar", member=1)
    assert dpytest.verify().message().contains().content("Oskar") 

    await dpytest.message("!book")
    assert dpytest.verify().message().contains().content("Oskar") 

@pytest.mark.asyncio
async def test_snack():
    await dpytest.message("!snack")

    assert dpytest.verify().message().contains().content("Hela boken")

@pytest.mark.asyncio
async def test_setsnack_denied():
    await dpytest.message("!setsnack New Snack")

    assert dpytest.verify().message().contains().content("You must be")

@pytest.mark.asyncio
async def test_setsnack():
    await dpytest.message("!setsnack New Snack", member=1)

    assert dpytest.verify().message().contains().content("New Snack")

    await dpytest.message("!snack")
    assert dpytest.verify().message().contains().content("New Snack")
    

@pytest.mark.asyncio
async def test_cleardb_denied():
    await dpytest.message("!cleardb")

    assert dpytest.verify().message().contains().content("You must be")

@pytest.mark.asyncio
async def test_addtext():
    await dpytest.message("!addtext This is a test")

    assert dpytest.verify().message().contains().content("Text added")


@pytest.mark.asyncio
async def test_texts():
    await dpytest.message("!listtexts")
    assert dpytest.verify().message().contains().content("No texts stored yet.")

    await dpytest.message("!addtext This is a test")
    assert dpytest.verify().message().contains().content("Text added")

    await dpytest.message("!listtexts")
    assert dpytest.verify().message().contains().content("This is a test")

    await dpytest.message("!cleardb", member=1)
    assert dpytest.verify().message().contains().content("You must be")
    
@pytest.mark.asyncio
async def test_roles():
    await dpytest.message("!roles")
    assert dpytest.verify().message().contains().content("Roller saknas!")

@pytest.mark.asyncio
async def test_roles_work():
    await dpytest.message("!roles")
    assert dpytest.verify().message().contains().content("Roller saknas!")

    await dpytest.message("!initroles", member=1)
    assert dpytest.verify().message().contains().content("initialiserade")

    await dpytest.message("!roles")
    assert dpytest.verify().message().contains().content("Detaljspanaren")