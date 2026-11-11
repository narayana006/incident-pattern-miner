"""Turn incident text into TF-IDF vectors and group similar incidents."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .ingest import Incident

Vector = dict[str, float]

STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had
has have having he her here hers him his how i if in into is it its itself just me more most my no
nor not now of off on once only or other our out over own same she should so some such than that
the their them then there these they this those through to too under until up very was we were
what when where which while who whom why will with would you your
incident incidents postmortem outage issue issues problem problems service services team teams
engineer engineers oncall call responder customer customers user users impact impacted affected
cause caused causes root during started began minutes minute hours hour utc time times summary
happened went wrong found took one two three several many new old production prod system systems
around approximately about still later first until since were being got get made make per every
because which due also back until led result resulted resulting caused however within without
""".split())

# Common operations vocabulary folded onto one term, so that "cert expired"
# and "certificate expiry" count as the same thing.
SYNONYMS = {
    "cert": "certificate", "certs": "certificate", "certificates": "certificate", "tls": "certificate",
    "ssl": "certificate", "x509": "certificate",
    "expiry": "expire", "expired": "expire", "expires": "expire", "expiration": "expire",
    "expiring": "expire", "renewal": "renew", "renewed": "renew", "renewing": "renew",
    "renewals": "renew",
    "config": "configuration", "configs": "configuration", "configurations": "configuration",
    "misconfiguration": "configuration", "misconfigured": "configuration", "setting": "configuration",
    "settings": "configuration", "flag": "configuration", "flags": "configuration",
    "db": "database", "databases": "database", "postgres": "database", "postgresql": "database",
    "mysql": "database",
    "deploy": "deploy", "deployed": "deploy", "deployment": "deploy", "deployments": "deploy",
    "deploying": "deploy", "release": "deploy", "released": "deploy", "rollout": "deploy",
    "rollouts": "deploy", "releases": "deploy",
    "pushed": "push", "pushes": "push", "pushing": "push",
    "connections": "connection", "conn": "connection", "pools": "pool",
    "oom": "memory", "oomkilled": "memory",
    "disks": "disk", "volume": "disk", "volumes": "disk", "storage": "disk",
    "resolver": "dns", "resolvers": "dns", "nameserver": "dns",
    "queues": "queue", "backlog": "queue",
    "timeouts": "timeout", "timed": "timeout",
    "retries": "retry", "retried": "retry", "retrying": "retry",
}

_WORD = re.compile(r"[a-z][a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-case words with stopwords removed and common variants folded together."""
    tokens = []
    # Host names such as api.example.com say where, not what, so they are dropped.
    text = re.sub(r"\b[\w-]+(?:\.[\w-]+)+\b", " ", text.lower())
    for word in _WORD.findall(text):
        if word in STOPWORDS:
            continue
        word = SYNONYMS.get(word, word)
        if len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
            word = SYNONYMS.get(word[:-1], word[:-1])
        if word not in STOPWORDS:
            tokens.append(word)
    return tokens


def tfidf_vectors(texts: list[str]) -> list[Vector]:
    """Unit-length TF-IDF vectors (sub-linear term frequency, smoothed IDF)."""
    documents = [Counter(tokenize(text)) for text in texts]
    document_frequency = Counter(term for counts in documents for term in counts)
    total = len(documents)
    vectors = []
    for counts in documents:
        vector = {term: (1 + math.log(count)) * (math.log((1 + total) / (1 + document_frequency[term])) + 1)
                  for term, count in counts.items()}
        norm = math.sqrt(sum(weight * weight for weight in vector.values()))
        vectors.append({term: weight / norm for term, weight in vector.items()} if norm else {})
    return vectors


def cosine(a: Vector, b: Vector) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


def cluster_vectors(vectors: list[Vector], threshold: float) -> list[list[int]]:
    """Average-linkage agglomerative clustering.

    Repeatedly merges the two most similar groups until no pair has an average
    pairwise cosine similarity of at least `threshold`. Returns groups of
    indexes into `vectors`. Deterministic: ties go to the earliest pair.
    """
    count = len(vectors)
    similarity = [[cosine(vectors[i], vectors[j]) if i != j else 1.0 for j in range(count)]
                  for i in range(count)]
    groups: dict[int, list[int]] = {i: [i] for i in range(count)}
    # between[a][b] holds the average similarity between groups a and b.
    between = {i: {j: similarity[i][j] for j in range(count) if j != i} for i in range(count)}
    while len(groups) > 1:
        best, pair = threshold, None
        for a in groups:
            for b, value in between[a].items():
                if a < b and (value > best or (pair is None and value >= best)):
                    best, pair = value, (a, b)
        if pair is None:
            break
        a, b = pair
        size_a, size_b = len(groups[a]), len(groups[b])
        for other in groups:
            if other in (a, b):
                continue
            merged = (between[a][other] * size_a + between[b][other] * size_b) / (size_a + size_b)
            between[a][other] = between[other][a] = merged
            del between[other][b]
        del between[b], between[a][b]
        groups[a].extend(groups.pop(b))
    return [sorted(members) for members in groups.values()]


@dataclass(frozen=True)
class Theme:
    label: str
    terms: tuple[str, ...]  # most characteristic terms, strongest first
    incidents: tuple[Incident, ...]  # oldest first


def _top_terms(vectors: list[Vector], limit: int) -> tuple[str, ...]:
    """Terms with the highest total weight that appear in at least half the group."""
    weight: Counter[str] = Counter()
    presence: Counter[str] = Counter()
    for vector in vectors:
        weight.update(vector)
        presence.update(vector.keys())
    needed = max(2, math.ceil(len(vectors) / 2)) if len(vectors) > 1 else 1
    shared = [term for term in weight if presence[term] >= needed] or list(weight)
    return tuple(sorted(shared, key=lambda term: (-weight[term], term))[:limit])


def find_themes(incidents: list[Incident], threshold: float = 0.15, min_size: int = 2,
                vectors: list[Vector] | None = None) -> tuple[list[Theme], list[Incident]]:
    """Group incidents into themes.

    Returns the themes (largest first) and the incidents that did not fall
    into any group of at least `min_size`. Pass `vectors` to cluster on your
    own embeddings instead of the built-in TF-IDF; labels still come from the
    incident text.
    """
    if not incidents:
        return [], []
    label_vectors = tfidf_vectors([incident.text for incident in incidents])
    if vectors is None:
        vectors = label_vectors
    elif len(vectors) != len(incidents):
        raise ValueError("vectors must have one entry per incident")
    themes, singles = [], []
    for members in cluster_vectors(vectors, threshold):
        group = sorted((incidents[i] for i in members), key=lambda inc: (inc.date, inc.id))
        if len(group) < min_size:
            singles.extend(group)
            continue
        terms = _top_terms([label_vectors[i] for i in members], 6)
        themes.append(Theme(" / ".join(terms[:3]), terms, tuple(group)))
    themes.sort(key=lambda theme: (-len(theme.incidents), theme.label))
    singles.sort(key=lambda incident: (incident.date, incident.id))
    return themes, singles


def dense_to_vector(values: list[float]) -> Vector:
    """Convert a dense embedding into the unit-length sparse form used here."""
    norm = math.sqrt(sum(value * value for value in values))
    return {str(index): value / norm for index, value in enumerate(values) if value} if norm else {}
