import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Optional

import discord
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..result_types import Err, Ok, Result
from .model import (
    Book,
    BookClub,
    BookClubReader,
    BookClubReaderRole,
    BookClubReaderState,
    BookState,
    Note,
    Quote,
    Review,
    SuggestedBook,
    User,
)


def try_except_result(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logging.exception("An error occurred in BookCircleService")
            return Err("An error occurred")

    return wrapper


@dataclass
class ServiceBook:
    id: int
    title: str
    suggester_id: int
    suggested_at: datetime
    author: Optional[str] = None


# Put this in a utility function.
def relative_time(d: datetime) -> str:
    dt_utc = d.replace(tzinfo=timezone.utc)
    return f"<t:{int(dt_utc.timestamp())}:R>"


class BookCircleService:
    def __init__(self, engine):
        self.engine = engine

    @try_except_result
    def caught_up(self, book_club_id: int, user_id: int) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("Book club not found.")
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == book_club_id,
                    BookClubReader.user_id == user_id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("You are not a member of this book club.")
            if bcr.state == BookClubReaderState.CAUGHT_UP:
                return Err("You are already caught up.")
            bcr.state = BookClubReaderState.CAUGHT_UP
            session.commit()
            user = session.get(User, user_id)
            if user is None:
                return Err("User not found.")
            embed = discord.Embed(
                title="🎉 You Caught Up!",
                description=f"{user.name} has caught up to the current target! Give them a round of applause! 👏",
                color=discord.Color.gold(),
            )
            embed.set_thumbnail(
                url="https://media.giphy.com/media/111ebonMs90YLu/giphy.gif"
            )
            return Ok(embed)

    @try_except_result
    def set_progress(
        self, book_club_id: int, user_id: int, progress: str
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            bcr = session.execute(
                select(BookClubReader).where(
                    BookClubReader.book_club_id == book_club_id,
                    BookClubReader.user_id == user_id,
                )
            ).scalar_one_or_none()
            if not bcr:
                return Err("You are not a member of this book club.")
            bcr.progress = progress
            session.commit()
            embed = discord.Embed(
                title="📈 Progress Updated",
                description=f"Your progress is now set to: {progress}",
                color=discord.Color.blue(),
            )
            return Ok(embed)

    @try_except_result
    def suggest_book(
        self, suggester_id: int, title: str, author: Optional[str] = None
    ) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            user = session.get(User, suggester_id)
            if not user:
                return Err("User not found.")
            suggestion = SuggestedBook(
                title=title, author=author, suggester_id=suggester_id
            )
            session.add(suggestion)
            session.commit()
            embed = discord.Embed(
                title="📚 Book Suggested",
                description=f"'{title}' by {author or 'Unknown'} has been suggested by {user.name}.",
                color=discord.Color.blue(),
            )
            return Ok(embed)

    @try_except_result
    def get_suggested_books(self, limit=10) -> Result[list]:
        with Session(self.engine) as session:
            suggestions = (
                session.execute(select(SuggestedBook).limit(limit)).scalars().all()
            )
            return Ok(
                [
                    ServiceBook(
                        id=s.id,
                        title=s.title,
                        author=s.author,
                        suggester_id=s.suggester_id,
                        suggested_at=s.created_at,
                    )
                    for s in suggestions
                ]
            )

    @try_except_result
    def remove_suggested_book(self, suggestion_id: int) -> Result[None]:
        with Session(self.engine) as session:
            suggestion = session.get(SuggestedBook, suggestion_id)
            if not suggestion:
                return Err("Suggestion not found.")
            session.delete(suggestion)
            session.commit()
            return Ok(None)

    class BookAppliedToClub:
        pass

    class BookClubNotFound:
        pass

    @try_except_result
    def pop_suggested_book(
        self, book_club_id: int, suggestion_id: int
    ) -> Result[BookAppliedToClub | BookClubNotFound]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            suggestion = session.get(SuggestedBook, suggestion_id)
            if not suggestion:
                return Err("Suggestion not found.")
            if club:
                club.book.title = suggestion.title
                club.book.author = suggestion.author
            session.delete(suggestion)
            session.commit()
            if club:
                return Ok(BookCircleService.BookAppliedToClub())
            return Ok(BookCircleService.BookClubNotFound())

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
                role = reader.role
                embed.add_field(
                    name=reader.user.name,
                    value=f"{role.emoji} {role.value}",
                    inline=True,
                )
            return Ok(embed)

    @try_except_result
    def list_roles(self, book_club_id: int) -> Result[discord.Embed]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("This channel does not have a registered book club.")
            if not club.readers:
                return Err("No one has joined this book club yet.")

            embed = discord.Embed(
                title="📖 Current Roles",
                description="Here are the current roles in this book club:",
                color=discord.Color.blue(),
            )

            # Sort readers by enum order
            role_order = list(BookClubReaderRole)
            sorted_readers = sorted(
                club.readers, key=lambda r: role_order.index(r.role)
            )

            for reader in sorted_readers:
                role = reader.role
                if role == BookClubReaderRole.NONE:
                    continue  # skip NONE if you don't want to show it
                embed.add_field(
                    name=reader.user.name,
                    value=f"{role.emoji} {role.value.replace('_', ' ').title()}",
                    inline=True,
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
                    reviews.append(
                        (
                            reader.user.name,
                            review.text,
                            review.rating,
                            review.created_at,
                        )
                    )
            if not reviews:
                return Err("No reviews found for this book club.")
            embed = discord.Embed(title=f"📝 Reviews for {club.book.title}")
            for name, text, rating, created in reviews:
                emoji = "⭐"
                created_str = relative_time(created)
                embed.add_field(
                    name=f"{name} (Rating: {rating if rating is not None else 'N/A'})",
                    value=f"{emoji} {text}\n*Added: {created_str}*",
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
                    notes.append((reader.user.name, note.text, note.created_at))
            if not notes:
                return Err("No notes found for this book club.")
            embed = discord.Embed(title=f"🗒️ Notes for {club.book.title}")
            for name, text, created in notes:
                emoji = "🗒️"
                created_str = relative_time(created)
                embed.add_field(
                    name=name,
                    value=f"{emoji} {text}\n*Added: {created_str}*",
                    inline=False,
                )
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
                    quotes.append((reader.user.name, quote.text, quote.created_at))
            if not quotes:
                return Err("No quotes found for this book club.")
            embed = discord.Embed(title=f"💬 Quotes for {club.book.title}")
            for name, text, created in quotes:
                emoji = "💬"
                created_str = relative_time(created)
                embed.add_field(
                    name=name,
                    value=f"{emoji} {text}\n*Added: {created_str}*",
                    inline=False,
                )
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

    @try_except_result
    def create_club(self, book_club_id: int) -> Result[discord.Embed]:
        """Create a new book or update an existing one. Returns Ok(Book) or Err(str)."""
        with Session(self.engine) as session:
            club = BookClub(id=book_club_id)
            club.book = Book(title="Update me", author="Unknown")
            session.merge(club)
            session.commit()
        embed = discord.Embed(
            title="🎉 Book Club Created",
            description=f"Book club created successfully.",
        )
        return Ok(embed)

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
    ) -> Result[int]:
        with Session(self.engine) as session:
            club = session.get(BookClub, book_club_id)
            if not club:
                return Err("No book club found.")
            if club.state == BookState.COMPLETED:
                return Err("Book club is already completed.")
            club.state = state
            if target is None:
                return Err("Target chapter must be specified.")
            if club.target != target:
                club.target = target
                # Set all readers to READING when a new target is set
                for reader in club.readers:
                    reader.state = BookClubReaderState.READING
            if state == BookState.COMPLETED:
                for reader in club.readers:
                    reader.state = BookClubReaderState.COMPLETED

            session.commit()
            return Ok(book_club_id)

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
            embed.add_field(
                name="Target", value=f"🎯 {club.target or 'N/A'}", inline=False
            )
            embed.add_field(name="Readers", value=f"🙋 {readers_list}", inline=False)
            embed.add_field(name="Reviews", value=f"⭐ {total_reviews}", inline=True)
            embed.add_field(name="Quotes", value=f"💬 {total_quotes}", inline=True)
            embed.add_field(name="Notes", value=f"🗒️ {total_notes}", inline=True)
            # Add per-user progress
            progress_lines = []
            for reader in club.readers:
                progress = getattr(reader, "progress", None)
                progress_lines.append(
                    f"{reader.user.name}: {progress or 'No progress set'}"
                )
            if progress_lines:
                embed.add_field(
                    name="Progress", value="\n".join(progress_lines), inline=False
                )
            return Ok(embed)
