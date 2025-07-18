from collections import Counter

from flask import Flask

from src.database import JobCategoryORM
from src.controllers.controller import Controllers, error_handler
from src.utils import tokenize


class IndustryTaxonomyController(Controllers):
    """
    Builds keyword list directly from existing JobCategory rows.
    """
    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def fetch_keywords(
            self,
            title: str,
            description: str,
            skills: list[str],
    ) -> list[tuple[str, int]]:
        tokens = set(tokenize(" ".join([title, description, *skills])))

        with self.get_session() as session:
            categories = session.query(JobCategoryORM).all()

            if not categories:  # 1. no categories at all
                return []

            def overlap(c):
                # treat None as empty list
                canon = c.canonical_skills or []
                syns = list(c.skill_synonyms or {})
                return len(tokens.intersection(set(canon + syns)))

            best = max(categories, key=overlap)

            if overlap(best) == 0:  # 2. no overlap with any category
                return []

            counter = Counter(best.canonical_skills or [])
            for canon, syns in (best.skill_synonyms or {}).items():
                counter[canon] += sum(counter.get(s, 0) for s in syns or [])

            return counter.most_common()
