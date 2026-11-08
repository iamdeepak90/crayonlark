"""Website content agent: a short public book description and a blog post draft when a book
goes live. Everything it writes is a draft: a blog post is only published after a human approves
it in admin (the decide_post gate in core/approvals)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from crayonlark.core import blocklist
from crayonlark.core.models import Book
from crayonlark.providers.llm.base import AgentTask, run_task


class PostOut(BaseModel):
    title: str = Field(max_length=120)
    excerpt: str = Field(max_length=300)
    body_md: str = Field(max_length=8000)
    seo_title: str = Field(max_length=70)
    seo_description: str = Field(max_length=160)


class WebsiteContentOut(BaseModel):
    public_description_md: str = Field(max_length=2000)
    post: PostOut


SYSTEM = """You write for the Crayonlark website (kids' coloring and activity books). Audience:
parents, grandparents and teachers. Warm, simple, honest, short sentences. Never mention brands,
famous characters or living artists; never say "handmade" or "hand-drawn"; no fake reviews,
awards or sales claims. Blog posts are useful first (ideas for using the pages: quiet time, travel,
classroom, birthday parties, simple learning tips) and mention the book once near the end.
Use Markdown with ## headings and short lists. Return ONLY JSON matching the schema."""


def offline(book: Book, n_pages: int) -> WebsiteContentOut:
    from crayonlark.agents.listing import _theme
    from crayonlark.print.activities import build_activities

    theme = _theme(book).lower()
    ages = f"{book.age_min}-{book.age_max}"
    desc = (
        f"{book.title} has {n_pages} pages of friendly {theme} pictures with thick, simple "
        f"lines for kids ages {ages}. Every picture is printed on its own page, so markers "
        "do not bleed through."
    )
    if build_activities(book.activity_plan or {}, seed=book.id):
        desc += " Bonus activities and answers are at the back."
    body = (
        f"## Why {theme} pictures work so well\n\n"
        f"Kids love {theme}. Simple pictures with thick lines let small hands finish a page and "
        "feel proud of it.\n\n"
        "## Five ways to use coloring pages\n\n"
        "- **Quiet time:** one page after lunch, with soft music.\n"
        "- **Travel:** a few loose pages and a small box of crayons.\n"
        "- **Classroom:** a calm start to the morning.\n"
        "- **Parties:** a coloring table for guests who need a break.\n"
        "- **Talk about it:** ask your child what colors they chose and why.\n\n"
        "## Our new book\n\n"
        f"*{book.title}* is made for ages {ages}, with {n_pages} pages to color.\n"
    )
    return WebsiteContentOut(
        public_description_md=desc,
        post=PostOut(
            title=f"{theme.title()} Coloring Pages: Easy Ideas for Ages {ages}"[:120],
            excerpt=f"Simple ways to use {theme} coloring pages at home, on the go and in class."[
                :300
            ],
            body_md=body,
            seo_title=f"{theme.title()} Coloring Pages for Kids {ages}"[:70],
            seo_description=f"Ideas for using {theme} coloring pages with kids ages {ages}, "
            "plus our new coloring book."[:160],
        ),
    )


def problems(out: WebsiteContentOut, extra: list[str]) -> dict[str, list[str]]:
    p = out.post
    hits = blocklist.check_many(
        {
            "title": p.title,
            "excerpt": p.excerpt,
            "body": p.body_md,
            "description": out.public_description_md,
        },
        extra,
    )
    text = (p.body_md + out.public_description_md).lower()
    if "handmade" in text or "hand-drawn" in text:
        hits["wording"] = ["handmade/hand-drawn"]
    return hits


def run(book: Book, n_pages: int) -> WebsiteContentOut:
    prompt = (
        f"Book: {book.title}\nSubtitle: {book.subtitle}\nThemes: {', '.join(book.themes or [])}"
        f"\nAges {book.age_min}-{book.age_max}, {n_pages} coloring pages."
        "\nWrite the public book description and one blog post."
    )
    task = AgentTask(
        agent="website_content",
        system=SYSTEM,
        prompt=prompt,
        schema=WebsiteContentOut,
        offline=lambda: offline(book, n_pages),
        max_tokens=3000,
        book_id=book.id,
    )
    return run_task(task)
