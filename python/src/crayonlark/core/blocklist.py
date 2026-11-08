"""Blocklist check for famous characters, brands, logos and living artists' styles.

Matching ignores case and accents (Pokémon → pokemon) and treats spaces, hyphens and
apostrophes as optional (Spider-Man, spiderman, spider man all match "spider man").
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from sqlalchemy.orm import Session

from crayonlark.core.config import ASSETS_DIR


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'")
    return re.sub(r"[^a-z0-9']+", " ", text).strip()


@lru_cache
def builtin_terms() -> tuple[str, ...]:
    lines = (ASSETS_DIR / "blocklist.txt").read_text(encoding="utf-8").splitlines()
    return tuple(sorted({normalise(x) for x in lines if x.strip() and not x.startswith("#")}))


def _pattern(term: str) -> re.Pattern[str]:
    parts = [re.escape(p) for p in term.replace("'", " ").split()]
    joined = r"[\s']*".join(parts)  # "spider man" also matches "spiderman"
    return re.compile(rf"(?<![a-z0-9]){joined}s?(?![a-z0-9])")


@lru_cache(maxsize=2048)
def _compiled(term: str) -> re.Pattern[str]:
    return _pattern(term)


def find(text: str, extra: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Return blocked terms found in text (empty list = clean)."""
    if not text:
        return []
    norm = normalise(text)
    squashed = norm.replace("'", "")
    hits = []
    for term in (*builtin_terms(), *(normalise(e) for e in extra if e.strip())):
        pat = _compiled(term)
        if pat.search(norm) or pat.search(squashed):
            hits.append(term)
    return sorted(set(hits))


def check_many(
    fields: dict[str, str | list[str]], extra: list[str] | tuple[str, ...] = ()
) -> dict[str, list[str]]:
    """{field: [hits]} for every field with a hit."""
    out: dict[str, list[str]] = {}
    for name, value in fields.items():
        text = " | ".join(value) if isinstance(value, list) else value
        hits = find(text, extra)
        if hits:
            out[name] = hits
    return out


def extra_terms(session: Session | None = None) -> list[str]:
    from crayonlark.core import app_settings

    return list(app_settings.get("blocklist_extra", session) or [])


class BlockedContent(ValueError):
    def __init__(self, hits: dict[str, list[str]]):
        self.hits = hits
        super().__init__(
            "blocked terms: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in hits.items())
        )
