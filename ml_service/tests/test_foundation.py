"""
Unit tests for the foundation layers (no network, no model loading).

Run from ml_service/:  python -m pytest tests/ -q
"""
import pytest

import knowledge
import intent
import db
import migrations


# --------------------------------------------------------------------------- #
# Knowledge compiler — determinism, hashing, no raw JSON
# --------------------------------------------------------------------------- #

_P = {
    "id": 1, "name": "Sauvage", "brand": "Dior",
    "accords": '["fresh spicy", "amber", "citrus"]',
    "top_notes": "Calabrian bergamot, Pepper",
    "middle_notes": "Sichuan Pepper, Lavender",
    "base_notes": "Ambroxan, Cedar",
    "gender": "men", "season": "all autumn winter", "perfumer1": "Francois Demachy",
}


def test_compiler_is_deterministic():
    assert knowledge.compile_embedding_doc(_P) == knowledge.compile_embedding_doc(dict(_P))
    assert knowledge.content_hash(_P) == knowledge.content_hash(dict(_P))


def test_compiler_never_emits_raw_json():
    doc = knowledge.compile_embedding_doc(_P)
    assert "{" not in doc and "[" not in doc
    assert "Calabrian bergamot" in doc and "fresh spicy" in doc


def test_hash_changes_with_content():
    other = dict(_P, base_notes="Vanilla, Tonka")
    assert knowledge.content_hash(other) != knowledge.content_hash(_P)


def test_concentration_detection_is_longest_match():
    assert knowledge.detect_concentration("Sauvage Elixir") == "elixir"
    assert knowledge.detect_concentration("Bleu de Chanel Eau de Parfum") == "eau de parfum"
    assert knowledge.detect_concentration("Sauvage EDP") == "eau de parfum"
    assert knowledge.detect_concentration("Aventus") is None


# --------------------------------------------------------------------------- #
# Intent routing + constraint extraction
# --------------------------------------------------------------------------- #

def test_routing_intents():
    assert intent.route("similar to Dior Sauvage") == ("similar", "Dior Sauvage")
    assert intent.route("something like Aventus under $100") == ("similar", "Aventus")
    assert intent.route("price of Khamrah") == ("price", "Khamrah")
    assert intent.route("new releases this week")[0] == "new_releases"
    assert intent.route("fresh citrus for the office")[0] == "search"


def test_constraint_extraction():
    c = intent.extract_constraints("a winter scent for women under $80")
    assert c.gender == "women"
    assert c.season == "winter"
    assert c.budget == 80.0


# --------------------------------------------------------------------------- #
# DB foundation — migrations + relationship confidence merge
# --------------------------------------------------------------------------- #

@pytest.fixture
def tmpdb(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(db, "_conn", None)
    db.init_db()
    yield db
    if db._conn:
        db._conn.close()
    monkeypatch.setattr(db, "_conn", None)


def test_migrations_idempotent(tmpdb):
    # init_db already ran migrations; a second run applies nothing.
    assert migrations.run(tmpdb.get_connection()) == 0


def test_confidence_noisy_or_merge(tmpdb):
    tmpdb.add_relationship("1", "2", "smells_like", confidence=0.4, source="accord")
    edge = tmpdb.get_relationships("1")[0]
    assert abs(edge["confidence"] - 0.4) < 1e-6

    # Independent evidence accumulates: 1 - (1-0.4)(1-0.5) = 0.7
    tmpdb.add_relationship("1", "2", "smells_like", confidence=0.5, source="perfumer")
    edge = tmpdb.get_relationships("1")[0]
    assert abs(edge["confidence"] - 0.7) < 1e-6
    assert "accord" in edge["sources"] and "perfumer" in edge["sources"]


def test_weaker_evidence_never_lowers_confidence(tmpdb):
    tmpdb.add_relationship("1", "2", "smells_like", confidence=0.9, source="clone_db")
    tmpdb.add_relationship("1", "2", "smells_like", confidence=0.1, source="weak")
    edge = tmpdb.get_relationships("1")[0]
    assert edge["confidence"] >= 0.9


def test_no_self_relationship(tmpdb):
    tmpdb.add_relationship("1", "1", "smells_like", confidence=0.9, source="x")
    assert tmpdb.get_relationships("1") == []
