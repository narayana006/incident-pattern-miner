import math
from datetime import date

import pytest

from incident_pattern_miner.cluster import (cluster_vectors, cosine, dense_to_vector, find_themes,
                                            tfidf_vectors, tokenize)
from incident_pattern_miner.ingest import Incident


def incident(number, text, day=None):
    return Incident(id=f"I{number}", title=text, date=day or date(2026, 1, number), text=text)


def test_tokenize_folds_variants_and_drops_noise():
    assert tokenize("The certs EXPIRED on api.example.com during the incident") == ["certificate", "expire"]
    assert tokenize("Config pushes and deployments") == ["configuration", "push", "deploy"]
    assert tokenize("database connections, pools, queues") == ["database", "connection", "pool", "queue"]
    assert tokenize("status of the bus address") == ["status", "bus", "address"]


def test_tfidf_vectors_are_unit_length_and_weight_rare_terms():
    vectors = tfidf_vectors(["certificate expired", "certificate renewed", "certificate rotated", ""])
    assert math.isclose(sum(w * w for w in vectors[0].values()), 1.0)
    assert vectors[0]["expire"] > vectors[0]["certificate"]
    assert vectors[3] == {}
    assert cosine(vectors[0], vectors[3]) == 0.0
    assert math.isclose(cosine(vectors[0], vectors[0]), 1.0)


def test_cluster_vectors_average_linkage():
    a, b, c = {"x": 1.0}, {"x": 0.8, "y": 0.6}, {"y": 1.0}
    # a-b 0.8, b-c 0.6, a-c 0.0: a and b merge, then the group averages 0.3 with c.
    assert cluster_vectors([a, b, c], 0.5) == [[0, 1], [2]]
    assert cluster_vectors([a, b, c], 0.3) == [[0, 1, 2]]
    assert cluster_vectors([a, b, c], 0.9) == [[0], [1], [2]]
    assert cluster_vectors([], 0.5) == []
    assert cluster_vectors([a], 0.5) == [[0]]


def test_find_themes_groups_and_labels():
    incidents = [
        incident(1, "TLS certificate expired on the gateway, renewal was manual"),
        incident(2, "Database connection pool exhausted by slow query"),
        incident(3, "Certificate expiry on the mail relay, no renewal alert"),
        incident(4, "Config push removed the backend pool without validation"),
        incident(5, "Auth database ran out of connections after pool size change"),
        incident(6, "Cert expired for partner API, renewal reminder missed"),
        incident(7, "Forklift drove into the rack"),
    ]
    themes, one_offs = find_themes(incidents)
    assert [[i.id for i in t.incidents] for t in themes] == [["I1", "I3", "I6"], ["I2", "I5"]]
    assert themes[0].terms[:2] == ("certificate", "expire")
    assert themes[0].label.startswith("certificate / expire")
    assert "connection" in themes[1].terms and "database" in themes[1].terms
    assert [i.id for i in one_offs] == ["I4", "I7"]


def test_find_themes_min_size_and_empty():
    incidents = [incident(1, "certificate expired"), incident(2, "certificate expired again"),
                 incident(3, "disk full")]
    themes, one_offs = find_themes(incidents, min_size=3)
    assert themes == [] and len(one_offs) == 3
    assert find_themes([]) == ([], [])


def test_find_themes_accepts_external_vectors():
    incidents = [incident(1, "alpha outage"), incident(2, "beta failure"), incident(3, "gamma crash")]
    vectors = [dense_to_vector([1, 0]), dense_to_vector([0, 2]), dense_to_vector([3, 0.1])]
    themes, one_offs = find_themes(incidents, threshold=0.9, vectors=vectors)
    assert [[i.id for i in t.incidents] for t in themes] == [["I1", "I3"]]
    assert [i.id for i in one_offs] == ["I2"]
    with pytest.raises(ValueError):
        find_themes(incidents, vectors=vectors[:2])
    assert dense_to_vector([0, 0]) == {}
