"""Allow-list HTML sanitizer for anything shown on the public site (book texts, blog posts)."""

from __future__ import annotations

import html
from html.parser import HTMLParser

import markdown as md

ALLOWED = {
    "p",
    "br",
    "b",
    "strong",
    "i",
    "em",
    "ul",
    "ol",
    "li",
    "h2",
    "h3",
    "h4",
    "blockquote",
    "a",
    "hr",
}
VOID = {"br", "hr"}
SAFE_SCHEMES = ("https://", "http://", "/", "mailto:")


class _Cleaner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[str] = []
        self.skip = 0  # inside <script>/<style>

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "iframe", "object"):
            self.skip += 1
            return
        if tag not in ALLOWED or self.skip:
            return
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if not href.strip().lower().startswith(SAFE_SCHEMES):
                self.out.append("<a>")
            else:
                ext = href.startswith("http")
                rel = ' rel="noopener nofollow" target="_blank"' if ext else ""
                self.out.append(f'<a href="{html.escape(href, quote=True)}"{rel}>')
        else:
            self.out.append(f"<{tag}>")
        if tag not in VOID:
            self.open.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "iframe", "object"):
            self.skip = max(0, self.skip - 1)
            return
        if tag in self.open and not self.skip:
            while self.open:
                t = self.open.pop()
                self.out.append(f"</{t}>")
                if t == tag:
                    break

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        return "".join(self.out) + "".join(f"</{t}>" for t in reversed(self.open))


def clean(text: str) -> str:
    c = _Cleaner()
    c.feed(text or "")
    c.close()
    return c.result()


def markdown_to_html(text: str) -> str:
    return clean(md.markdown(text or "", extensions=["extra", "sane_lists"], output_format="html"))
