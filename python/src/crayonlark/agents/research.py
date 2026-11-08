"""Research agent: from a theme I type (plus optional competitor notes I paste) suggest 10 niches
with age range, angle, risks and seasonality.

It may use an optional web-search API (integrations/websearch.py, official APIs only, Amazon and
Etsy results excluded). It never scrapes Amazon or Etsy. Ideas are saved as *proposed* niches:
nothing happens until I approve one in admin (decide_niche gate in core/approvals).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from crayonlark.core import blocklist
from crayonlark.core.enums import NicheStatus
from crayonlark.core.models import Niche
from crayonlark.providers.llm.base import AgentTask, run_task

MAX_NOTES_CHARS = 12000


class NicheIdea(BaseModel):
    name: str = Field(max_length=120, description="Short niche name, e.g. 'Cute Ocean Babies'")
    age_range: str = Field(max_length=10, description="e.g. '3-6'")
    angle: str = Field(max_length=500, description="What makes this book different")
    risks: str = Field(
        max_length=500, description="Trademark/character risks, saturation, accuracy needs"
    )
    seasonality: str = Field(max_length=120, description="'evergreen' or the season/holiday")
    example_scenes: list[str] = Field(default_factory=list, max_length=5)


class ResearchOut(BaseModel):
    ideas: list[NicheIdea] = Field(min_length=5, max_length=12)


SYSTEM = """You help a one-person publisher pick niches for kids' coloring and activity books
(KDP paperbacks and Etsy printables, ages 2-12). Suggest exactly 10 distinct niches for the
theme. Each needs a clear angle (age, style, learning goal, occasion), honest risks
(trademarks, famous characters, brands, saturated markets, facts that must be correct) and
seasonality. Never suggest famous characters, brands, logos, franchises or a living artist's
style. Keep everything friendly and age-appropriate. Base market claims only on the notes and
search results given; if you have none, say what to check instead of inventing numbers.
Return ONLY JSON matching the schema."""

ANGLES = [
    ("Big & Easy {t}", "2-4", "Very thick lines and one big shape per page for toddlers."),
    ("Cute {t} Friends", "4-8", "Smiling characters in everyday scenes kids recognise."),
    ("{t} Activity Book", "5-8", "Coloring mixed with mazes, dot-to-dot and word searches."),
    ("{t} Learn & Color", "3-6", "Each page names the subject in a caption-free way to learn."),
    ("{t} Mandalas for Kids", "8-12", "Simple pattern pages for older kids who like detail."),
    ("{t} Holiday Fun", "4-8", "Seasonal scenes (Christmas, Halloween, Easter)."),
    ("{t} Adventure Stories", "5-9", "Pages that follow a little story from start to end."),
    ("{t} Coloring for Boys and Girls", "4-8", "Broad appeal, gift-friendly title."),
    ("{t} Travel Pack", "4-8", "Small mini-pack printable for car trips and restaurants."),
    ("{t} Classroom Pack", "5-7", "Teacher-friendly printable bundle with simple pages."),
]


def offline(theme: str) -> ResearchOut:
    t = theme.strip().title() or "Animals"
    ideas = []
    for name, ages, angle in ANGLES:
        ideas.append(
            NicheIdea(
                name=name.format(t=t)[:120],
                age_range=ages,
                angle=angle,
                risks="Check how crowded this niche is on KDP and Etsy yourself; "
                "keep every design original.",
                seasonality="Q4 gifts" if "Holiday" in name else "evergreen",
                example_scenes=[f"{t.lower()} playing", f"{t.lower()} at the beach"],
            )
        )
    return ResearchOut(ideas=ideas)


def build_prompt(theme: str, notes: str, search: list[dict[str, str]]) -> str:
    parts = [f"Theme: {theme.strip()}"]
    if notes.strip():
        parts.append("My own competitor notes (pasted by me):\n" + notes.strip()[:MAX_NOTES_CHARS])
    if search:
        lines = [f"- {r['title']}: {r['snippet']} ({r['url']})" for r in search]
        parts.append("Web search results:\n" + "\n".join(lines))
    parts.append("Suggest 10 niches.")
    return "\n\n".join(parts)


def run(theme: str, notes: str = "", search: list[dict[str, str]] | None = None) -> ResearchOut:
    task = AgentTask(
        agent="research",
        system=SYSTEM,
        prompt=build_prompt(theme, notes, search or []),
        schema=ResearchOut,
        offline=lambda: offline(theme),
        max_tokens=4000,
    )
    return run_task(task)


def save_ideas(session: Session, theme: str, out: ResearchOut) -> tuple[list[Niche], list[str]]:
    """Store ideas as proposed niches. Ideas that hit the blocklist are dropped (returned)."""
    extra = blocklist.extra_terms(session)
    saved, dropped = [], []
    for idea in out.ideas[:10]:
        hits = blocklist.check_many(
            {"name": idea.name, "angle": idea.angle, "scenes": idea.example_scenes}, extra
        )
        if hits:
            dropped.append(idea.name)
            continue
        niche = Niche(
            theme=theme[:200],
            name=idea.name,
            age_range=idea.age_range,
            angle=idea.angle,
            risks=idea.risks,
            seasonality=idea.seasonality,
            notes=("Example scenes: " + "; ".join(idea.example_scenes))
            if idea.example_scenes
            else "",
            source="research_agent",
            status=NicheStatus.PROPOSED,
        )
        session.add(niche)
        saved.append(niche)
    session.flush()
    return saved, dropped
