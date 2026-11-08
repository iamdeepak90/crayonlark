from __future__ import annotations

from crayonlark.core import blocklist


def test_brands_and_characters_detected_with_variants() -> None:
    assert blocklist.find("Cute Pokémon coloring") == ["pokemon"]
    assert "spider man" in blocklist.find("Spider-Man coloring pages")
    assert "spider man" in blocklist.find("SPIDERMAN fun")
    assert "peppa pig" in blocklist.find("peppa-pig and friends")
    assert "crayola" in blocklist.find("crayola colors")
    assert "gabby's dollhouse" in blocklist.find("Gabbys Dollhouse")


def test_no_false_positives_on_normal_words() -> None:
    assert blocklist.find("Ocean animals: fish, whale, octopus and a friendly starfish") == []
    assert blocklist.find("Mariola the cat and a large woodland scene") == []  # mario/woody
    assert blocklist.find("Frozen pond in winter, woody forest, stitch a quilt") == []
    assert blocklist.find("Elsa from Frozen") == ["elsa"]


def test_handmade_claims_blocked() -> None:
    assert "handmade" in blocklist.find("A handmade coloring book")
    assert "hand drawn" in blocklist.find("Hand-drawn illustrations")


def test_extra_terms_and_check_many() -> None:
    hits = blocklist.check_many(
        {"title": "Dino Fun", "tags": ["dino", "zogtastic toys"]}, extra=["Zogtastic"]
    )
    assert hits == {"tags": ["zogtastic"]}
