"""
Tests for the Gap 7-10 evolution + vote parser. No network / no model loading.

Run from ml_service/:  python -m pytest tests/ -q
"""
import pytest
from bs4 import BeautifulSoup

import db
import explainability
import repositories


# --------------------------------------------------------------------------- #
# Vote parser (tuned against the rendered DOM shape)
# --------------------------------------------------------------------------- #

_RENDERED_VOTES = """
<div id="votes">
  <div>LONGEVITY</div>
  <div>no vote</div><div>very weak</div><div>525</div>
  <div>weak</div><div>927</div><div>moderate</div><div>6.6k</div>
  <div>long lasting</div><div>10.3k</div><div>eternal</div><div>1.8k</div>
</div>
"""


def test_vote_parser_handles_buckets_and_k_suffix():
    from ingestion import fragrantica_scraper as fs
    soup = BeautifulSoup(_RENDERED_VOTES, "lxml")
    votes = fs._parse_votes(soup)
    lon = votes.get("longevity", {})
    assert lon.get("very weak") == 525        # not confused with 'weak'
    assert lon.get("weak") == 927
    assert lon.get("moderate") == 6600        # k-suffix parsed
    assert lon.get("long lasting") == 10300
    assert "no vote" not in lon               # excluded


def test_parse_count_suffixes():
    from ingestion import fragrantica_scraper as fs
    assert fs._parse_count("525") == 525
    assert fs._parse_count("6.6k") == 6600
    assert fs._parse_count("1,800") == 1800
    assert fs._parse_count("2m") == 2_000_000
    assert fs._parse_count("n/a") is None


# --------------------------------------------------------------------------- #
# Explainability (Gap 8)
# --------------------------------------------------------------------------- #

def test_explainability_annotation():
    recs = [
        {"name": "A", "relation": "clone_of", "similarity_reason": ["Community clone"],
         "in_inventory": True, "in_stock": True, "match_score": 1.2},
        {"name": "B", "in_inventory": False},
    ]
    explainability.annotate(recs, explainability.search_pipeline())
    assert recs[0]["explain"]["retrieval_pipeline"][:3] == ["FTS5", "Qdrant", "RRF"]
    assert recs[0]["explain"]["graph_relation"] == "clone_of"
    assert recs[0]["explain"]["inventory_reason"] == "Available in shop inventory"
    assert "graph_relation" not in recs[1]["explain"]


# --------------------------------------------------------------------------- #
# Repository protocols (Gap 10)
# --------------------------------------------------------------------------- #

def test_adapters_satisfy_protocols():
    assert isinstance(repositories.get_perfume_repo(), repositories.PerfumeRepository)
    assert isinstance(repositories.get_vector_repo(), repositories.VectorRepository)
    assert isinstance(repositories.get_relationship_repo(), repositories.RelationshipRepository)


# --------------------------------------------------------------------------- #
# Worker metrics + state (Gap 7)
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


def test_job_metrics_accumulate(tmpdb):
    tmpdb.record_job("embedding_sync", "ok", items=5, duration_ms=120)
    tmpdb.record_job("embedding_sync", "ok", items=3, duration_ms=90)
    m = {r["job"]: r for r in tmpdb.get_job_metrics()}["embedding_sync"]
    assert m["runs_total"] == 2
    assert m["items_total"] == 8
    assert m["last_items"] == 3


def test_worker_state_roundtrip(tmpdb):
    assert tmpdb.get_state("rel_cursor", "0") == "0"
    tmpdb.set_state("rel_cursor", "300")
    assert tmpdb.get_state("rel_cursor") == "300"


def test_base_name_collapses_concentrations():
    import knowledge as k
    assert k.base_name("Sauvage Eau de Parfum") == "sauvage"
    assert k.base_name("Sauvage Elixir") == "sauvage"
    assert k.base_name("Bleu de Chanel Parfum") == "bleu de chanel"


def test_structural_inference_links_concentrations(tmpdb, monkeypatch):
    # Two concentration siblings of the same line + one unrelated perfume.
    for name, fid in [("Sauvage Eau de Toilette", "1"), ("Sauvage Elixir", "2"),
                      ("Aventus", "9")]:
        tmpdb.upsert_perfume({
            "name": name, "brand": "Dior" if fid != "9" else "Creed",
            "url": f"https://x/perfume/b/{name.replace(' ','-')}-{fid}.html",
        })
    import relationship_builder
    res = relationship_builder.infer_structural_relationships()
    assert res["edges"] >= 2
    # The two Sauvage concentrations are linked; Aventus is not.
    rels = tmpdb.get_relationships("1")
    types = {r["rel_type"] for r in rels}
    assert "same_collection" in types
    assert all(r["dst_frag_id"] != "9" for r in rels)  # no cross-line edge


def test_performance_consensus_no_invented_numbers():
    import knowledge as k
    p = {"longevity_votes": '{"weak": 10, "long lasting": 200, "moderate": 50}',
         "sillage_votes": '{"strong": 100, "moderate": 40}'}
    c = k.performance_consensus(p)
    assert "long lasting longevity" in c and "strong sillage" in c
    assert not any(ch.isdigit() for ch in c)  # consensus, not fake hours


def test_embedding_doc_includes_mood_and_inferred_season():
    import knowledge as k
    p = {"name": "X", "brand": "Y", "accords": '["vanilla","amber"]',
         "inferred_season": "fall winter", "season": "summer"}
    doc = k.compile_embedding_doc(p)
    assert "Mood:" in doc and "cozy" in doc
    assert "fall winter" in doc            # inferred_season preferred over crawled
    assert "{" not in doc


def test_seasonal_inference_rules():
    import seasonal
    assert "summer" in seasonal.infer_season(["citrus", "aquatic", "fresh"])
    winter = seasonal.infer_season(["amber", "vanilla", "gourmand"])
    assert "winter" in winter
    # heavy performance pushes toward cold seasons
    s = seasonal.infer_season(["woody"], longevity_votes='{"eternal": 100}',
                              sillage_votes='{"enormous": 80}')
    assert "winter" in s or "fall" in s
    assert seasonal.infer_season([]) == "all seasons"


def test_regional_modifiers_and_rerank():
    import regional
    hot = regional.modifiers(temp_c=33, humidity=80)
    assert hot.get("citrus", 1) > 1 and hot.get("gourmand", 1) < 1
    cold = regional.modifiers(temp_c=2)
    assert cold.get("amber", 1) > 1 and cold.get("aquatic", 1) < 1
    # re-rank: a fresh scent should outrank a gourmand one in the heat
    results = [
        {"name": "Gourmand", "accords": ["gourmand", "vanilla"], "final_score": 1.0},
        {"name": "Citrus", "accords": ["citrus", "fresh"], "final_score": 0.95},
    ]
    ranked = regional.apply(results, hot)
    assert ranked[0]["name"] == "Citrus"


def test_reset_failed_targets(tmpdb):
    tmpdb.enqueue_url("https://x/perfume/a/b-9.html")
    tmpdb.mark_target_failed("https://x/perfume/a/b-9.html", "boom")
    tmpdb.mark_target_failed("https://x/perfume/a/b-9.html", "boom")
    tmpdb.mark_target_failed("https://x/perfume/a/b-9.html", "boom")  # -> failed
    assert tmpdb.reset_failed_targets() == 1
    assert tmpdb.count_targets_by_status().get("pending") == 1
