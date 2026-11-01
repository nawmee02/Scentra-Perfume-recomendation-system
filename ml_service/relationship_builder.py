"""
Relationship ingestion pipeline (evidence → confidence).

Populates the graph from multiple evidence sources, each contributing a base
confidence that merges via noisy-OR in db.add_relationship (stronger evidence is
never overwritten). Cheap sources run now without a browser:

  shared_perfumer      → shares_dna_with   (base 0.40)
  accord fingerprint   → smells_like       (0.35 + 0.5·Jaccard, gated ≥0.6)

Candidates are bounded to each perfume's top dense neighbours (via Qdrant), so
the job is O(N·k) not O(N²). Crowdsourced "reminds me of" (clone_of/smells_like
at high confidence) and clone databases plug into the same add_relationship merge
once the Playwright box scraper lands.
"""
import logging

import db
import knowledge
import qdrant_store

log = logging.getLogger("rel_builder")

CANDIDATES = 26
ACCORD_JACCARD_MIN = 0.6
SRC_PERFUMER = "shared_perfumer"
SRC_ACCORD = "accord_fingerprint"


def _accord_set(row: dict) -> set[str]:
    return {a.lower() for a in knowledge.accords_list(row.get("accords"))}


def build_for_perfume(seed: dict) -> int:
    """Derive evidence edges for one perfume against its dense neighbours."""
    fid = db.frag_id(seed.get("url"))
    if not fid:
        return 0
    seed_id = seed["id"]
    seed_accords = _accord_set(seed)
    seed_perf = (seed.get("perfumer1") or "").strip().lower()

    neighbours = qdrant_store.search(knowledge.compile_embedding_doc(seed), CANDIDATES)
    edges = 0
    for nb in neighbours:
        nid = nb.get("db_id")
        if nid is None or nid == seed_id:
            continue
        row = db.get_by_id(nid)
        if not row:
            continue
        dfid = db.frag_id(row.get("url"))
        if not dfid:
            continue

        if seed_perf and seed_perf != "unknown" \
                and (row.get("perfumer1") or "").strip().lower() == seed_perf:
            db.add_relationship(fid, dfid, "shares_dna_with", confidence=0.40,
                                source=SRC_PERFUMER, dst_url=row.get("url"),
                                dst_name=row.get("name"))
            edges += 1

        nb_accords = _accord_set(row)
        if seed_accords and nb_accords:
            jac = len(seed_accords & nb_accords) / len(seed_accords | nb_accords)
            if jac >= ACCORD_JACCARD_MIN:
                db.add_relationship(fid, dfid, "smells_like",
                                    confidence=round(0.35 + 0.5 * jac, 3),
                                    source=SRC_ACCORD, dst_url=row.get("url"),
                                    dst_name=row.get("name"))
                edges += 1
    return edges


def build_batch(seeds: list[dict]) -> dict:
    """Build edges for a batch of perfume rows. Returns metrics."""
    perfumes = edges = 0
    for seed in seeds:
        e = build_for_perfume(seed)
        edges += e
        perfumes += 1
    log.info("relationship_builder: %d perfumes → %d edges", perfumes, edges)
    return {"perfumes": perfumes, "edges": edges}


def build_page(offset: int = 0, limit: int = 200) -> dict:
    """Resumable page over the catalog (for the background worker)."""
    seeds = db.iter_perfumes(offset, limit)
    result = build_batch(seeds)
    result["next_offset"] = offset + len(seeds)
    result["done"] = len(seeds) < limit
    return result


# --------------------------------------------------------------------------- #
# Structural inference — concentration siblings & collection lines (offline)
# --------------------------------------------------------------------------- #

# Guards against accidental mega-groups from generic/empty base names.
_MAX_GROUP = 12
_CONF_COLLECTION = 0.75
_CONF_PARENT = 0.70


def _canonical(members: list[dict]) -> dict:
    """Pick the line's parent: the variant with no concentration, else earliest year."""
    plain = [m for m in members if not knowledge.detect_concentration(m["name"])]
    pool = plain or members
    return min(pool, key=lambda m: m.get("year") or 9999)


def infer_structural_relationships() -> dict:
    """Deterministic, offline: group catalog by (brand, base name); within a group
    link concentration siblings as same_collection and each variant to the line
    parent as parent_line. Bulk-UPSERT, idempotent, never merges concentrations."""
    rows = db.get_catalog_min()
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        fid = db.frag_id(r.get("url"))
        bn = knowledge.base_name(r.get("name", ""))
        if not fid or not bn:
            continue
        key = ((r.get("brand") or "").strip().lower(), bn)
        groups.setdefault(key, []).append({**r, "fid": fid})

    edges: list[tuple] = []
    group_count = 0
    for members in groups.values():
        if not (2 <= len(members) <= _MAX_GROUP):
            continue
        group_count += 1
        canon = _canonical(members)
        for a in members:
            for b in members:
                if a["fid"] != b["fid"]:
                    edges.append((a["fid"], b["fid"], "same_collection",
                                  _CONF_COLLECTION, "structural", b.get("url"), b.get("name")))
            if a["fid"] != canon["fid"]:
                edges.append((a["fid"], canon["fid"], "parent_line",
                              _CONF_PARENT, "structural", canon.get("url"), canon.get("name")))

    written = db.add_relationships_bulk(edges)
    log.info("structural inference: %d groups → %d edges", group_count, written)
    return {"groups": group_count, "edges": written}
