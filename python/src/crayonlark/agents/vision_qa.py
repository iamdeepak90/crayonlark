"""Vision QA agent: a vision model looks at each original image and flags anatomy errors, scary
faces, text, character/brand lookalikes, age suitability and bad line art.

It only *recommends* keep/reject; I still approve every image set (approve_image_set gate). With
the offline provider nothing is checked and the image keeps its Python QA result alone.
"""

from __future__ import annotations

import io
from typing import Any, Literal

from PIL import Image as PILImage
from pydantic import BaseModel, Field

from crayonlark.providers.llm.base import AgentTask, run_task

MAX_SIDE = 1024  # downscale before sending: enough to judge, far fewer tokens


class VisionQAOut(BaseModel):
    matches_scene: bool = Field(description="The picture shows the requested scene")
    anatomy_ok: bool = Field(description="No extra/missing limbs, eyes, fingers; animals correct")
    scary: bool = Field(description="Anything frightening, violent or sad for young kids")
    has_text: bool = Field(description="Any letters, numbers, words, logos or signatures")
    lookalike: str = Field(
        default="",
        max_length=120,
        description="Famous character, brand or logo it resembles; empty if none",
    )
    age_ok: bool = Field(description="Suitable for the stated ages")
    line_art_ok: bool = Field(
        description="Clean black outlines on white, no shading, grey fills or gradients"
    )
    score: float = Field(ge=0, le=1, description="Overall quality 0-1 for a kids' coloring page")
    recommendation: Literal["keep", "reject"]
    notes: str = Field(default="", max_length=400)


SYSTEM = """You check pages for a children's coloring book before a human reviews them. Be strict
and concrete. Reject anything with wrong anatomy (extra or missing limbs, eyes, fingers, tails),
anything scary or sad, any text/letters/numbers/logos/signatures, anything that resembles a
famous character, brand or logo, and anything that is not clean black line art on white. Say
briefly what is wrong in notes. Return ONLY JSON matching the schema."""


def small_jpeg(data: bytes) -> bytes:
    with PILImage.open(io.BytesIO(data)) as src:
        im = src.convert("L")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=85)
    return out.getvalue()


def flags(out: VisionQAOut) -> list[str]:
    f = []
    if not out.matches_scene:
        f.append("does not match scene")
    if not out.anatomy_ok:
        f.append("anatomy")
    if out.scary:
        f.append("scary")
    if out.has_text:
        f.append("text")
    if out.lookalike.strip():
        f.append(f"looks like {out.lookalike.strip()}")
    if not out.age_ok:
        f.append("not age-appropriate")
    if not out.line_art_ok:
        f.append("line art")
    return f


def to_scores(out: VisionQAOut) -> dict[str, Any]:
    reject = out.recommendation == "reject" or bool(flags(out))
    return {
        **out.model_dump(),
        "checked": True,
        "flags": flags(out),
        "recommendation": "reject" if reject else "keep",
    }


def offline_marker() -> VisionQAOut:
    raise NotImplementedError  # never used: run() returns None when the agent is offline


def run(image: bytes, scene: str, ages: str, book_id: int | None = None) -> VisionQAOut | None:
    from crayonlark.providers.llm.base import agent_config

    if agent_config("vision_qa").get("provider", "offline") == "offline":
        return None
    task = AgentTask(
        agent="vision_qa",
        system=SYSTEM,
        prompt=f"Requested scene: {scene or 'unknown'}\nAges: {ages}\nCheck this page.",
        schema=VisionQAOut,
        offline=offline_marker,
        images=[small_jpeg(image)],
        max_tokens=800,
        book_id=book_id,
    )
    return run_task(task)


def enabled() -> bool:
    from crayonlark.providers.llm.base import agent_config

    return agent_config("vision_qa").get("provider", "offline") != "offline"
