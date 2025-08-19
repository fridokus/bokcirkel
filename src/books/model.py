from ..models import Base
from typing import Optional
from sqlalchemy import Integer, String, Enum, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

# Define BookState enum at the top so it can be referenced directly in models
class BookState(enum.Enum):
    PLANNED = "planned"
    READING = "reading"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

# State enum for BookClubReader
class BookClubReaderState(enum.Enum):
    READING = "reading"
    CAUGHT_UP = "caught_up"
    GIVEN_UP = "given_up"
    COMPLETED = "completed"

# Role enum for BookClubReader
class BookClubReaderRole(enum.Enum):
    NONE = "none"
    FACILITATOR = "facilitator"
    SUMMARIZER = "summarizer"
    QUOTE_PICKER = "quote_picker"
    THEME_SPOTTER = "theme_spotter"
    LINK_FINDER = "link_finder"
    DEVILS_ADVOCATE = "devils_advocate"
    DETAIL_SPOTTER = "detail_spotter"
    MOOD_SPOTTER = "mood_spotter"


# Association object for BookClub readers
class BookClubReader(Base):
    __tablename__ = "book_club_reader"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_club_id: Mapped[int] = mapped_column(Integer, ForeignKey("book_club.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    state: Mapped["BookClubReaderState"] = mapped_column(Enum(BookClubReaderState), nullable=False, default=BookClubReaderState.READING)
    role: Mapped["BookClubReaderRole"] = mapped_column(Enum(BookClubReaderRole), nullable=False, default=BookClubReaderRole.NONE)
    # Add more fields as needed (e.g., join_date)
    book_club: Mapped["BookClub"] = relationship("BookClub", back_populates="readers")
    user: Mapped["User"] = relationship("User", back_populates="book_club_readerships")
    quotes: Mapped[list["Quote"]] = relationship("Quote", back_populates="book_club_reader")
    notes: Mapped[list["Note"]] = relationship("Note", back_populates="book_club_reader")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="book_club_reader")

class BookClub(Base):
    __tablename__ = "book_club"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("book.id"), nullable=True)
    target: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    state: Mapped[BookState] = mapped_column(Enum(BookState), nullable=False, default=BookState.PLANNED)
    # Optionally add fields like meeting_date, etc.
    book: Mapped["Book"] = relationship("Book", back_populates="book_club")
    readers: Mapped[list["BookClubReader"]] = relationship("BookClubReader", back_populates="book_club")

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    book_club_readerships: Mapped[list["BookClubReader"]] = relationship("BookClubReader", back_populates="user")

class Book(Base):
    __tablename__ = "book"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Add more fields as needed (e.g., year, isbn)
    book_club: Mapped[Optional["BookClub"]] = relationship("BookClub", back_populates="book")


class Quote(Base):
    __tablename__ = "quote"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_club_reader_id: Mapped[int] = mapped_column(Integer, ForeignKey("book_club_reader.id"), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    book_club_reader: Mapped["BookClubReader"] = relationship("BookClubReader", back_populates="quotes")

class Note(Base):
    __tablename__ = "note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_club_reader_id: Mapped[int] = mapped_column(Integer, ForeignKey("book_club_reader.id"), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    book_club_reader: Mapped["BookClubReader"] = relationship("BookClubReader", back_populates="notes")

class Review(Base):
    __tablename__ = "review"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_club_reader_id: Mapped[int] = mapped_column(Integer, ForeignKey("book_club_reader.id"), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    book_club_reader: Mapped["BookClubReader"] = relationship("BookClubReader", back_populates="reviews")