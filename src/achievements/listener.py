import logging
from datetime import datetime, timedelta, UTC
from typing import List

import discord
from blinker import signal
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..books.model import BookClub, User
from .model import Achievement, Counter, UserAchievement


class Listener:
    signal_name: str

    def __init__(self, engine, signal_name=None):
        if signal_name:
            self.signal_name = signal_name
        logging.info(f"Initializing listener for signal: {self.signal_name}")
        self.engine = engine
        self.signal = signal(self.signal_name)
        self.signal.connect(self.action)

    def increment(self, session, user_id: int, amount: int):
        counter = session.query(Counter).filter_by(user_id=user_id, name=self.signal_name).one_or_none()
        if counter is None:
            counter = Counter(user_id=user_id, name=self.signal_name, value=amount)
            session.add(counter)
        else:
            counter.value += amount

    async def action(self, sender, **kwargs):
        try:
            user_id = kwargs.get("user_id")
            ctx = kwargs.get("ctx")
            if ctx is None or user_id is None:
                return
            embeds = []
            with Session(self.engine) as session:
                self.increment(session, user_id, 1)
                session.flush()
                embeds.extend(self.check_achievements(session, user_id))
                session.commit()
            for embed in embeds:
                await ctx.send(embed=embed)
        except Exception:
            logging.exception(f"Error in {self.signal_name} listener action")

    def check_achievements(self, session: Session, user_id: int) -> List[discord.Embed]:
        # Fetch all counters for the user
        counters = {c.name: c.value for c in session.scalars(select(Counter).where(Counter.user_id==user_id)).all()}
        # Fetch all achievements
        achievements = session.scalars(select(Achievement)).all()
        # Fetch already granted achievement ids
        granted_ids = set(
            ua.achievement_id for ua in session.scalars(
                select(UserAchievement).where(UserAchievement.user_id == user_id)
            ).all()
        )
        user = session.get(User, user_id)
        granted_embeds = []
        for ach in achievements:
            rule = ach.rule_json
            counter_name = rule.get("counter")
            required_value = rule.get("value")
            if counter_name is None or required_value is None:
                continue
            if counters.get(counter_name, 0) >= required_value and ach.id not in granted_ids:
                session.merge(UserAchievement(user_id=user_id, achievement_id=ach.id))
                embed = discord.Embed(
                    title=f"{user.name if user else 'Unknown'} unlocks achievement: {ach.name} {ach.icon or ''}",
                    description=ach.description,
                    color=discord.Color.gold()
                )
                granted_embeds.append(embed)
        return granted_embeds

class StreakListener(Listener):
    def increment(self, session, user_id: int, amount: int):
        counter = session.query(Counter).filter_by(user_id=user_id, name=self.signal_name).one_or_none()
        if counter is None:
            counter = Counter(user_id=user_id, name=self.signal_name, value=amount)
            session.add(counter)
            return
    
        if counter.updated_at is not None:
            # Updated yesterday? +1.
            if counter.updated_at.date() == (datetime.now(UTC) - timedelta(days=1)).date():
                counter.value += 1
                return
            # Today? +- 0
            if counter.updated_at.date() == datetime.now(UTC).date():
                return

        # Reset
        counter.value = amount

    async def action(self, sender, **kwargs):
        try:
            user_id = kwargs.get("user_id")
            ctx = kwargs.get("ctx")
            if ctx is None or user_id is None:
                return
            embeds = []
            with Session(self.engine) as session:
                self.increment(session, user_id, 1)
                session.flush()
                embeds.extend(self.check_achievements(session, user_id))
                session.commit()
            for embed in embeds:
                await ctx.send(embed=embed)
        except Exception:
            logging.exception("Error in ReadStreak listener action")



class BooksFinished(Listener):
    signal_name = "books_finished"

    async def action(self, sender, **kwargs):
        try:
            book_club_id = kwargs.get("book_club_id")
            ctx = kwargs.get("ctx")
            if ctx is None or book_club_id is None:
                return
            with Session(self.engine) as session:
                bk = session.get(BookClub, book_club_id)
                if bk is None:
                    return
                for reader in bk.readers:
                    self.increment(session, reader.user_id, 1)
                session.flush()

                embeds = []
                for reader in bk.readers:
                    embeds.extend(self.check_achievements(session, reader.user_id))
                session.commit()
            for embed in embeds:
                await ctx.send(embed=embed)
        except Exception:
            logging.exception("Error in BooksFinished listener action")

class ListenerCollection:
    def __init__(self, engine):
        canonical_counts = ["caught_up", "shame", "notes", "quotes", "reviews"]
        canonical_streaks = ["read", "shamee"]
        self.listeners = []
        self.listeners.append(BooksFinished(engine))
        for signal_name in canonical_counts:
            self.listeners.append(Listener(engine, signal_name))
        for signal_name in canonical_streaks:
            self.listeners.append(StreakListener(engine, signal_name))
