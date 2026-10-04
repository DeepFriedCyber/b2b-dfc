"""Data models for the Industry Intelligence Layer.

These records mirror ``docs/industry-intelligence-v0.01.md`` §3–§5 and §9. They are
deliberately declarative: vocabulary, structure and record-level invariants only.

No resolution, ambiguity handling or query-plan behaviour belongs in this module.
Those are separate concerns, out of scope for v0.01 phase 1.

Records are frozen dataclasses so that a loaded ontology is immutable and
reproducible (spec §13, determinism).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "Alias",
    "AliasType",
    "Concept",
    "ConceptStatus",
    "ConceptType",
    "Domain",
    "Relationship",
    "RelationshipType",
    "SearchPolicy",
    "TerminologyMaturity",
]


class Domain(str, Enum):
    """Controlled domain values.

    Exactly two values exist (spec §3). A concept belongs to one or more, so
    cross-domain meaning is expressed as ``[CYBERSECURITY, AI]`` rather than by
    inventing an intersection pseudo-domain.
    """

    CYBERSECURITY = "CYBERSECURITY"
    AI = "AI"


class ConceptType(str, Enum):
    """What kind of thing a concept denotes (spec §4.1)."""

    DISCIPLINE = "DISCIPLINE"
    CAPABILITY = "CAPABILITY"
    TECHNOLOGY = "TECHNOLOGY"
    PRODUCT_CATEGORY = "PRODUCT_CATEGORY"
    SERVICE_CATEGORY = "SERVICE_CATEGORY"
    THREAT = "THREAT"
    RISK = "RISK"
    CONTROL = "CONTROL"
    PROTOCOL = "PROTOCOL"
    FRAMEWORK = "FRAMEWORK"
    STANDARD = "STANDARD"
    CONCEPT = "CONCEPT"


class ConceptStatus(str, Enum):
    """Concept lifecycle state (spec §4.2)."""

    ACTIVE = "ACTIVE"
    CANDIDATE = "CANDIDATE"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"
    MERGED = "MERGED"


class TerminologyMaturity(str, Enum):
    """How settled the surrounding language is (spec §4.3).

    Metadata only. This must not gate, reorder or block resolution in v0.01.
    """

    STABLE = "STABLE"
    ESTABLISHED = "ESTABLISHED"
    EMERGING = "EMERGING"
    UNSETTLED = "UNSETTLED"


class AliasType(str, Enum):
    """The nature of an alias term (spec §5.2).

    There is deliberately no ``AMBIGUOUS_ALIAS`` member. Ambiguity is a property
    of an alias record (``Alias.ambiguous``), not of its type, so the two
    dimensions can evolve independently.
    """

    EXACT_ALIAS = "EXACT_ALIAS"
    ABBREVIATION = "ABBREVIATION"
    COMMON_NAME = "COMMON_NAME"
    MARKET_TERM = "MARKET_TERM"
    LEGACY_TERM = "LEGACY_TERM"
    MISSPELLING = "MISSPELLING"


class RelationshipType(str, Enum):
    """Typed, directional concept-to-concept edges (spec §9).

    ``MAY_*`` variants are distinct from their definitive counterparts:
    ``MAY_PROVIDE`` is not ``PROVIDES`` (spec §9.3).
    """

    BROADER = "BROADER"
    NARROWER = "NARROWER"
    RELATED = "RELATED"
    PART_OF = "PART_OF"
    USES = "USES"
    MAY_USE = "MAY_USE"
    PROVIDES = "PROVIDES"
    MAY_PROVIDE = "MAY_PROVIDE"
    APPLIES_TO = "APPLIES_TO"
    AFFECTS = "AFFECTS"
    MITIGATES = "MITIGATES"
    DETECTS = "DETECTS"
    PROTECTS = "PROTECTS"
    IMPLEMENTS = "IMPLEMENTS"
    REQUIRES = "REQUIRES"


class SearchPolicy(str, Enum):
    """Whether traversing a relationship may expand a retrieval query (spec §9.2)."""

    SAFE = "SAFE"
    CONSERVATIVE = "CONSERVATIVE"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    NONE = "NONE"


@dataclass(frozen=True)
class Concept:
    """A controlled meaning (spec §4).

    ``domains`` is a tuple of one or more :class:`Domain` values, not a singular
    field, so cross-domain concepts need no artificial third domain.
    """

    concept_id: str
    preferred_label: str
    definition: str
    domains: tuple[Domain, ...]
    concept_type: ConceptType
    status: ConceptStatus
    terminology_maturity: TerminologyMaturity

    def __post_init__(self) -> None:
        if not self.domains:
            raise ValueError(
                f"concept {self.concept_id!r} must belong to at least one domain"
            )

    def is_canonical(self) -> bool:
        """Whether normal deterministic resolution may treat this as canonical.

        Only ``ACTIVE`` concepts are canonical (spec §4.2, AGENTS.md §5.1). A
        ``CANDIDATE`` concept must never silently behave as a canonical concept.
        """
        return self.status is ConceptStatus.ACTIVE


@dataclass(frozen=True)
class Alias:
    """An independent term record pointing at one or more concepts (spec §5.1).

    Alias type and ambiguity are orthogonal. ``MCP`` is an ``ABBREVIATION`` with
    ``ambiguous=True``; ``EDR`` is an ``ABBREVIATION`` with ``ambiguous=False``.

    ``candidates`` is a tuple because the architecture must permit an alias to
    denote more than one concept in future.
    """

    alias_id: str
    surface_form: str
    alias_type: AliasType
    candidates: tuple[str, ...]
    ambiguous: bool
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError(
                f"alias {self.alias_id!r} must reference at least one concept"
            )


@dataclass(frozen=True)
class Relationship:
    """A typed, directional edge between two concepts (spec §9.1).

    ``search_policy`` is mandatory and never defaulted: graph connectivity must
    not automatically become query expansion (AGENTS.md §6).
    """

    relationship_id: str
    from_concept_id: str
    to_concept_id: str
    relationship_type: RelationshipType
    search_policy: SearchPolicy
    notes: str = ""

    def __post_init__(self) -> None:
        if self.from_concept_id == self.to_concept_id:
            raise ValueError(
                f"relationship {self.relationship_id!r} cannot link a concept to itself"
            )