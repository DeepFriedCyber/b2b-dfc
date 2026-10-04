"""Structural tests for the Industry Intelligence data models.

These assert the vocabularies and record invariants defined in
``docs/industry-intelligence-v0.01.md`` §3–§5 and §9. They deliberately test
*structure only* — no resolution, ambiguity or query-plan behaviour lives here.
"""

from __future__ import annotations

import dataclasses

import pytest

from b2b_dfc.intelligence.models import (
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


class TestDomainVocabulary:
    def test_initial_domain_values_are_exactly_two(self):
        assert [d.value for d in Domain] == ["CYBERSECURITY", "AI"]

    def test_generic_technology_domain_does_not_exist(self):
        """Spec §3: a generic Technology domain is review-blocking."""
        values = {d.value for d in Domain}
        assert "TECHNOLOGY" not in values

    def test_no_intersection_pseudo_domain_exists(self):
        """Spec §3: cross-domain is expressed with a list, not a third value."""
        values = {d.value for d in Domain}
        assert "CYBERSECURITY_AND_AI" not in values
        assert "CYBERSECURITY_AI" not in values


class TestConceptTypeVocabulary:
    def test_vocabulary_matches_specification(self):
        assert [t.value for t in ConceptType] == [
            "DISCIPLINE",
            "CAPABILITY",
            "TECHNOLOGY",
            "PRODUCT_CATEGORY",
            "SERVICE_CATEGORY",
            "THREAT",
            "RISK",
            "CONTROL",
            "PROTOCOL",
            "FRAMEWORK",
            "STANDARD",
            "CONCEPT",
        ]

    def test_threat_and_risk_are_distinct_members(self):
        """Spec §4.1: a threat is an adversary/event; a risk is potential impact."""
        assert ConceptType.THREAT is not ConceptType.RISK


class TestConceptStatusVocabulary:
    def test_lifecycle_states_match_specification(self):
        assert [s.value for s in ConceptStatus] == [
            "ACTIVE",
            "CANDIDATE",
            "REJECTED",
            "DEPRECATED",
            "MERGED",
        ]


class TestTerminologyMaturityVocabulary:
    def test_vocabulary_matches_specification(self):
        assert [m.value for m in TerminologyMaturity] == [
            "STABLE",
            "ESTABLISHED",
            "EMERGING",
            "UNSETTLED",
        ]


class TestAliasTypeVocabulary:
    def test_vocabulary_matches_specification(self):
        assert [t.value for t in AliasType] == [
            "EXACT_ALIAS",
            "ABBREVIATION",
            "COMMON_NAME",
            "MARKET_TERM",
            "LEGACY_TERM",
            "MISSPELLING",
        ]

    def test_there_is_no_ambiguous_alias_type(self):
        """AGENTS.md §7.2 / spec §5.2: ambiguity is not an alias type."""
        values = {t.value for t in AliasType}
        assert "AMBIGUOUS_ALIAS" not in values
        assert not hasattr(AliasType, "AMBIGUOUS_ALIAS")

    def test_abbreviation_may_be_unambiguous(self):
        """Spec §5.2: alias type and ambiguity are orthogonal."""
        alias = Alias(
            alias_id="a_edr",
            surface_form="EDR",
            alias_type=AliasType.ABBREVIATION,
            candidates=("endpoint_detection_and_response",),
            ambiguous=False,
        )
        assert alias.ambiguous is False


class TestRelationshipVocabulary:
    def test_relationship_types_match_specification(self):
        assert [r.value for r in RelationshipType] == [
            "BROADER",
            "NARROWER",
            "RELATED",
            "PART_OF",
            "USES",
            "MAY_USE",
            "PROVIDES",
            "MAY_PROVIDE",
            "APPLIES_TO",
            "AFFECTS",
            "MITIGATES",
            "DETECTS",
            "PROTECTS",
            "IMPLEMENTS",
            "REQUIRES",
        ]

    def test_may_variants_are_distinct_from_definitive_ones(self):
        """Spec §9.3: MAY_PROVIDE is not PROVIDES, and MAY_USE is not USES."""
        assert RelationshipType.MAY_PROVIDE is not RelationshipType.PROVIDES
        assert RelationshipType.MAY_USE is not RelationshipType.USES

    def test_search_policies_match_specification(self):
        assert [p.value for p in SearchPolicy] == [
            "SAFE",
            "CONSERVATIVE",
            "DISCOVERY_ONLY",
            "NONE",
        ]


def _concept(**overrides) -> Concept:
    fields = dict(
        concept_id="managed_detection_and_response",
        preferred_label="Managed Detection and Response",
        definition="A commercially delivered monitoring and response service.",
        domains=(Domain.CYBERSECURITY,),
        concept_type=ConceptType.SERVICE_CATEGORY,
        status=ConceptStatus.ACTIVE,
        terminology_maturity=TerminologyMaturity.ESTABLISHED,
    )
    fields.update(overrides)
    return Concept(**fields)


class TestConceptRecord:
    def test_concept_requires_at_least_one_domain(self):
        """Spec §3/§4: ``domains`` is a list of one or more values."""
        with pytest.raises(ValueError):
            _concept(domains=())

    def test_concept_accepts_multiple_domains_for_cross_domain_meaning(self):
        """Spec §3: MCP Security is [CYBERSECURITY, AI], not a third domain."""
        concept = _concept(
            concept_id="mcp_security",
            preferred_label="MCP Security",
            domains=(Domain.CYBERSECURITY, Domain.AI),
        )
        assert concept.domains == (Domain.CYBERSECURITY, Domain.AI)

    def test_canonical_status_predicate(self):
        assert _concept(status=ConceptStatus.ACTIVE).is_canonical() is True

    @pytest.mark.parametrize(
        "status",
        [
            ConceptStatus.CANDIDATE,
            ConceptStatus.REJECTED,
            ConceptStatus.DEPRECATED,
            ConceptStatus.MERGED,
        ],
    )
    def test_only_active_concepts_are_canonical(self, status):
        """AGENTS.md §5.1 / spec §4.2: only ACTIVE is canonical and resolvable."""
        assert _concept(status=status).is_canonical() is False

    def test_concept_is_immutable(self):
        concept = _concept()
        with pytest.raises(dataclasses.FrozenInstanceError):
            concept.preferred_label = "Something Else"


class TestAliasRecord:
    def test_alias_requires_at_least_one_candidate(self):
        with pytest.raises(ValueError):
            Alias(
                alias_id="a_empty",
                surface_form="EMPTY",
                alias_type=AliasType.ABBREVIATION,
                candidates=(),
                ambiguous=False,
            )

    def test_alias_permits_multiple_candidates(self):
        """Spec §5.1: the architecture must permit multiple candidates."""
        alias = Alias(
            alias_id="a_multi",
            surface_form="OVERSEAS",
            alias_type=AliasType.COMMON_NAME,
            candidates=("concept_one", "concept_two"),
            ambiguous=True,
        )
        assert len(alias.candidates) == 2
        assert alias.ambiguous is True

    def test_mcp_is_an_abbreviation_flagged_ambiguous(self):
        """AGENTS.md §7.2 worked example."""
        alias = Alias(
            alias_id="a_mcp",
            surface_form="MCP",
            alias_type=AliasType.ABBREVIATION,
            candidates=("model_context_protocol",),
            ambiguous=True,
            notes="Competing readings exist but have no canonical concept in v0.01.",
        )
        assert alias.alias_type is AliasType.ABBREVIATION
        assert alias.ambiguous is True
        assert alias.candidates == ("model_context_protocol",)

    def test_alias_is_immutable(self):
        alias = Alias(
            alias_id="a_edr",
            surface_form="EDR",
            alias_type=AliasType.ABBREVIATION,
            candidates=("endpoint_detection_and_response",),
            ambiguous=False,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            alias.ambiguous = True


class TestRelationshipRecord:
    def _relationship(self, **overrides) -> Relationship:
        fields = dict(
            relationship_id="r_mdr_may_use_edr",
            from_concept_id="managed_detection_and_response",
            to_concept_id="endpoint_detection_and_response",
            relationship_type=RelationshipType.MAY_USE,
            search_policy=SearchPolicy.DISCOVERY_ONLY,
            notes="Taxonomy does not establish that any provider does.",
        )
        fields.update(overrides)
        return Relationship(**fields)

    def test_relationship_requires_distinct_endpoints(self):
        with pytest.raises(ValueError):
            self._relationship(to_concept_id="managed_detection_and_response")

    def test_search_policy_is_mandatory(self):
        """Spec §9.1: search_policy is required, never defaulted."""
        assert self._relationship().search_policy is SearchPolicy.DISCOVERY_ONLY

    def test_may_provide_is_not_treated_as_providing(self):
        """Spec §9.3: MAY_PROVIDE must never be policy SAFE."""
        relationship = self._relationship(
            relationship_type=RelationshipType.MAY_PROVIDE,
            search_policy=SearchPolicy.DISCOVERY_ONLY,
        )
        assert relationship.relationship_type is RelationshipType.MAY_PROVIDE
        assert relationship.search_policy is not SearchPolicy.SAFE

    def test_relationship_is_immutable(self):
        relationship = self._relationship()
        with pytest.raises(dataclasses.FrozenInstanceError):
            relationship.search_policy = SearchPolicy.SAFE