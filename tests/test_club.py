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

def test_create_club_and_set_target(in_memory_service):
    service, engine = in_memory_service
    Session = sessionmaker(bind=engine)
    # Create club
    result = service.create_club(1)
    assert is_ok(result)
    # Set target
    result = service.set_target(1, BookState.READING, 'Ch 1')
    assert is_ok(result)
    with Session() as session:
        club = session.query(BookClub).get(1)
        assert club.target == 'Ch 1'
        assert club.state == BookState.READING

def test_cannot_join_twice(in_memory_service):
    service, engine = in_memory_service
    Session = sessionmaker(bind=engine)
    with Session() as session:
        club = BookClub(id=1, state=BookState.READING, target="T")
        user = User(id=1, name="User1")
        session.add_all([club, user])
        session.commit()
    class DummyUser:
        id = 1
        name = "User1"
    result = service.join_club(1, DummyUser())
    assert is_ok(result)
    result2 = service.join_club(1, DummyUser())
    assert is_err(result2)

def test_leave_non_member(in_memory_service):
    service, engine = in_memory_service
    Session = sessionmaker(bind=engine)
    with Session() as session:
        club = BookClub(id=1, state=BookState.READING, target="T")
        user = User(id=1, name="User1")
        session.add_all([club, user])
        session.commit()
    class DummyUser:
        id = 1
        name = "User1"
    result = service.leave_club(1, DummyUser())
    assert is_err(result)
