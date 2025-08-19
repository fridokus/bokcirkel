import logging
from functools import wraps
from typing import Optional

import discord
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..result_types import Err, Ok, Result
from .model import (Book, BookClub, BookClubReader, BookClubReaderRole,
                    BookClubReaderState, BookState, Note, Quote, Review, User)


def try_except_result(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logging.exception("An error occurred in BookCircleService")
            return Err("An error occurred")

    return wrapper


class BookCircleService:

    @try_except_result
    def shuffle_roles(self, book_club_id: int) -> Result[discord.Embed]:
        import random

        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            readers = [r for r in club.readers]
            if not readers:
                return Err("No readers to assign roles to.")
            # Exclude NONE from assignable roles
            assignable_roles = [
                role for role in BookClubReaderRole if role != BookClubReaderRole.NONE
            ]
            random.shuffle(assignable_roles)
            # If fewer roles than readers, cycle roles
            roles = (assignable_roles * ((len(readers) // len(assignable_roles)) + 1))[
                : len(readers)
            ]
            random.shuffle(roles)
            for reader, role in zip(readers, roles):
                reader.role = role
            session.commit()
            embed = discord.Embed(
                title="🔀 Roles Shuffled",
                description="Roles have been randomly assigned to all readers.",
            )
            for reader in readers:
                emoji = "🎭"
                embed.add_field(
                    name=reader.user.name, value=f"{emoji} {reader.role.value}", inline=True
                )
            return Ok(embed)

    @try_except_result
    def get_books_for_user(
        self, user: discord.User | discord.Member
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            db_user = session.get(User, user.id)
            if not db_user:
                return Err("You have not joined any book clubs.")
            clubs = (
                session.execute(
                    select(BookClub)
                    .join(BookClubReader)
                    .where(BookClubReader.user_id == db_user.id)
                )
                .scalars()
                .all()
            )
            if not clubs:
                return Err("You have not read any books in a club.")
            embed = discord.Embed(title=f"📖 Books read by {user.name}")
            for club in clubs:
                if club.book:
                    embed.add_field(
                        name=club.book.title,
                        value=f"✍️ by {club.book.author or 'Unknown'}",
                        inline=False,
                    )
            return Ok(embed)

    @try_except_result
    def get_reviews(self, book_club_id: int) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            reviews = []
            for reader in club.readers:
                for review in reader.reviews:
                    reviews.append((reader.user.name, review.text, review.rating))
            if not reviews:
                return Err("No reviews found for this book club.")
            embed = discord.Embed(title=f"📝 Reviews for {club.book.title}")
            for name, text, rating in reviews:
                emoji = "⭐"
                embed.add_field(
                    name=f"{name} (Rating: {rating if rating is not None else 'N/A'})",
                    value=f"{emoji} {text}",
                    inline=False,
                )
            return Ok(embed)

    @try_except_result
    def get_notes(self, book_club_id: int) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            notes = []
            for reader in club.readers:
                for note in reader.notes:
                    notes.append((reader.user.name, note.text))
            if not notes:
                return Err("No notes found for this book club.")
            embed = discord.Embed(title=f"🗒️ Notes for {club.book.title}")
            for name, text in notes:
                emoji = "🗒️"
                embed.add_field(name=name, value=f"{emoji} {text}", inline=False)
            return Ok(embed)

    @try_except_result
    def get_quotes(self, book_club_id: int) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            quotes = []
            for reader in club.readers:
                for quote in reader.quotes:
                    quotes.append((reader.user.name, quote.text))
            if not quotes:
                return Err("No quotes found for this book club.")
            embed = discord.Embed(title=f"💬 Quotes for {club.book.title}")
            for name, text in quotes:
                emoji = "💬"
                embed.add_field(name=name, value=f"{emoji} {text}", inline=False)
            return Ok(embed)

    @try_except_result
    def join_club(
        self, book_club_id: int, user: discord.User | discord.Member
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            db_user = session.get(User, user.id)
            if not db_user:
                db_user = User(id=user.id, name=user.name)
                session.add(db_user)
                session.commit()
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == club.id,
                    BookClubReader.user_id == db_user.id,
                )
            ).scalar_one_or_none()
            if bcr:
                return Err("You are already a member of this book club.")
            bcr = BookClubReader(book_club_id=club.id, user_id=db_user.id)
            session.add(bcr)
            session.commit()
        return Ok(
            discord.Embed(
                title="🙋 Joined Book Club",
                description=f"{user.name} joined the book club!",
                color=discord.Color.green(),
            )
        )

    @try_except_result
    def leave_club(
        self, book_club_id: int, user: discord.User | discord.Member
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == club.id,
                    BookClubReader.user_id == user.id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("You are not a member of this book club.")
            session.delete(bcr)
            session.commit()
        return Ok(
            discord.Embed(
                title="👋 Left Book Club",
                description=f"{user.name} left the book club.",
                color=discord.Color.orange(),
            )
        )

    @try_except_result
    def kick_member(
        self, book_club_id: int, user: discord.User | discord.Member
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == club.id,
                    BookClubReader.user_id == user.id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("User is not a member of this book club.")
            session.delete(bcr)
            session.commit()
        return Ok(
            discord.Embed(
                title="🚫 Kicked from Book Club",
                description=f"User {user.name} was kicked from the book club.",
                color=discord.Color.red(),
            )
        )

    def __init__(self, engine):
        self.engine = engine

    @try_except_result
    def create_club(self, book_club_id: int) -> Result[discord.Embed]:
        """Create a new book or update an existing one. Returns Ok(Book) or Err(str)."""
        with Session(self.engine) as session:
            club = BookClub(id=book_club_id)
            club.book = Book(title="Update me", author="Unknown")
            session.merge(club)
            session.commit()
        return Ok(
            discord.Embed(
                title="🎉 Book Club Created",
                description=f"Book club created successfully.",
            )
        )

    @try_except_result
    def create_or_update_book(
        self, book_club_id: int, title: Optional[str], author: Optional[str] = None
    ) -> Result[discord.Embed]:
        """Create a new book or update an existing one. Returns Ok(Book) or Err(str)."""
        with Session(self.engine) as session:
            book_club = session.get(BookClub, book_club_id)
            if not book_club:
                return Err(f"Book club not found.")
            book = book_club.book
            if book is None:
                # Create new book
                book = Book(title=title, author=author)
                book_club.book = book
                session.add(book)
                session.commit()
                return Ok(
                    discord.Embed(
                        title="Book Created",
                        description=f"Book '{book.title}' by {book.author} created successfully.",
                        color=discord.Color.green(),
                    )
                )

            if title is not None:
                book.title = title
            if author is not None:
                book.author = author
            session.commit()
            return Ok(
                discord.Embed(
                    title="Book Updated",
                    description=f"Book '{book.title}' by {book.author} updated successfully.",
                    color=discord.Color.green(),
                )
            )

    @try_except_result
    def set_target(
        self, book_club_id: int, state: BookState, target: Optional[str] = None
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("No book club found.")
            club.state = state
            if target is None:
                return Err("Target chapter must be specified.")
            club.target = target
            # Set all readers to READING when a new target is set
            for reader in club.readers:
                reader.state = BookClubReaderState.READING
            session.commit()
            embed = discord.Embed(
                title="book_club Updated",
                description=f"Book club status set to {state.value}. New target is {target or club.target}",
            )
        return Ok(embed)

    @try_except_result
    def add_review(
        self,
        book_club_id: int,
        member: discord.Member | discord.User,
        text: str,
        rating: Optional[int] = None,
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            user = session.get(User, member.id)
            if not user:
                user = session.merge(User(id=member.id, name=member.name))
            if not club:
                return Err("Book club not found.")
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == club.id,
                    BookClubReader.user_id == member.id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("User is not a member of this book club.")
            review = session.execute(
                select(Review).where(Review.book_club_reader_id == bcr.id)
            ).scalar_one_or_none()
            if not review:
                review = Review(book_club_reader_id=bcr.id)
            review.rating = rating
            review.text = text
            session.merge(review)
            session.commit()

            embed = discord.Embed(
                title="⭐ Review Added",
                description=f"{member.name} reviewed '{club.book.title}': {text}\nRating: {rating if rating is not None else 'N/A'}",
            )
        return Ok(embed)

    @try_except_result
    def add_quote(
        self, book_club_id: int, user_id: int, text: str
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if club is None:
                return Err("Book club not found.")
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == club.id,
                    BookClubReader.user_id == user_id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("User is not a member of this book club.")
            quote = Quote(book_club_reader_id=bcr.id, text=text)
            session.add(quote)
            session.commit()
            embed = discord.Embed(
                title="💬 Quote Added",
                description=f"{bcr.user.name} added a quote for '{club.book.title}': {text}",
            )
        return Ok(embed)

    @try_except_result
    def add_note(
        self, book_club_id: int, member: discord.User | discord.Member, text: str
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            user = session.get(User, member.id)
            if not user:
                user = session.merge(
                    User(id=member.id, name=member.name)
                )  # Create user if not found
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == club.id,
                    BookClubReader.user_id == user.id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("User is not a member of this book club. Type !join to join")
            note = Note(book_club_reader_id=bcr.id, text=text)
            session.add(note)
            session.commit()
            embed = discord.Embed(
                title="🗒️ Note Added",
                description=f"{user.name} added a note for '{club.book.title}': {text}",
            )
        return Ok(embed)

    @try_except_result
    def set_reader_state(
        self, book_club_id: int, user_id: int, state: BookClubReaderState
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("No book club found.")
            book_club = club
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == book_club.id,
                    BookClubReader.user_id == user_id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("User is not a member of this book club.")
            bcr.state = state
            session.commit()
            embed = discord.Embed(
                title="🔄 Reader State Updated",
                description=f"Reader state set to {state.value}.",
            )
        return Ok(embed)

    @try_except_result
    def set_reader_role(
        self,
        book_club_id: int,
        user: discord.Member | discord.User,
        role: BookClubReaderRole,
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            book_club = session.get(BookClub, book_club_id)
            if book_club is None:
                return Err("Book club not found.")
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == book_club.id,
                    BookClubReader.user_id == user.id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("User is not a member of this book club.")
            bcr.role = role
            session.commit()
            embed = discord.Embed(
                title="🎭 Reader Role Updated",
                description=f"Reader role set to {role.value} for user {user.name} in book club {book_club.book.title}.",
            )
        return Ok(embed)

    @try_except_result
    def get_status(self, book_club_id: int) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            # Aggregate reviews, quotes, notes from all BookClubReader objects
            total_reviews = sum(len(reader.reviews) for reader in club.readers)
            total_quotes = sum(len(reader.quotes) for reader in club.readers)
            total_notes = sum(len(reader.notes) for reader in club.readers)
            readers_list = (
                ", ".join(reader.user.name for reader in club.readers)
                if club.readers
                else "No readers yet"
            )
            embed = discord.Embed(title=f"📊 Book Club Status: {club.book.title}")
            embed.add_field(name="State", value=f"📖 {club.state.value}", inline=False)
            embed.add_field(name="Target", value=f"🎯 {club.target or 'N/A'}", inline=False)
            embed.add_field(name="Readers", value=f"🙋 {readers_list}", inline=False)
            embed.add_field(name="Reviews", value=f"⭐ {total_reviews}", inline=True)
            embed.add_field(name="Quotes", value=f"💬 {total_quotes}", inline=True)
            embed.add_field(name="Notes", value=f"🗒️ {total_notes}", inline=True)
            return Ok(embed)
