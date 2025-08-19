import discord
from sqlalchemy.orm import Session
from ..result_types import Ok, Err, Result
from .model import BookClub

def rotate_roles(engine, book_club_id: int) -> Result[discord.Embed]:
    """
    Rotate roles among all readers in the book club: each reader gets the next reader's role (cyclic).
    """
    with Session(engine) as session:
        club = session.get(BookClub, book_club_id)
        if not club:
            return Err("Book club not found.")
        readers = [r for r in club.readers]
        if not readers or len(readers) < 2:
            return Err("Not enough readers to rotate roles.")
        # Get current roles in order
        roles = [r.role for r in readers]
        # Rotate roles cyclically
        rotated_roles = roles[-1:] + roles[:-1]
        for reader, new_role in zip(readers, rotated_roles):
            reader.role = new_role
        session.commit()
        embed = discord.Embed(
            title="Roles Rotated",
            description="Each reader has received the next reader's role.",
        )
        for reader in readers:
            embed.add_field(name=reader.user.name, value=reader.role.value, inline=True)
        return Ok(embed)
