from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from apps.recommendations.domain.entities import ProjectRecommendation
from apps.recommendations.domain.ports import ProjectCatalogPort

_WORD_PATTERN = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "for", "and", "or", "to", "of", "in", "on", "with",
    "is", "this", "that", "it", "app", "project", "using",
}


def _words(text: str) -> set[str]:
    return {w for w in _WORD_PATTERN.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class GetRecommendationsForUserService:
    """
    A deliberately simple, explainable content-based recommender - not a
    trained ML model. It builds a "taste profile" from tags + description
    words across the requesting user's own projects, then scores every
    other user's "ready" project by tag overlap (weighted highest) plus a
    smaller bonus for shared description vocabulary. See
    DOCUMENTATION_STAGE5.md for why this approach was chosen over a real
    ML/embedding-based system for this stage.
    """

    catalog: ProjectCatalogPort
    tag_weight: float = 0.8
    text_weight: float = 0.2

    def recommend(self, *, user_id: UUID, limit: int = 5) -> list[ProjectRecommendation]:
        all_projects = self.catalog.list_ready_projects()
        my_projects = [p for p in all_projects if p["owner_id"] == user_id]
        other_projects = [p for p in all_projects if p["owner_id"] != user_id]

        if not my_projects:
            return self._popularity_fallback(other_projects, limit)

        my_tags: set[str] = set()
        my_words: set[str] = set()
        for p in my_projects:
            my_tags.update(p["tags"])
            my_words.update(_words(p["description"]) | _words(p["title"]))

        if not my_tags and not my_words:
            return self._popularity_fallback(other_projects, limit)

        scored = []
        for p in other_projects:
            project_tags = set(p["tags"])
            project_words = _words(p["description"]) | _words(p["title"])

            tag_score = _jaccard(my_tags, project_tags)
            text_score = _jaccard(my_words, project_words)
            score = self.tag_weight * tag_score + self.text_weight * text_score

            if score <= 0:
                continue

            shared_tags = sorted(my_tags & project_tags)
            reason = (
                f"Shares tags with your projects: {', '.join(shared_tags)}"
                if shared_tags
                else "Similar description to your projects"
            )

            scored.append(
                ProjectRecommendation(
                    project_id=p["id"],
                    title=p["title"],
                    owner_username=p["owner_username"],
                    shared_tags=shared_tags,
                    score=round(score, 4),
                    reason=reason,
                )
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        if scored:
            return scored[:limit]

        # No content overlap at all with anything - fall back rather than
        # returning an empty, unhelpful list.
        return self._popularity_fallback(other_projects, limit)

    def _popularity_fallback(self, projects: list[dict], limit: int) -> list[ProjectRecommendation]:
        ranked = sorted(projects, key=lambda p: p.get("download_count", 0), reverse=True)
        return [
            ProjectRecommendation(
                project_id=p["id"],
                title=p["title"],
                owner_username=p["owner_username"],
                shared_tags=[],
                score=0.0,
                reason="Popular on SkillSphere right now",
            )
            for p in ranked[:limit]
        ]
