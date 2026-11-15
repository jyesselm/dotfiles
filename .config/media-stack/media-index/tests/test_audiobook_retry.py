"""The weekly audiobook retry only takes a release that is this book, this volume, in English."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1]))

import audiobook_retry as ar  # noqa: E402


def book(title, subtitle="", author="Brandon Sanderson", hours=45):
    return SimpleNamespace(title=title, subtitle=subtitle, authors=[author], narrators=[],
                           runtime_length_min=hours * 60)


def release(title, mb, seeders=20):
    return SimpleNamespace(title=title, size=mb * 1e6, seeders=seeders)


def test_a_torrent_without_the_subtitles_book_number_is_still_this_book():
    kings = book("The Way of Kings", "The Stormlight Archive, Book 1")
    assert ar.other_book(kings, "Brandon Sanderson - The Way of Kings") is None
    assert ar.other_book(kings, "Brandon Sanderson - The Way of Kings (The Stormlight Archive #1)") is None


def test_a_number_in_the_title_must_match():
    hunter = book("The Primal Hunter", author="Zogarth")
    assert ar.other_book(hunter, "Zogarth - Primal Hunter T02 - 2025") == "other volume"
    assert ar.other_book(book("The Primal Hunter 5", author="Zogarth"), "The Primal Hunter - Zogarth") == "other volume"


def test_translations_and_parts_of_a_book_are_skipped():
    assert ar.reason_to_skip(book("The Primal Hunter", author="Zogarth", hours=28),
                             release("Zogarth - Primal Hunter [MP3 à 128 kb/s]", 1600)) == "other language"
    kings, name = book("The Way of Kings"), "Brandon Sanderson - The Way of Kings"
    assert ar.reason_to_skip(kings, release(name, 444)) == "wrong size"
    assert ar.reason_to_skip(kings, release(name, 1983)) is None


def test_only_english_releases_are_taken():
    hunter = book("The Primal Hunter", author="Zogarth", hours=28)
    for name in ["Zogarth - The Primal Hunter [GER]", "Zogarth - The Primal Hunter (Hörbuch)",
                 "Zogarth - The Primal Hunter - Audiolibro", "Зогарт - The Primal Hunter Zogarth"]:
        assert ar.reason_to_skip(hunter, release(name, 1600)) == "other language", name
    assert ar.reason_to_skip(hunter, release("Zogarth - The Primal Hunter (Unabridged)", 1600)) is None
    french = book("The French Revolution", author="Zogarth", hours=28)
    assert ar.reason_to_skip(french, release("Zogarth - The French Revolution", 1600)) is None
