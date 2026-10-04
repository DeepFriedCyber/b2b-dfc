"""Loading and structural validation for the controlled ontology (spec §4, §9).

The store is deliberately passive. It holds concepts, aliases and relationships,
and refuses data that is internally inconsistent. It performs no resolution, no
ambiguity detection and no query planning — those are later phases.

Uniqueness and referential integrity are enforced here rather than in
``models.py`` because they are properties of a whole ontology, not of a single
record.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .models import (
    Alias,
    AliasType,
    Concept,
    ConceptStatus,
    ConceptType,
    Domain,
    Relationship,
    RelationshipType,
    SearchPolicy,
    TerminologyMaturity,
)

__all__ = [
    "Ontology",
    "OntologyValidationError",
    "default_ontology_path",
    "load_ontology",
]


class OntologyValidationError(ValueError):
    """Raised when ontology data is missing, malformed or internally inconsistent."""


@dataclass(frozen=True)
class Ontology:
    """An immutable, validated set of concepts, aliases and relationships."""

    concepts: tuple[Concept, ...] = ()
    aliases: tuple[Alias, ...] = ()
    relationships: tuple[Relationship, ...] = ()

    def concept_index(self) -> Mapping[str, Concept]:
        """Concepts keyed by ``concept_id``."""
        return {concept.concept_id: concept for concept in self.concepts}

    def alias_index(self) -> Mapping[str, Alias]:
        """Aliases keyed by exact ``surface_form``."""
        return {alias.surface_form: alias for alias in self.aliases}

    def relationship_index(self) -> Mapping[str, Relationship]:
        """Relationships keyed by ``relationship_id``."""
        return {
            relationship.relationship_id: relationship
            for relationship in self.relationships
        }

    def get_concept(self, concept_id: str) -> Concept | None:
        """Return the concept, or ``None`` when it is not in the ontology."""
        return self.concept_index().get(concept_id)

    def canonical_concepts(self) -> tuple[Concept, ...]:
        """Concepts that normal deterministic resolution may treat as canonical."""
        return tuple(concept for concept in self.concepts if concept.is_canonical())

    def canonical_concept_ids(self) -> tuple[str, ...]:
        return tuple(concept.concept_id for concept in self.canonical_concepts())

    def aliases_for(self, concept_id: str) -> tuple[Alias, ...]:
        """Aliases that list ``concept_id`` among their candidates."""
        return tuple(
            alias for alias in self.aliases if concept_id in alias.candidates
        )

    def relationships_from(self, concept_id: str) -> tuple[Relationship, ...]:
        """Outgoing edges from ``concept_id``."""
        return tuple(
            relationship
            for relationship in self.relationships
            if relationship.from_concept_id == concept_id
        )

    def relationships_to(self, concept_id: str) -> tuple[Relationship, ...]:
        """Incoming edges to ``concept_id``."""
        return tuple(
            relationship
            for relationship in self.relationships
            if relationship.to_concept_id == concept_id
        )

    def relationships_of(self, concept_id: str) -> tuple[Relationship, ...]:
        """All edges touching ``concept_id`` in either direction."""
        return self.relationships_from(concept_id) + self.relationships_to(
            concept_id
        )


def default_ontology_path() -> Path:
    """Location of the seed ontology shipped with the repository."""
    return Path(__file__).resolve().parents[3] / "data" / "ontology.seed.json"


def _require(mapping: Mapping[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise OntologyValidationError(f"{context}: missing required field {key!r}")
    return mapping[key]


def _parse_concept(raw: Mapping[str, Any], index: int) -> Concept:
    context = f"concepts[{index}]"
    if not isinstance(raw, Mapping):
        raise OntologyValidationError(f"{context}: expected an object")

    concept_id = _require(raw, "concept_id", context)
    domains_raw = _require(raw, "domains", context)
    if not isinstance(domains_raw, Sequence) or isinstance(domains_raw, (str, bytes)):
        raise OntologyValidationError(f"{context}: 'domains' must be a list")
    if not domains_raw:
        raise OntologyValidationError(f"{context}: 'domains' must not be empty")

    try:
        domains = tuple(Domain(value) for value in domains_raw)
    except ValueError as error:
        raise OntologyValidationError(f"{context}: {error}") from error

    return Concept(
        concept_id=concept_id,
        preferred_label=_require(raw, "preferred_label", context),
        definition=_require(raw, "definition", context),
        domains=domains,
        concept_type=_parse_enum(
            ConceptType, _require(raw, "concept_type", context), context
        ),
        status=_parse_enum(ConceptStatus, _require(raw, "status", context), context),
        terminology_maturity=_parse_enum(
            TerminologyMaturity,
            _require(raw, "terminology_maturity", context),
            context,
        ),
    )


def _parse_alias(raw: Mapping[str, Any], index: int) -> Alias:
    context = f"aliases[{index}]"
    if not isinstance(raw, Mapping):
        raise OntologyValidationError(f"{context}: expected an object")

    candidates_raw = _require(raw, "candidates", context)
    if not isinstance(candidates_raw, Sequence) or isinstance(
        candidates_raw, (str, bytes)
    ):
        raise OntologyValidationError(f"{context}: 'candidates' must be a list")

    ambiguous_raw = _require(raw, "ambiguous", context)
    if not isinstance(ambiguous_raw, bool):
        raise OntologyValidationError(f"{context}: 'ambiguous' must be a boolean")

    return Alias(
        alias_id=_require(raw, "alias_id", context),
        surface_form=_require(raw, "surface_form", context),
        alias_type=_parse_enum(
            AliasType, _require(raw, "alias_type", context), context
        ),
        candidates=tuple(candidates_raw),
        ambiguous=ambiguous_raw,
        notes=raw.get("notes", ""),
    )


def _parse_relationship(raw: Mapping[str, Any], index: int) -> Relationship:
    context = f"relationships[{index}]"
    if not isinstance(raw, Mapping):
        raise OntologyValidationError(f"{context}: expected an object")

    return Relationship(
        relationship_id=_require(raw, "relationship_id", context),
        from_concept_id=_require(raw, "from_concept_id", context),
        to_concept_id=_require(raw, "to_concept_id", context),
        relationship_type=_parse_enum(
            RelationshipType, _require(raw, "relationship_type", context), context
        ),
        search_policy=_parse_enum(
            SearchPolicy, _require(raw, "search_policy", context), context
        ),
        notes=raw.get("notes", ""),
    )


def _parse_enum(enum_type: type, value: Any, context: str) -> Any:
    try:
        return enum_type(value)
    except ValueError as error:
        raise OntologyValidationError(
            f"{context}: {value!r} is not a valid {enum_type.__name__}"
        ) from error


def _validate_unique(
    values: Sequence[str], kind: str
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise OntologyValidationError(
            f"duplicate {kind}: {sorted(duplicates)}"
        )


def _validate_integrity(ontology: Ontology) -> None:
    _validate_unique(
        [concept.concept_id for concept in ontology.concepts], "concept_id"
    )
    _validate_unique(
        [concept.preferred_label for concept in ontology.concepts], "preferred_label"
    )
    _validate_unique([alias.alias_id for alias in ontology.aliases], "alias_id")
    _validate_unique(
        [alias.surface_form for alias in ontology.aliases], "alias surface_form"
    )
    _validate_unique(
        [relationship.relationship_id for relationship in ontology.relationships],
        "relationship_id",
    )

    known = set(ontology.concept_index())

    for alias in ontology.aliases:
        for candidate in alias.candidates:
            if candidate not in known:
                raise OntologyValidationError(
                    f"alias {alias.alias_id!r} references unknown concept {candidate!r}"
                )

    for relationship in ontology.relationships:
        if relationship.from_concept_id not in known:
            raise OntologyValidationError(
                f"relationship {relationship.relationship_id!r} has unknown "
                f"from_concept_id {relationship.from_concept_id!r}"
            )
        if relationship.to_concept_id not in known:
            raise OntologyValidationError(
                f"relationship {relationship.relationship_id!r} has unknown "
                f"to_concept_id {relationship.to_concept_id!r}"
            )


def load_ontology(path: str | Path) -> Ontology:
    """Read, parse and validate an ontology JSON document.

    Raises :class:`OntologyValidationError` for a missing file, malformed JSON,
    an unknown enum value, a duplicate identifier or a dangling reference.
    """
    path = Path(path)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise OntologyValidationError(f"cannot read ontology file {path}: {error}") from error

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise OntologyValidationError(f"{path} is not valid JSON: {error}") from error

    if not isinstance(payload, Mapping):
        raise OntologyValidationError(f"{path}: expected a JSON object at the root")

    for key in ("concepts", "aliases", "relationships"):
        if key not in payload:
            raise OntologyValidationError(f"{path}: missing required section {key!r}")
        if not isinstance(payload[key], list):
            raise OntologyValidationError(f"{path}: section {key!r} must be a list")

    ontology = Ontology(
        concepts=tuple(
            _parse_concept(raw, index) for index, raw in enumerate(payload["concepts"])
        ),
        aliases=tuple(
            _parse_alias(raw, index) for index, raw in enumerate(payload["aliases"])
        ),
        relationships=tuple(
            _parse_relationship(raw, index)
            for index, raw in enumerate(payload["relationships"])
        ),
    )

    _validate_integrity(ontology)
    return ontology