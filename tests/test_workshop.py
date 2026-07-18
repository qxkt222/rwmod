"""Test workshop — data model and logic, no network calls.

Only tests logic paths that don't require network:
ModSearchResult dataclass, fetch_item_dependencies with empty input.
"""

from __future__ import annotations

from rwmod.workshop import (
    ModSearchResult,
    fetch_item_dependencies,
)


class TestModSearchResult:
    def test_defaults(self):
        r = ModSearchResult(id="123", title="Test", author="Author")
        assert r.id == "123"
        assert r.title == "Test"
        assert r.author == "Author"
        assert r.description == ""
        assert r.preview_url == ""

    def test_full_fields(self):
        r = ModSearchResult(
            id="123",
            title="Test Mod",
            author="Tester",
            description="A great mod",
            preview_url="https://img.example.com/thumb.png",
            rating="4.5",
            subscribers="10000",
        )
        assert r.description == "A great mod"
        assert r.preview_url == "https://img.example.com/thumb.png"
        assert r.rating == "4.5"
        assert r.subscribers == "10000"

    def test_dataclass_equality(self):
        """ModSearchResult supports field comparison."""
        a = ModSearchResult(id="1", title="A", author="X")
        b = ModSearchResult(id="1", title="A", author="X")
        assert a == b
        c = ModSearchResult(id="2", title="A", author="X")
        assert a != c


class TestFetchItemDependencies:
    def test_empty_list(self):
        assert fetch_item_dependencies([]) == {}
