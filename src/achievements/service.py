import logging
import os
import json
from .model import Achievement
from sqlalchemy.orm import Session
from sqlalchemy import select
from .model import Achievement, UserAchievement
from typing import Optional, Sequence


class AchievementService:
    def __init__(self, engine):
        self.engine = engine

    def grant_achievement(
        self, user_id: int, achievement_name: str
    ) -> Optional[UserAchievement]:
        """Grant an achievement to a user if not already granted."""
        with Session(self.engine) as session:
            achievement = session.execute(
                select(Achievement).where(Achievement.name == achievement_name)
            ).scalar_one_or_none()
            if not achievement:
                return None
            already = session.execute(
                select(UserAchievement).where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement.id,
                )
            ).scalar_one_or_none()
            if already:
                return already
            user_achievement = UserAchievement(
                user_id=user_id, achievement_id=achievement.id
            )
            session.add(user_achievement)
            session.commit()
            return user_achievement

    def get_user_achievements(self, user_id: int) -> Sequence[Achievement]:
        with Session(self.engine) as session:
            rows = (
                session.execute(
                    select(Achievement)
                    .join(UserAchievement)
                    .where(UserAchievement.user_id == user_id)
                )
                .scalars()
                .all()
            )
            return rows

def load_achievements_from_json(engine, achievements_dir=None):
    """Load achievements from JSON files and populate the database."""
    if achievements_dir is None:
        achievements_dir = os.path.join(os.path.dirname(__file__), "achievements")
    from sqlalchemy.orm import Session
    with Session(engine) as session:
        count = 0
        for filename in os.listdir(achievements_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(achievements_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for ach in data:
                    count += 1
                    # Upsert by name
                    existing = session.query(Achievement).filter_by(name=ach["name"]).one_or_none()
                    if existing:
                        existing.description = ach["description"]
                        existing.icon = ach.get("icon")
                        existing.rule_json = ach["rule"]
                    else:
                        session.add(Achievement(
                            name=ach["name"],
                            description=ach["description"],
                            icon=ach.get("icon"),
                            rule_json=ach["rule"]
                        ))
        logging.info(f"Loaded {count} achievements from JSON.")

        session.commit()