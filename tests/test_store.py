"""Structural tests for the ontology store and the seed ontology.

These assert that the seed data is internally consistent and obeys the
constraints in ``docs/industry-intelligence-v0.01.md`` §4, §5, §9 and §10.
No resolution, ambiguity or query-plan behaviour is exercised.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from b2b_dfc.intelligence.models import (
    AliasType,
    ConceptStatus,
    Domain,
    RelationshipType,
    SearchPolicy,
)
from b2b_dfc.intelligence.store import (
    Ontology,
    OntologyValidationError,
    default_ontology_path,
    load_ontology,
)


@pytest.fixture(scope="module")
def seed() -> Ontology:
    return load_ontology(default_ontology_path())


@pytest.fixture(scope="module")
def seed_path() -> Path:
    return default_ontology_path()


class TestSeedLoading:
    def test_seed_file_exists_and_is_json(self, seed_path: Path):
        assert seed_path.is_file()
        assert seed_path.suffix == ".json"
        json.loads(seed_path.read_text(encoding="utf-8"))

    def test_loading_is_deterministic(self, seed_path: Path):
        """Same input must produce an equivalent store every time."""
        assert load_ontology(seed_path) == load_ontology(seed_path)


class TestSeedScope:
    def test_seed_concept_count_is_within_initial_target(self, seed: Ontology):
        """Spec §10: a 12–15 concept seed, deliberately below the 50–75 target."""
        assert 12 <= len(seed.concepts) <= 15

    def test_loading_introduces_no_concepts_beyond_the_file(
        self, seed: Ontology, seed_path: Path
    ):
        """Spec §6: loading must not create concepts for unknown terminology."""
        declared = json.loads(seed_path.read_text(encoding="utf-8"))["concepts"]
        assert len(seed.concepts) == len(declared)

    def test_seed_declares_aliases_and_relationships(self, seed: Ontology):
        assert seed.aliases, "seed ontology must carry aliases"
        assert seed.relationships, "seed ontology must carry relationships"


class TestIdentifierUniqueness:
    def test_concept_ids_are_unique(self, seed: Ontology):
        ids = [c.concept_id for c in seed.concepts]
        assert len(ids) == len(set(ids))

    def test_preferred_labels_are_unique(self, seed: Ontology):
        """Spec §10.2 item 3."""
        labels = [c.preferred_label for c in seed.concepts]
        assert len(labels) == len(set(labels))

    def test_alias_ids_are_unique(self, seed: Ontology):
        ids = [a.alias_id for a in seed.aliases]
        assert len(ids) == len(set(ids))

    def test_alias_surface_forms_are_unique(self, seed: Ontology):
        forms = [a.surface_form for a in seed.aliases]
        assert len(forms) == len(set(forms))

    def test_relationship_ids_are_unique(self, seed: Ontology):
        ids = [r.relationship_id for r in seed.relationships]
        assert len(ids) == len(set(ids))


class TestDomainAssignments:
    def test_every_concept_has_at_least_one_domain(self, seed: Ontology):
        assert all(concept.domains for concept in seed.concepts)

    def test_domains_are_limited_to_the_two_initial_values(self, seed: Ontology):
        """Spec §3 / §10.2 item 2."""
        for concept in seed.concepts:
            assert set(concept.domains) <= {Domain.CYBERSECURITY, Domain.AI}

    def test_cross_domain_concepts_use_multiple_entries(self, seed: Ontology):
        """A cross-domain concept uses two entries, never a pseudo-domain."""
        by_id = seed.concept_index()
        assert by_id["mcp_security"].domains == (
            Domain.CYBERSECURITY,
            Domain.AI,
        )
        assert by_id["ai_red_teaming"].domains == (
            Domain.CYBERSECURITY,
            Domain.AI,
        )
        assert by_id["managed_detection_and_response"].domains == (
            Domain.CYBERSECURITY,
        )


class TestReferentialIntegrity:
    def test_every_alias_candidate_resolves_to_a_concept(self, seed: Ontology):
        """Spec §7 invariant: no dangling concept references."""
        known = set(seed.concept_index())
        for alias in seed.aliases:
            for candidate in alias.candidates:
                assert candidate in known, f"{alias.alias_id} -> {candidate}"

    def test_every_relationship_endpoint_resolves(self, seed: Ontology):
        known = set(seed.concept_index())
        for relationship in seed.relationships:
            assert relationship.from_concept_id in known
            assert relationship.to_concept_id in known

    def test_aliases_expose_their_concepts(self, seed: Ontology):
        assert seed.aliases_for("model_context_protocol")
        assert seed.aliases_for("managed_detection_and_response")


class TestAcronymsAreAliasesNotConcepts:
    """Spec §10.1 / AGENTS.md §5.2: an acronym never earns a canonical concept."""

    @pytest.mark.parametrize(
        "acronym,expected_id",
        [
            ("MDR", "managed_detection_and_response"),
            ("EDR", "endpoint_detection_and_response"),
            ("SOC", "security_operations_center"),
            ("SIEM", "security_information_and_event_management"),
            ("MFA", "multi_factor_authentication"),
            ("LLM", "large_language_model"),
        ],
    )
    def test_acronym_resolves_as_an_abbreviation_alias(
        self, seed: Ontology, acronym: str, expected_id: str
    ):
        alias = seed.alias_index()[acronym]
        assert alias.alias_type is AliasType.ABBREVIATION
        assert alias.candidates == (expected_id,)

    @pytest.mark.parametrize("acronym", ["MDR", "EDR", "SOC", "SIEM", "MFA", "LLM"])
    def test_acronym_is_not_its_own_concept(self, seed: Ontology, acronym: str):
        labels = {c.preferred_label.upper() for c in seed.concepts}
        ids = set(seed.concept_index())
        assert acronym not in labels
        assert acronym not in ids

    def test_mdr_and_spelled_out_form_are_one_concept(self, seed: Ontology):
        """No duplicate concept created solely for the acronym (spec §10.1)."""
        alias = seed.alias_index()["MDR"]
        concept = seed.get_concept("managed_detection_and_response")
        assert concept is not None
        assert concept.preferred_label == "Managed Detection and Response"
        assert alias.candidates == (concept.concept_id,)
        assert seed.get_concept("mdr") is None

    def test_secops_alias_is_not_present(self, seed: Ontology):
        """`SecOps` was withdrawn rather than mapped to a new concept."""
        assert "SecOps" not in seed.alias_index()

    def test_no_concept_was_added_for_the_withdrawn_alias(self, seed: Ontology):
        labels = {c.preferred_label.lower() for c in seed.concepts}
        ids = set(seed.concept_index())
        assert "secops" not in labels
        assert "secops" not in ids


class TestAmbiguousAliasRepresentation:
    def test_mcp_is_an_abbreviation_with_ambiguity_flag(self, seed: Ontology):
        """Spec §5.3 worked example."""
        alias = seed.alias_index()["MCP"]
        assert alias.alias_type is AliasType.ABBREVIATION
        assert alias.ambiguous is True
        assert alias.candidates == ("model_context_protocol",)
        assert alias.notes

    def test_unambiguous_acronyms_are_not_flagged_ambiguous(self, seed: Ontology):
        for form in ("MDR", "EDR", "SOC", "MFA"):
            assert seed.alias_index()[form].ambiguous is False

    def test_seed_alias_types_are_all_declared_in_the_vocabulary(self, seed: Ontology):
        for alias in seed.aliases:
            assert isinstance(alias.alias_type, AliasType)


class TestLifecycleInSeed:
    def test_ai_red_teaming_is_active(self, seed: Ontology):
        """AI Red Teaming was promoted to a canonical, resolvable concept."""
        concept = seed.get_concept("ai_red_teaming")
        assert concept is not None
        assert concept.status is ConceptStatus.ACTIVE
        assert concept.is_canonical() is True
        assert "ai_red_teaming" in seed.canonical_concept_ids()

    def test_seed_canonical_set_excludes_every_non_active_concept(self, seed: Ontology):
        """Spec §4.2: only ACTIVE concepts may be treated as canonical.

        This asserts the invariant against whatever the seed contains, so it
        holds whether or not the seed currently includes a non-ACTIVE row.
        """
        non_active = {
            c.concept_id for c in seed.concepts if c.status is not ConceptStatus.ACTIVE
        }
        assert set(seed.canonical_concept_ids()).isdisjoint(non_active)

    def test_seed_canonical_ids_match_is_canonical_filter(self, seed: Ontology):
        assert set(seed.canonical_concept_ids()) == {
            c.concept_id for c in seed.concepts if c.is_canonical()
        }

    def test_lifecycle_filter_excludes_non_active_concepts(self, tmp_path: Path):
        """The lifecycle rule is enforced by the store, not by seed contents.

        Uses a synthetic ontology so the safeguard cannot be lost if the seed
        later contains only ACTIVE rows.
        """
        statuses = [
            "ACTIVE",
            "CANDIDATE",
            "REJECTED",
            "DEPRECATED",
            "MERGED",
        ]
        payload = {
            "concepts": [
                {
                    "concept_id": f"concept_{status.lower()}",
                    "preferred_label": f"Concept {status.title()}",
                    "definition": "Synthetic concept for lifecycle coverage.",
                    "domains": ["AI"],
                    "concept_type": "CONCEPT",
                    "status": status,
                    "terminology_maturity": "UNSETTLED",
                }
                for status in statuses
            ],
            "aliases": [],
            "relationships": [],
        }
        path = tmp_path / "ontology.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        ontology = load_ontology(path)

        assert ontology.canonical_concept_ids() == ("concept_active",)
        assert "concept_candidate" not in ontology.canonical_concept_ids()

    def test_canonical_filter_ignores_terminology_maturity(self, seed: Ontology):
        """Spec §4.3: maturity is metadata and must not gate resolution."""
        emerging_active = [
            c
            for c in seed.canonical_concepts()
            if c.terminology_maturity.value == "EMERGING"
        ]
        assert emerging_active, "seed should have ACTIVE concepts with EMERGING maturity"

    def test_every_concept_records_terminology_maturity(self, seed: Ontology):
        assert all(c.terminology_maturity is not None for c in seed.concepts)


class TestRelationshipPolicies:
    def test_every_relationship_has_an_explicit_policy(self, seed: Ontology):
        """Spec §9.1: search_policy is required, never defaulted."""
        assert all(
            isinstance(r.search_policy, SearchPolicy) for r in seed.relationships
        )

    def test_seed_exercises_every_search_policy(self, seed: Ontology):
        """All four policies must be represented so grading is meaningful."""
        used = {r.search_policy for r in seed.relationships}
        assert used == set(SearchPolicy)

    def test_no_may_relationship_is_safe_for_expansion(self, seed: Ontology):
        """Spec §5/§9.3: MAY_* must never silently become a resolved requirement."""
        for relationship in seed.relationships:
            if relationship.relationship_type in (
                RelationshipType.MAY_USE,
                RelationshipType.MAY_PROVIDE,
            ):
                assert relationship.search_policy is not SearchPolicy.SAFE, (
                    f"{relationship.relationship_id} may not be SAFE"
                )

    def test_may_relationships_carry_justification_notes(self, seed: Ontology):
        """Spec §9.1: notes justify MAY_* and DISCOVERY_ONLY edges."""
        for relationship in seed.relationships:
            if relationship.relationship_type in (
                RelationshipType.MAY_USE,
                RelationshipType.MAY_PROVIDE,
            ):
                assert relationship.notes.strip(), relationship.relationship_id

    def test_may_provide_edge_to_incident_response_is_not_safe(self, seed: Ontology):
        """The documented negative case must hold in the actual seed data."""
        edge = seed.relationship_index()["r_mdr_may_provide_incident_response"]
        assert edge.relationship_type is RelationshipType.MAY_PROVIDE
        assert edge.search_policy is not SearchPolicy.SAFE
        assert edge.from_concept_id == "managed_detection_and_response"
        assert edge.to_concept_id == "incident_response"

    def test_soc_may_use_siem_is_hedged_not_definitive(self, seed: Ontology):
        """SOC MAY_USE SIEM: common practice, not a definitional dependency."""
        edge = seed.relationship_index()["r_soc_may_use_siem"]
        assert edge.from_concept_id == "security_operations_center"
        assert edge.to_concept_id == "security_information_and_event_management"
        assert edge.relationship_type is RelationshipType.MAY_USE
        assert edge.search_policy is not SearchPolicy.SAFE
        assert edge.notes.strip()

    def test_agent_may_use_llm_is_hedged_not_definitive(self, seed: Ontology):
        """Agent MAY_USE LLM: common practice, not a definitional dependency."""
        edge = seed.relationship_index()["r_agent_may_use_llm"]
        assert edge.from_concept_id == "artificial_intelligence_agent"
        assert edge.to_concept_id == "large_language_model"
        assert edge.relationship_type is RelationshipType.MAY_USE
        assert edge.search_policy is not SearchPolicy.SAFE
        assert edge.notes.strip()

    def test_no_definitive_use_edge_remains_for_hedged_pairs(self, seed: Ontology):
        """The hedged pairs must not reappear as definitive USES edges."""
        definitive_use = {
            (r.from_concept_id, r.to_concept_id)
            for r in seed.relationships
            if r.relationship_type is RelationshipType.USES
        }
        assert ("security_operations_center", "security_information_and_event_management") not in definitive_use
        assert ("artificial_intelligence_agent", "large_language_model") not in definitive_use

    def test_ai_red_teaming_makes_no_incident_response_claim(self, seed: Ontology):
        """AI Red Teaming must not carry a capability claim about incident response."""
        claims = [
            r
            for r in seed.relationships
            if r.from_concept_id == "ai_red_teaming"
            and r.to_concept_id == "incident_response"
            and r.relationship_type
            in (RelationshipType.MAY_PROVIDE, RelationshipType.PROVIDES)
        ]
        assert claims == []

    def test_relationships_are_indexed_both_directions(self, seed: Ontology):
        outgoing = seed.relationships_from("managed_detection_and_response")
        incoming = seed.relationships_to("endpoint_detection_and_response")
        assert outgoing
        assert incoming
        assert {r.relationship_id for r in outgoing} & {
            r.relationship_id for r in incoming
        }


class TestRegressionCasePrerequisites:
    """The MCP regression cases in spec §8.2 need these concepts to exist."""

    @pytest.mark.parametrize(
        "concept_id",
        [
            "model_context_protocol",
            "mcp_security",
            "prompt_injection",
            "artificial_intelligence_agent",
            "large_language_model",
        ],
    )
    def test_regression_prerequisite_concepts_exist(self, seed: Ontology, concept_id: str):
        assert concept_id in seed.concept_index()


class TestStoreValidation:
    def _minimal_payload(self) -> dict:
        return {
            "concepts": [
                {
                    "concept_id": "alpha",
                    "preferred_label": "Alpha",
                    "definition": "First concept.",
                    "domains": ["AI"],
                    "concept_type": "TECHNOLOGY",
                    "status": "ACTIVE",
                    "terminology_maturity": "EMERGING",
                }
            ],
            "aliases": [],
            "relationships": [],
        }

    def _write(self, tmp_path: Path, payload: dict) -> Path:
        path = tmp_path / "ontology.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_minimal_payload_loads(self, tmp_path: Path):
        ontology = load_ontology(self._write(tmp_path, self._minimal_payload()))
        assert ontology.concept_index()["alpha"].preferred_label == "Alpha"

    def test_dangling_alias_candidate_is_rejected(self, tmp_path: Path):
        payload = self._minimal_payload()
        payload["aliases"] = [
            {
                "alias_id": "a_bad",
                "surface_form": "BAD",
                "alias_type": "ABBREVIATION",
                "candidates": ["does_not_exist"],
                "ambiguous": False,
            }
        ]
        with pytest.raises(OntologyValidationError):
            load_ontology(self._write(tmp_path, payload))

    def test_dangling_relationship_endpoint_is_rejected(self, tmp_path: Path):
        payload = self._minimal_payload()
        payload["relationships"] = [
            {
                "relationship_id": "r_bad",
                "from_concept_id": "alpha",
                "to_concept_id": "ghost",
                "relationship_type": "USES",
                "search_policy": "CONSERVATIVE",
            }
        ]
        with pytest.raises(OntologyValidationError):
            load_ontology(self._write(tmp_path, payload))

    def test_duplicate_concept_id_is_rejected(self, tmp_path: Path):
        payload = self._minimal_payload()
        payload["concepts"].append(dict(payload["concepts"][0]))
        with pytest.raises(OntologyValidationError):
            load_ontology(self._write(tmp_path, payload))

    def test_duplicate_preferred_label_is_rejected(self, tmp_path: Path):
        payload = self._minimal_payload()
        payload["concepts"].append(
            {**payload["concepts"][0], "concept_id": "beta"}
        )
        with pytest.raises(OntologyValidationError):
            load_ontology(self._write(tmp_path, payload))

    def test_duplicate_alias_surface_form_is_rejected(self, tmp_path: Path):
        payload = self._minimal_payload()
        payload["aliases"] = [
            {
                "alias_id": "a_one",
                "surface_form": "SAME",
                "alias_type": "ABBREVIATION",
                "candidates": ["alpha"],
                "ambiguous": False,
            },
            {
                "alias_id": "a_two",
                "surface_form": "SAME",
                "alias_type": "COMMON_NAME",
                "candidates": ["alpha"],
                "ambiguous": True,
            },
        ]
        with pytest.raises(OntologyValidationError):
            load_ontology(self._write(tmp_path, payload))

    def test_unknown_enum_value_is_rejected(self, tmp_path: Path):
        payload = self._minimal_payload()
        payload["concepts"][0]["status"] = "SORT_OF_ACTIVE"
        with pytest.raises(OntologyValidationError):
            load_ontology(self._write(tmp_path, payload))

    def test_generic_technology_domain_is_rejected(self, tmp_path: Path):
        payload = self._minimal_payload()
        payload["concepts"][0]["domains"] = ["TECHNOLOGY"]
        with pytest.raises(OntologyValidationError):
            load_ontology(self._write(tmp_path, payload))

    def test_malformed_json_is_reported_as_validation_error(self, tmp_path: Path):
        path = tmp_path / "ontology.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(OntologyValidationError):
            load_ontology(path)

    def test_missing_file_is_reported_as_validation_error(self, tmp_path: Path):
        with pytest.raises(OntologyValidationError):
            load_ontology(tmp_path / "absent.json")


class TestOntologyQueries:
    def test_get_concept_returns_none_for_unknown_id(self, seed: Ontology):
        assert seed.get_concept("no_such_concept") is None

    def test_concept_index_covers_every_concept(self, seed: Ontology):
        assert len(seed.concept_index()) == len(seed.concepts)

    def test_ontology_is_immutable(self, seed: Ontology):
        with pytest.raises(Exception):
            seed.concepts = ()