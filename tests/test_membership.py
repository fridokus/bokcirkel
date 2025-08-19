import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.books.service import BookCircleService, BookClubReaderState, BookState
from src.books.model import BookClub, BookClubReader, User, Base

def is_ok(result):
    return hasattr(result, 'value')

def is_err(result):
    return hasattr(result, 'msg')

@pytest.fixture
def in_memory_service():
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    service = BookCircleService(engine)
    return service, engine

def test_join_and_leave_club(in_memory_service):
    service, engine = in_memory_service
    Session = sessionmaker(bind=engine)
    with Session() as session:
        club = BookClub(id=1, state=BookState.READING, target="T")
        user = User(id=1, name="User1")
        session.add_all([club, user])
        session.commit()
    # Join
    class DummyUser:
        id = 1
        name = "User1"
    result = service.join_club(1, DummyUser())
    assert is_ok(result)
    # Leave
    result = service.leave_club(1, DummyUser())
    assert is_ok(result)
    with Session() as session:
        bcr = session.query(BookClubReader).filter_by(book_club_id=1, user_id=1).first()
        assert bcr is None

def test_set_reader_state(in_memory_service):
    service, engine = in_memory_service
    Session = sessionmaker(bind=engine)
    with Session() as session:
        club = BookClub(id=1, state=BookState.READING, target="T")
        user = User(id=1, name="User1")
        session.add_all([club, user])
        session.commit()
        bcr = BookClubReader(book_club_id=1, user_id=1, state=BookClubReaderState.READING)
        session.add(bcr)
        session.commit()
    result = service.set_reader_state(1, 1, BookClubReaderState.CAUGHT_UP)
    assert is_ok(result)
    with Session() as session:
        bcr = session.query(BookClubReader).filter_by(book_club_id=1, user_id=1).first()
        assert bcr.state == BookClubReaderState.CAUGHT_UP

def test_kick_member(in_memory_service):
    service, engine = in_memory_service
    Session = sessionmaker(bind=engine)
    with Session() as session:
        club = BookClub(id=1, state=BookState.READING, target="T")
        user = User(id=1, name="User1")
        session.add_all([club, user])
        session.commit()
        bcr = BookClubReader(book_club_id=1, user_id=1, state=BookClubReaderState.READING)
        session.add(bcr)
        session.commit()
    class DummyUser:
        id = 1
        name = "User1"
    result = service.kick_member(1, DummyUser())
    assert is_ok(result)
    with Session() as session:
        bcr = session.query(BookClubReader).filter_by(book_club_id=1, user_id=1).first()
        assert bcr is None
