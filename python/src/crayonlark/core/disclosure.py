"""AI disclosure wording for KDP and Etsy, generated from the book's AI fields (never by an LLM).

KDP asks whether the book contains AI-generated text, images and translations. Content made by an
AI tool counts as "AI-generated" even if we edited it afterwards. Etsy listings say the item is
"Designed by" the seller and state that the artwork was made with AI tools and edited by the seller.
"""

from __future__ import annotations

from typing import Any

from crayonlark.core.models import Book


def kdp_answers(book: Book, cover_ai: bool | None = None) -> dict[str, Any]:
    cover = book.ai_cover_image if cover_ai is None else (book.ai_cover_image or cover_ai)
    images_ai = book.ai_interior_images or cover
    tools = book.ai_tools or "AI image and text tools"
    return {
        "contains_ai_content": images_ai or book.ai_text,
        "text": "AI-generated" if book.ai_text else "None",
        "text_tools": tools if book.ai_text else "",
        "images": "AI-generated" if images_ai else "None",
        "images_detail": ", ".join(
            p
            for p, on in (
                ("interior illustrations", book.ai_interior_images),
                ("cover image", cover),
            )
            if on
        ),
        "images_tools": tools if images_ai else "",
        "translations": "None",
        "edited_by_human": True,
    }


def kdp_markdown(book: Book, cover_ai: bool | None = None) -> str:
    a = kdp_answers(book, cover_ai)
    lines = [
        f"# AI disclosure for “{book.title}”",
        "",
        "KDP → Paperback Content → *AI-Generated Content* question. Answer exactly as below.",
        "",
        "- **Does this book contain AI-generated content?** "
        + ("Yes" if a["contains_ai_content"] else "No"),
        f"- **Text:** {a['text']}" + (f" (tools: {a['text_tools']})" if a["text_tools"] else ""),
        f"- **Images:** {a['images']}"
        + (f": {a['images_detail']} (tools: {a['images_tools']})" if a["images_tools"] else ""),
        f"- **Translations:** {a['translations']}",
        "",
        "Everything was reviewed and edited by Crayonlark before publishing.",
        "",
        f"Record: interior images AI = {book.ai_interior_images}, cover image AI = "
        f"{bool(book.ai_cover_image or cover_ai)}, text AI = {book.ai_text}.",
    ]
    return "\n".join(lines) + "\n"


def etsy_text(book: Book) -> str:
    if book.ai_interior_images:
        return (
            "Designed by Crayonlark. The artwork was made with AI tools and then edited "
            "and checked by Crayonlark for clean lines and kid-friendly content."
        )
    return "Designed by Crayonlark."
