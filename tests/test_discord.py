import bokcirkel
import discord
import discord.ext.test as dpytest
import pytest
import pytest_asyncio

from pathlib import Path
from pytest_postgresql import factories
from unittest.mock import patch

postgresql_proc = factories.postgresql_proc(load=[Path("bokcirkel_schema.sql")])
postgress = factories.postgresql(
    "postgresql_proc",
)



@pytest_asyncio.fixture(autouse=True)
async def bot(postgress):
    with patch('db.get_db_connection', return_value=postgress):
        bot = bokcirkel.bot_for_test()
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
    await dpytest.message("!setbook Oskar", member=1)

    assert dpytest.verify().message().contains().content("Oskar") 

    # Add a !book call here to verify the book was set after DB connection is kept.

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

@pytest.mark.asyncio
async def test_cleardb_denied():
    await dpytest.message("!cleardb")

    assert dpytest.verify().message().contains().content("You must be")

@pytest.mark.asyncio
async def test_addtext():
    await dpytest.message("!addtext This is a test")

    assert dpytest.verify().message().contains().content("Text added")

