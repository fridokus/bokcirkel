import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.books.service import BookCircleService, BookClubReaderState, BookState
from src.books.model import BookClub, BookClubReader, User, Base


def is_ok(result):
    return hasattr(result, "value")


def is_err(result):
    return hasattr(result, "msg")


@pytest.fixture
def in_memory_service():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    service = BookCircleService(engine)
    return service, engine


def test_set_target_sets_all_readers_to_reading(in_memory_service):
    service, engine = in_memory_service
    Session = sessionmaker(bind=engine)
    with Session() as session:
        club = BookClub(id=1, state=BookState.READING, target="Old")
        user1 = User(id=1, name="User1")
        user2 = User(id=2, name="User2")
        session.add_all([club, user1, user2])
        session.commit()
        bcr1 = BookClubReader(
            book_club_id=1, user_id=1, state=BookClubReaderState.CAUGHT_UP
        )
        bcr2 = BookClubReader(
            book_club_id=1, user_id=2, state=BookClubReaderState.CAUGHT_UP
        )
        session.add_all([bcr1, bcr2])
        session.commit()
    result = service.set_target(1, BookState.READING, "Chapter 5")
    with Session() as session:
        readers = session.query(BookClubReader).filter_by(book_club_id=1).all()
        assert all(r.state == BookClubReaderState.READING for r in readers)
    assert is_ok(result)


def test_set_target_requires_target(in_memory_service):
    service, engine = in_memory_service
    Session = sessionmaker(bind=engine)
    with Session() as session:
        club = BookClub(id=1, state=BookState.READING, target="Old")
        session.add(club)
        session.commit()
    result = service.set_target(1, BookState.READING, None)
    assert is_err(result)
