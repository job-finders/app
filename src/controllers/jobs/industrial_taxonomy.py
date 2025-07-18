import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import Flask
from sqlalchemy import or_, desc, String
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql.operators import and_

from src.controllers.controller import Controllers
from src.controllers.controller import error_handler


class IndustryTaxonomyController(Controllers):
    """
    Builds keyword list directly from existing JobCategory rows.
    """
    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app: Flask):
        super().init_app(app=app)


    async def fetch_keywords(
        self,
        title: str,
        description: str,
        skills: List[str],
    ) -> List[tuple[str, int]]:
        """
        1.  Tokenise title + description + skills
        2.  Find the best matching JobCategory via overlap
        3.  Return (canonical_skill, frequency) tuples
        """
        tokens = set(tokenize(" ".join([title, description, *skills])))

        with self.get_session() as session:
            # pick category with highest skill overlap
            categories = session.query(JobCategoryORM).all()
            best = max(
                categories,
                key=lambda c: len(tokens.intersection(set(c.canonical_skills + list(c.skill_synonyms.keys()))))
            )

        # build frequency map
        counter = Counter(best.canonical_skills)
        for canon, syns in best.skill_synonyms.items():
            counter[canon] += sum(counter[s] for s in syns)

        return counter.most_common()